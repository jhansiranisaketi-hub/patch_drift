"""
hindsight.py — PatchDrift Hindsight Memory

Stores successful API migration knowledge so PatchDrift can:
- Retain: store successful migrations after healing
- Recall: retrieve known migrations when the same error occurs
- Reflect: analyze patterns across migrations (future enhancement)

Uses in-memory dict for MVP. Can be swapped with SQLite/Redis for persistence.
"""

from __future__ import annotations

import time
from typing import Any

# ---------------------------------------------------------------------------
# In-memory store
# ---------------------------------------------------------------------------

_store: dict[str, dict[str, Any]] = {}


# ---------------------------------------------------------------------------
# Retain — store a successful migration
# ---------------------------------------------------------------------------

def retain(api_name: str, error_signature: str, adapter_map: dict, result: dict) -> None:
    """
    Store a successful migration in Hindsight memory.

    Args:
        api_name: Name of the API (e.g., "payment")
        error_signature: The error message that triggered the migration
        adapter_map: The field mapping that fixed the issue
        result: The successful API response after healing

    Example:
        retain(
            "payment",
            "Unknown field: billing_address",
            {"billing_address": ("customer", "address", "billing")},
            {"success": True, "transaction_id": "TXN_1234"}
        )
    """
    key = _make_key(api_name, error_signature)

    if key in _store:
        # Migration already exists — increment use count
        _store[key]["uses"] += 1
        _store[key]["last_used"] = time.time()
    else:
        # New migration — store it
        _store[key] = {
            "api": api_name,
            "error_signature": error_signature,
            "adapter": adapter_map,
            "result": result,
            "uses": 1,
            "created_at": time.time(),
            "last_used": time.time(),
        }


# ---------------------------------------------------------------------------
# Recall — retrieve a known migration
# ---------------------------------------------------------------------------

def recall(api_name: str, error_signature: str) -> dict | None:
    """
    Retrieve a previously stored migration from Hindsight memory.

    Args:
        api_name: Name of the API
        error_signature: The error message

    Returns:
        The adapter_map if found, None otherwise

    Example:
        adapter = recall("payment", "Unknown field: billing_address")
        if adapter:
            # Reuse the known migration
            transformed = apply_adapter(payload, adapter)
    """
    key = _make_key(api_name, error_signature)

    if key in _store:
        entry = _store[key]
        # Increment use count on recall
        entry["uses"] += 1
        entry["last_used"] = time.time()
        return entry["adapter"]

    return None


# ---------------------------------------------------------------------------
# Get All — retrieve all stored migrations
# ---------------------------------------------------------------------------

def get_all() -> dict[str, dict[str, Any]]:
    """
    Get all stored migrations.

    Returns:
        Dictionary of all migrations keyed by "api:error_signature"

    Example:
        memories = get_all()
        for key, entry in memories.items():
            print(f"{key} used {entry['uses']} times")
    """
    return _store


# ---------------------------------------------------------------------------
# Reflect — analyze migration patterns (future enhancement)
# ---------------------------------------------------------------------------

def reflect() -> dict[str, Any]:
    """
    Analyze patterns across all stored migrations.

    Returns insights like:
    - Most common migration types
    - APIs with frequent changes
    - Success rate of different adapters

    This is a placeholder for future ML/pattern analysis.
    """
    total = len(_store)
    apis = set(entry["api"] for entry in _store.values())
    total_uses = sum(entry["uses"] for entry in _store.values())

    return {
        "total_migrations": total,
        "unique_apis": len(apis),
        "apis": list(apis),
        "total_reuses": total_uses - total,  # reuses = total uses - initial stores
        "most_used": _get_most_used(),
    }


def _get_most_used() -> dict[str, Any] | None:
    """Get the migration that has been reused the most."""
    if not _store:
        return None

    most_used_key = max(_store.keys(), key=lambda k: _store[k]["uses"])
    entry = _store[most_used_key]

    return {
        "key": most_used_key,
        "api": entry["api"],
        "error_signature": entry["error_signature"],
        "uses": entry["uses"],
        "adapter": entry["adapter"],
    }


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_key(api_name: str, error_signature: str) -> str:
    """Generate a unique key for storing a migration."""
    return f"{api_name}:{error_signature}"


# ---------------------------------------------------------------------------
# Clear (for testing)
# ---------------------------------------------------------------------------

def clear() -> None:
    """Clear all stored migrations. Useful for testing."""
    _store.clear()
