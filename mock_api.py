"""
mock_api.py — PatchDrift Mock Payment API
Runs on port 8001.

V1: accepts { customer_id, billing_address }
V2: accepts { customer_id, customer: { address: { billing } } }
     rejects old format with 400 Unknown field: billing_address
"""

import random
import string

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel

app = FastAPI(title="Mock Payment API", version="2.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _generate_txn_id() -> str:
    """Generate a random transaction ID for demo purposes."""
    suffix = "".join(random.choices(string.digits, k=4))
    return f"TXN_{suffix}"


# ---------------------------------------------------------------------------
# V1 Models
# ---------------------------------------------------------------------------

class V1PaymentRequest(BaseModel):
    customer_id: int
    billing_address: str


# ---------------------------------------------------------------------------
# V2 Models
# ---------------------------------------------------------------------------

class V2Address(BaseModel):
    billing: str


class V2Customer(BaseModel):
    address: V2Address


class V2PaymentRequest(BaseModel):
    customer_id: int
    customer: V2Customer


# ---------------------------------------------------------------------------
# V1 Endpoint — old format accepted
# ---------------------------------------------------------------------------

@app.post("/v1/payment")
async def v1_payment(request: Request):
    """
    Payment API V1.
    Accepts: { customer_id: int, billing_address: str }
    """
    body = await request.json()

    customer_id = body.get("customer_id")
    billing_address = body.get("billing_address")

    if customer_id is None:
        return JSONResponse(
            status_code=400,
            content={"error": "Missing required field: customer_id"},
        )

    if billing_address is None:
        return JSONResponse(
            status_code=400,
            content={"error": "Missing required field: billing_address"},
        )

    return {
        "success": True,
        "transaction_id": _generate_txn_id(),
        "api_version": "v1",
        "customer_id": customer_id,
        "billing_address": billing_address,
    }


# ---------------------------------------------------------------------------
# V2 Endpoint — new nested format required
# ---------------------------------------------------------------------------

@app.post("/v2/payment")
async def v2_payment(request: Request):
    """
    Payment API V2.
    Accepts: { customer_id: int, customer: { address: { billing: str } } }
    Rejects old flat format with 400.
    """
    body = await request.json()

    # Reject old format — this is the breaking change PatchDrift must handle
    if "billing_address" in body:
        return JSONResponse(
            status_code=400,
            content={
                "error": "Unknown field: billing_address",
                "message": (
                    "The field 'billing_address' is no longer accepted in V2. "
                    "Use customer.address.billing instead."
                ),
                "api_version": "v2",
            },
        )

    customer_id = body.get("customer_id")
    if customer_id is None:
        return JSONResponse(
            status_code=400,
            content={"error": "Missing required field: customer_id"},
        )

    customer = body.get("customer")
    if not customer:
        return JSONResponse(
            status_code=400,
            content={"error": "Missing required field: customer"},
        )

    address = customer.get("address") if isinstance(customer, dict) else None
    if not address:
        return JSONResponse(
            status_code=400,
            content={"error": "Missing required field: customer.address"},
        )

    billing = address.get("billing") if isinstance(address, dict) else None
    if not billing:
        return JSONResponse(
            status_code=400,
            content={"error": "Missing required field: customer.address.billing"},
        )

    return {
        "success": True,
        "transaction_id": _generate_txn_id(),
        "api_version": "v2",
        "customer_id": customer_id,
        "billing_address_normalized": billing,
    }


# ---------------------------------------------------------------------------
# Health check
# ---------------------------------------------------------------------------

@app.get("/health")
async def health():
    return {"status": "ok", "service": "mock_payment_api", "versions": ["v1", "v2"]}


# ---------------------------------------------------------------------------
# Run
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("mock_api:app", host="0.0.0.0", port=8001, reload=True)
