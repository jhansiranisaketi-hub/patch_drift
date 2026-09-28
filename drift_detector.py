"""
drift_detector.py — API Drift Detection
Person 2 module.

Determines whether an API error is caused by API drift (schema/contract change)
or by something unrelated (auth failure, server error, etc.).
"""

# ---------------------------------------------------------------------------
# Signals that indicate API drift (field-level contract changes)
# ---------------------------------------------------------------------------
_DRIFT_SIGNALS = [
    "unknown field",
    "missing required",
    "invalid key",
    "unrecognized field",
    "deprecated",
    "no longer supported",
]

# ---------------------------------------------------------------------------
# Signals / conditions that are explicitly NOT drift
# ---------------------------------------------------------------------------
_NON_DRIFT_SIGNALS = [
    "invalid password",
    "unauthorized",
    "forbidden",
]


def is_drift(status_code: int, error_body: str) -> bool:
    """
    Determine whether an API error represents API drift.

    Args:
        status_code: HTTP status code returned by the API.
        error_body:  Error message / response body as a string.

    Returns:
        True  — error looks like an API contract change (drift).
        False — error is auth-related, a server fault, or unrecognised.

    Examples:
        >>> is_drift(400, "Unknown field: billing_address")
        True
        >>> is_drift(401, "Invalid API key")
        False
        >>> is_drift(500, "Internal server error")
        False
    """
    # 5xx errors are server faults, never drift
    if status_code >= 500:
        return False

    normalised = error_body.lower()

    # Explicit non-drift signals take priority
    for signal in _NON_DRIFT_SIGNALS:
        if signal in normalised:
            return False

    # 401 / 403 are auth/authz errors regardless of message content
    if status_code in (401, 403):
        return False

    # Check for positive drift signals
    for signal in _DRIFT_SIGNALS:
        if signal in normalised:
            return True

    return False
