"""
main.py — PatchDrift Gateway
Runs on port 8000.

Proxies requests to the mock Payment API V2.
On failure, runs the full drift detection → adapter → sandbox → self-heal pipeline.

Endpoints:
  POST /call         — proxy a request through PatchDrift
  GET  /status       — last drift detection event
  GET  /hindsight    — all stored migrations
  POST /generate-pr  — trigger PR diff generation
  GET  /health       — service health check
"""

from __future__ import annotations

import httpx
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel

# ---------------------------------------------------------------------------
# Module imports — each implemented by their respective team member
# ---------------------------------------------------------------------------
try:
    from drift_detector import is_drift
except ImportError:
    # Fallback stub so gateway starts even if Person 2 hasn't pushed yet
    def is_drift(status_code: int, error_body: str) -> bool:  # type: ignore[misc]
        return status_code == 400 and "unknown field" in error_body.lower()

try:
    from adapter import apply_adapter, KNOWN_MIGRATIONS
except ImportError:
    KNOWN_MIGRATIONS = {"billing_address": ("customer", "address", "billing")}  # type: ignore[assignment]

    def apply_adapter(payload: dict, migration_map: dict) -> dict:  # type: ignore[misc]
        result = dict(payload)
        for old_key, new_path in migration_map.items():
            if old_key in result:
                val = result.pop(old_key)
                nested: dict = val  # type: ignore[assignment]
                for key in reversed(new_path):
                    nested = {key: nested}
                result.update(nested)
        return result

try:
    from hindsight import retain, recall, get_all
except ImportError:
    _store: dict = {}

    def retain(api_name: str, error_signature: str, adapter_map: dict, result: dict) -> None:  # type: ignore[misc]
        _store[f"{api_name}:{error_signature}"] = {"adapter": adapter_map, "result": result, "uses": 1}

    def recall(api_name: str, error_signature: str) -> dict | None:  # type: ignore[misc]
        entry = _store.get(f"{api_name}:{error_signature}")
        if entry:
            entry["uses"] += 1
            return entry["adapter"]
        return None

    def get_all() -> dict:  # type: ignore[misc]
        return _store

try:
    from sandbox import verify_adapter
except ImportError:
    def verify_adapter(original_payload: dict, migration_map: dict) -> str:  # type: ignore[misc]
        try:
            transformed = apply_adapter(original_payload, migration_map)
            resp = httpx.post("http://localhost:8001/v2/payment", json=transformed, timeout=5.0)
            return "PASS" if resp.status_code == 200 else "FAIL"
        except Exception:
            return "FAIL"

try:
    from pr_generator import generate_pr_diff
except ImportError:
    def generate_pr_diff() -> dict:  # type: ignore[misc]
        return {
            "title": "fix: migrate billing_address to customer.address.billing",
            "branch": "patchdrift/fix-billing-address-migration",
            "before": (
                "const payment = {\n"
                "    customer_id: customerId,\n"
                "    billing_address: address\n"
                "};"
            ),
            "after": (
                "const payment = {\n"
                "    customer_id: customerId,\n"
                "    customer: {\n"
                "        address: {\n"
                "            billing: address\n"
                "        }\n"
                "    }\n"
                "};"
            ),
            "description": (
                "PatchDrift detected that billing_address has moved to "
                "customer.address.billing in Payment API V2. "
                "This change updates the request payload to match the new schema."
            ),
            "status": "ready",
        }

# ---------------------------------------------------------------------------
# App setup
# ---------------------------------------------------------------------------

app = FastAPI(title="PatchDrift Gateway", version="1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# Module-level state — last drift event for /status
_last_drift_event: dict = {}

# Target API base URL (mock V2)
MOCK_API_BASE = "http://localhost:8001"
TARGET_ENDPOINT = f"{MOCK_API_BASE}/v2/payment"


# ---------------------------------------------------------------------------
# Request / Response models
# ---------------------------------------------------------------------------

class CallRequest(BaseModel):
    api: str = "payment"
    payload: dict


# ---------------------------------------------------------------------------
# POST /call — main PatchDrift pipeline
# ---------------------------------------------------------------------------

@app.post("/call")
async def call(request: CallRequest):
    global _last_drift_event

    api_name = request.api
    payload = request.payload

    # ------------------------------------------------------------------
    # Step 1: Forward request to target API
    # ------------------------------------------------------------------
    try:
        response = httpx.post(TARGET_ENDPOINT, json=payload, timeout=5.0)
    except httpx.ConnectError:
        return JSONResponse(
            status_code=503,
            content={
                "status": "error",
                "message": "Mock API not reachable. Start mock_api.py on port 8001.",
            },
        )

    # ------------------------------------------------------------------
    # Step 2: If success, return directly
    # ------------------------------------------------------------------
    if response.status_code == 200:
        return {
            "status": "direct_success",
            "api_response": response.json(),
        }

    # ------------------------------------------------------------------
    # Step 3: Check if failure is API drift
    # ------------------------------------------------------------------
    error_body = ""
    try:
        error_json = response.json()
        error_body = error_json.get("error", "") or str(error_json)
    except Exception:
        error_body = response.text

    drift_detected = is_drift(response.status_code, error_body)

    if not drift_detected:
        return JSONResponse(
            status_code=response.status_code,
            content={
                "status": "error",
                "message": "Request failed. Not identified as API drift.",
                "original_error": error_body,
            },
        )

    # Record drift event
    _last_drift_event = {
        "api": api_name,
        "status_code": response.status_code,
        "error": error_body,
        "payload": payload,
        "drift_detected": True,
    }

    # ------------------------------------------------------------------
    # Step 4: Check Hindsight for a known migration
    # ------------------------------------------------------------------
    error_signature = error_body
    known_adapter = recall(api_name, error_signature)

    if known_adapter:
        migration_map = known_adapter
        source = "hindsight"
    else:
        migration_map = KNOWN_MIGRATIONS
        source = "generated"

    # ------------------------------------------------------------------
    # Step 5: Sandbox verification
    # ------------------------------------------------------------------
    verification = verify_adapter(payload, migration_map)

    if verification == "FAIL":
        _last_drift_event["verification"] = "FAIL"
        return JSONResponse(
            status_code=422,
            content={
                "status": "needs_human_review",
                "message": "Adapter generated but failed sandbox verification.",
                "original_error": error_body,
                "adapter_attempted": {k: ".".join(v) for k, v in migration_map.items()},
                "verification": "FAIL",
            },
        )

    # ------------------------------------------------------------------
    # Step 6: Apply adapter and retry
    # ------------------------------------------------------------------
    transformed_payload = apply_adapter(payload, migration_map)

    try:
        retry_response = httpx.post(TARGET_ENDPOINT, json=transformed_payload, timeout=5.0)
    except httpx.ConnectError:
        return JSONResponse(
            status_code=503,
            content={"status": "error", "message": "Mock API not reachable on retry."},
        )

    if retry_response.status_code != 200:
        return JSONResponse(
            status_code=retry_response.status_code,
            content={
                "status": "retry_failed",
                "message": "Adapter applied but retry still failed.",
                "retry_error": retry_response.text,
            },
        )

    api_result = retry_response.json()

    # ------------------------------------------------------------------
    # Step 7: Store in Hindsight
    # ------------------------------------------------------------------
    hindsight_action = "recalled" if source == "hindsight" else "stored"
    if source != "hindsight":
        retain(api_name, error_signature, migration_map, api_result)

    # ------------------------------------------------------------------
    # Step 8: Update last drift event and return healed response
    # ------------------------------------------------------------------
    _last_drift_event.update(
        {
            "source": source,
            "adapter": {k: ".".join(v) for k, v in migration_map.items()},
            "verification": "PASS",
            "healed": True,
        }
    )

    return {
        "status": "healed",
        "source": source,
        "original_error": f"{response.status_code} {error_body}",
        "adapter_applied": {k: ".".join(v) for k, v in migration_map.items()},
        "verification": "PASS",
        "api_response": api_result,
        "hindsight": hindsight_action,
    }


# ---------------------------------------------------------------------------
# GET /status — last drift event
# ---------------------------------------------------------------------------

@app.get("/status")
async def status():
    if not _last_drift_event:
        return {"status": "no_drift_detected_yet"}
    return _last_drift_event


# ---------------------------------------------------------------------------
# GET /hindsight — all stored migrations
# ---------------------------------------------------------------------------

@app.get("/hindsight")
async def hindsight():
    memories = get_all()
    return {
        "total": len(memories),
        "migrations": memories,
    }


# ---------------------------------------------------------------------------
# POST /generate-pr — trigger PR diff generation
# ---------------------------------------------------------------------------

@app.post("/generate-pr")
async def generate_pr():
    diff = generate_pr_diff()
    return diff


# ---------------------------------------------------------------------------
# GET /health
# ---------------------------------------------------------------------------

@app.get("/health")
async def health():
    return {
        "status": "ok",
        "service": "patchdrift_gateway",
        "port": 8000,
        "target_api": MOCK_API_BASE,
    }


# ---------------------------------------------------------------------------
# Run
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
