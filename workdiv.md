# PatchDrift — Work Division & API Contract

> Read this before writing a single line of code.
> Everyone works independently. main.py is the glue. Stick to the contracts below and merging will be painless.

---

## Team Overview

| Person | Module | Files |
|---|---|---|
| Person 1 | Mock APIs + Gateway | `mock_api.py`, `main.py` |
| Person 2 | Drift Detection + Adapter + Sandbox | `drift_detector.py`, `adapter.py`, `sandbox.py` |
| Person 3 | Hindsight Memory + PR Generator | `hindsight.py`, `pr_generator.py` |
| Person 4 | Frontend Dashboard | `frontend/index.html` |

---

## CRITICAL: Start Order

**Person 1 starts first.** Everyone else can start in parallel after 10 minutes.

Person 1 must expose the mock API endpoints early so Person 2 can test their sandbox,
and Person 4 can test their frontend calls.

---

---

# PERSON 1 — Mock APIs + Gateway

## Files: `mock_api.py`, `main.py`

---

### Your job

1. Build the V1 and V2 mock payment APIs.
2. Build the PatchDrift gateway that proxies requests and wires all modules together.

---

### mock_api.py

Create a FastAPI app with two routers.

**V1 endpoint** — accepts old format:
```
POST /v1/payment
Body: { "customer_id": int, "billing_address": str }
Returns: { "success": true, "transaction_id": "TXN_XXXX" }
```

**V2 endpoint** — accepts new format only:
```
POST /v2/payment
Body: {
  "customer_id": int,
  "customer": {
    "address": {
      "billing": str
    }
  }
}
Returns: { "success": true, "transaction_id": "TXN_XXXX" }

If old format sent:
Returns 400: { "error": "Unknown field: billing_address" }
```

Run this on port 8001.

---

### main.py

Create the PatchDrift gateway on port 8000.

**Import these exactly** (others will implement them):
```python
from drift_detector import is_drift
from adapter import apply_adapter, KNOWN_MIGRATIONS
from hindsight import retain, recall, get_all
from sandbox import verify_adapter
from pr_generator import generate_pr_diff
```

**Endpoints to implement:**

```
POST /call
GET  /status
GET  /hindsight
POST /generate-pr
GET  /health
```

**POST /call logic (exact flow):**
```
1. Forward payload to mock V2 API
2. If 200 → return success response
3. If 400/error:
   a. Call is_drift(status_code, error_body) → bool
   b. If not drift → return original error
   c. If drift:
      i.  Call recall(api_name, error_signature) → adapter or None
      ii. If adapter found → source = "hindsight"
          Else → use KNOWN_MIGRATIONS, source = "generated"
      iii. Call verify_adapter(payload, adapter_map) → "PASS" or "FAIL"
      iv. If PASS:
            - Call apply_adapter(payload, adapter_map)
            - Retry request to V2 with transformed payload
            - Call retain(api_name, error_signature, adapter_map, result)
            - Return healed response
      v.  If FAIL → return { "status": "needs_human_review" }
```

**Request body for POST /call:**
```json
{
  "api": "payment",
  "payload": {
    "customer_id": 101,
    "billing_address": "Hyderabad"
  }
}
```

**Response for healed request:**
```json
{
  "status": "healed",
  "source": "generated",
  "original_error": "400 Unknown field: billing_address",
  "adapter_applied": { "billing_address": "customer.address.billing" },
  "verification": "PASS",
  "api_response": { "success": true, "transaction_id": "TXN_9182" },
  "hindsight": "stored"
}
```

**Response for Hindsight recall:**
```json
{
  "status": "healed",
  "source": "hindsight",
  "adapter_applied": { "billing_address": "customer.address.billing" },
  "verification": "PASS",
  "api_response": { "success": true, "transaction_id": "TXN_9182" },
  "hindsight": "recalled"
}
```

**GET /status** — return the last drift event dict (store it as a module-level variable in main.py)

**GET /hindsight** — call `get_all()` and return it

**POST /generate-pr** — call `generate_pr_diff()` and return the result

**GET /health** — return `{ "status": "ok" }`

---

### Add CORS to main.py

```python
from fastapi.middleware.cors import CORSMiddleware

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)
```

The frontend will break without this.

---

---

# PERSON 2 — Drift Detection + Adapter + Sandbox

## Files: `drift_detector.py`, `adapter.py`, `sandbox.py`

---

### Your job

1. Detect if an API error is caused by drift.
2. Apply a field mapping transformation to a payload.
3. Verify an adapter by testing it against the mock V2 API.

---

### drift_detector.py

**Expose exactly this function:**

```python
def is_drift(status_code: int, error_body: str) -> bool
```

- Returns `True` if the error looks like API drift
- Returns `False` for auth errors, server errors, etc.

**Signals that indicate drift:**
- `"unknown field"`
- `"missing required"`
- `"invalid key"`
- `"unrecognized field"`
- `"deprecated"`
- `"no longer supported"`

**Signals that are NOT drift:**
- `"invalid password"`
- `"unauthorized"`
- `"forbidden"`
- 500 status codes

Example:
```python
is_drift(400, "Unknown field: billing_address")  # → True
is_drift(401, "Invalid API key")                 # → False
is_drift(500, "Internal server error")           # → False
```

---

### adapter.py

**Expose exactly these:**

```python
KNOWN_MIGRATIONS = {
    "billing_address": ("customer", "address", "billing")
}

def apply_adapter(payload: dict, migration_map: dict) -> dict
```

`migration_map` format:
```python
{
  "old_field_name": ("path", "to", "new", "field")
}
```

`apply_adapter` must:
1. Take the old payload
2. For each key in migration_map that exists in payload, remove it and nest the value at the new path
3. Return the new payload without modifying the original

Example:
```python
apply_adapter(
    {"customer_id": 101, "billing_address": "Hyderabad"},
    {"billing_address": ("customer", "address", "billing")}
)
# Returns:
# {
#   "customer_id": 101,
#   "customer": { "address": { "billing": "Hyderabad" } }
# }
```

---

### sandbox.py

**Expose exactly this function:**

```python
def verify_adapter(original_payload: dict, migration_map: dict) -> str
```

- Returns `"PASS"` or `"FAIL"`

**How it works:**
1. Call `apply_adapter(original_payload, migration_map)` to get transformed payload
2. Send a POST request to `http://localhost:8001/v2/payment` with the transformed payload
3. If response is 200 → return `"PASS"`
4. If response is 400/error → return `"FAIL"`

Use `httpx` for the HTTP call (already in requirements.txt).

```python
import httpx
from adapter import apply_adapter

def verify_adapter(original_payload: dict, migration_map: dict) -> str:
    transformed = apply_adapter(original_payload, migration_map)
    try:
        response = httpx.post("http://localhost:8001/v2/payment", json=transformed)
        return "PASS" if response.status_code == 200 else "FAIL"
    except Exception:
        return "FAIL"
```

---

---

# PERSON 3 — Hindsight Memory + PR Generator

## Files: `hindsight.py`, `pr_generator.py`

---

### Your job

1. Store and retrieve successful migration knowledge.
2. Generate a before/after code diff showing the permanent fix.

---

### hindsight.py

**Expose exactly these functions:**

```python
def retain(api_name: str, error_signature: str, adapter_map: dict, result: dict) -> None
def recall(api_name: str, error_signature: str) -> dict | None
def get_all() -> dict
```

**Internal store** — module-level dict, no database needed:
```python
_store = {}
```

**retain:**
- Key = `f"{api_name}:{error_signature}"`
- Store: adapter_map, result, timestamp, use_count = 1

**recall:**
- Look up key
- If found: increment use_count, return the adapter_map
- If not found: return None

**get_all:**
- Return the full `_store` dict

**error_signature** is just the error string from the API response.
Example: `"Unknown field: billing_address"`

The key becomes: `"payment:Unknown field: billing_address"`

---

### pr_generator.py

**Expose exactly this function:**

```python
def generate_pr_diff() -> dict
```

Returns:
```json
{
  "title": "fix: migrate billing_address to customer.address.billing",
  "branch": "patchdrift/fix-billing-address-migration",
  "before": "const payment = {\n    customer_id: customerId,\n    billing_address: address\n};",
  "after": "const payment = {\n    customer_id: customerId,\n    customer: {\n        address: {\n            billing: address\n        }\n    }\n};",
  "description": "PatchDrift detected that billing_address has moved to customer.address.billing in Payment API V2. This change updates the request payload to match the new schema.",
  "status": "ready"
}
```

This is a hardcoded response for the MVP demo. It simulates what a real PR would look like.

**Optional (if time allows):** Use PyGithub to actually open a PR:
```python
from github import Github

def create_github_pr(token: str, repo_name: str, diff: dict) -> str:
    g = Github(token)
    repo = g.get_repo(repo_name)
    # create branch, commit, PR
    # return PR URL
```

Only do the optional part if the rest is done and you have 10 minutes left.

---

---

# PERSON 4 — Frontend Dashboard

## File: `frontend/index.html`

---

### Your job

Build a single HTML file dashboard. No frameworks. No build step. Open directly in browser.

Use Tailwind via CDN:
```html
<script src="https://cdn.tailwindcss.com"></script>
```

---

### Backend base URL

```javascript
const BASE_URL = "http://localhost:8000";
```

---

### API calls you will make

```javascript
// Send a request through PatchDrift
POST http://localhost:8000/call
Body: { "api": "payment", "payload": { "customer_id": 101, "billing_address": "Hyderabad" } }

// Get all Hindsight memories
GET http://localhost:8000/hindsight

// Get last drift event
GET http://localhost:8000/status

// Generate PR diff
POST http://localhost:8000/generate-pr
```

---

### Layout — 4 panels

```
┌─────────────────────────────────────────────────────────┐
│  🔧 PatchDrift Dashboard                                │
├────────────────────────┬────────────────────────────────┤
│  SEND REQUEST          │  DRIFT DETECTION LOG           │
│                        │                                │
│  Customer ID: [101   ] │  ● Forwarding to API V2...     │
│  Address: [Hyderabad ] │  ● 400 Unknown field detected  │
│                        │  ● Drift confirmed             │
│  [Send V1 Format]      │  ● Adapter generated           │
│                        │  ● Sandbox: PASS               │
│  Status badge here     │  ● Retry → 200 OK ✓            │
├────────────────────────┼────────────────────────────────┤
│  HINDSIGHT MEMORY      │  GENERATED PR DIFF             │
│                        │                                │
│  payment:Unknown field │  Title: fix: migrate           │
│  billing_address →     │  billing_address               │
│  customer.address.     │                                │
│  billing               │  - billing_address: address    │
│  ✓ Verified            │  + customer: {                 │
│  Used: 2 times         │  +   address: {                │
│                        │  +     billing: address        │
│  [Refresh Memory]      │  +   }                         │
│                        │  + }                           │
│                        │                                │
│                        │  [Generate PR]                 │
└────────────────────────┴────────────────────────────────┘
```

---

### Behaviour

**Send Request button:**
1. POST to `/call` with the form values
2. Show a step-by-step log in the Drift Detection panel based on response:
   - If `status === "healed"` and `source === "generated"` → show full drift pipeline steps
   - If `status === "healed"` and `source === "hindsight"` → show "Hindsight recall — instant fix"
   - Color the status badge green for healed, red for error

**Refresh Memory button:**
1. GET `/hindsight`
2. Display each memory entry in the Hindsight panel

**Generate PR button:**
1. POST `/generate-pr`
2. Display the before/after diff in the PR panel

---

### Status badge colors

- `healed` → green badge
- `needs_human_review` → yellow badge
- `error` → red badge
- `direct_success` → blue badge

---

### Important

- Do not use React, Vue, or any framework
- All fetch calls must include `Content-Type: application/json` header
- Handle loading state — show "Processing..." while waiting
- Handle errors gracefully — if backend is down, show "Backend not reachable"

---

---

# Shared: requirements.txt

Person 1 creates this file.

```
fastapi
uvicorn
httpx
PyGithub
```

---

# Shared: How to Run Everything

Person 1 documents this, everyone follows it:

```bash
# Terminal 1 — Mock APIs (V1 + V2)
uvicorn mock_api:app --port 8001

# Terminal 2 — PatchDrift Gateway
uvicorn main:app --port 8000 --reload

# Browser — Frontend
open frontend/index.html
```

---

# Integration Checklist (do before demo)

- [ ] Person 2: test `is_drift(400, "Unknown field: billing_address")` returns True
- [ ] Person 2: test `apply_adapter` output matches expected nested format
- [ ] Person 2: test `verify_adapter` returns PASS when mock V2 is running
- [ ] Person 3: test `retain` then `recall` returns the correct adapter
- [ ] Person 3: test `generate_pr_diff` returns all expected keys
- [ ] Person 1: test `POST /call` with old payload returns healed response
- [ ] Person 1: test second `POST /call` returns `source: hindsight`
- [ ] Person 4: test all 4 panels render and API calls succeed
- [ ] All: run full demo flow end-to-end once before recording

---

# Demo Script (for video)

1. Open dashboard in browser
2. Enter customer_id: 101, address: Hyderabad → click Send V1 Format
3. Show drift log: detection → adapter → PASS → healed
4. Click Refresh Memory → show migration stored
5. Send same request again → show "Hindsight recall — instant fix"
6. Click Generate PR → show before/after code diff
7. Done. That's the full story.
