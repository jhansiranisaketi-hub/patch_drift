"""
sandbox.py — Adapter Sandbox Verification
Person 2 module.

Tests a generated adapter against the live mock V2 API before it is used
in production. AI-generated fixes are never trusted blindly.
"""

import httpx
from adapter import apply_adapter

# ---------------------------------------------------------------------------
# The mock V2 endpoint to validate against
# ---------------------------------------------------------------------------
_V2_ENDPOINT = "http://localhost:8001/v2/payment"
_TIMEOUT = 5.0  # seconds


def verify_adapter(original_payload: dict, migration_map: dict) -> str:
    """
    Verify that applying migration_map to original_payload produces a payload
    that the V2 API accepts.

    Steps:
      1. Apply the adapter to obtain the transformed payload.
      2. POST the transformed payload to the mock V2 endpoint.
      3. Return "PASS" if the response is HTTP 200, "FAIL" otherwise.

    Args:
        original_payload: The original (old-format) request payload.
        migration_map:    Mapping of old_field -> (path, to, new, field).

    Returns:
        "PASS" — transformed payload was accepted by V2.
        "FAIL" — V2 rejected the payload, or the mock API is unreachable.

    Example:
        >>> verify_adapter(
        ...     {"customer_id": 101, "billing_address": "Hyderabad"},
        ...     {"billing_address": ("customer", "address", "billing")}
        ... )
        'PASS'  # when mock_api.py is running on port 8001
    """
    transformed = apply_adapter(original_payload, migration_map)

    try:
        response = httpx.post(_V2_ENDPOINT, json=transformed, timeout=_TIMEOUT)
        return "PASS" if response.status_code == 200 else "FAIL"
    except Exception:
        # Network error, timeout, or mock API not running
        return "FAIL"
