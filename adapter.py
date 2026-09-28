"""
adapter.py — Field Mapping Adapter
Person 2 module.

Provides a registry of known API migrations and a function to apply
any field-mapping transformation to a payload dict.
"""

import copy

# ---------------------------------------------------------------------------
# Registry of known field migrations.
# Key   = old field name in the payload.
# Value = tuple representing the new nested path where the value should live.
#
# Example:
#   "billing_address": ("customer", "address", "billing")
#   means payload["billing_address"] moves to
#   payload["customer"]["address"]["billing"]
# ---------------------------------------------------------------------------
KNOWN_MIGRATIONS: dict[str, tuple] = {
    "billing_address": ("customer", "address", "billing"),
}


def apply_adapter(payload: dict, migration_map: dict) -> dict:
    """
    Transform a payload by applying the field migrations described in
    migration_map.

    For each entry in migration_map whose key exists in payload:
      1. Remove the old top-level key.
      2. Nest the value at the path given by the tuple.

    The original payload is never mutated — a deep copy is used.

    Args:
        payload:       The original request payload dict.
        migration_map: Mapping of old_field -> (path, to, new, field).

    Returns:
        A new dict with all mapped fields moved to their new locations.

    Example:
        >>> apply_adapter(
        ...     {"customer_id": 101, "billing_address": "Hyderabad"},
        ...     {"billing_address": ("customer", "address", "billing")}
        ... )
        {'customer_id': 101, 'customer': {'address': {'billing': 'Hyderabad'}}}
    """
    result = copy.deepcopy(payload)

    for old_key, new_path in migration_map.items():
        if old_key not in result:
            continue

        value = result.pop(old_key)

        # Build the nested dict from the inside out.
        # e.g. ("customer", "address", "billing") with value "Hyderabad"
        # → {"billing": "Hyderabad"}
        # → {"address": {"billing": "Hyderabad"}}
        # → {"customer": {"address": {"billing": "Hyderabad"}}}
        nested: dict = value  # type: ignore[assignment]
        for key in reversed(new_path):
            nested = {key: nested}

        # Merge the constructed nested dict into result.
        # This handles the case where a top-level key (e.g. "customer")
        # already exists from a previous migration — we deep-merge rather
        # than overwrite.
        _deep_merge(result, nested)

    return result


# ---------------------------------------------------------------------------
# Internal helper
# ---------------------------------------------------------------------------

def _deep_merge(base: dict, override: dict) -> None:
    """
    Recursively merge *override* into *base* in-place.

    For keys that exist in both and whose values are dicts, merge
    recursively. Otherwise the override value wins.
    """
    for key, value in override.items():
        if key in base and isinstance(base[key], dict) and isinstance(value, dict):
            _deep_merge(base[key], value)
        else:
            base[key] = value
