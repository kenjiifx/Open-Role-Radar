"""orjson-based serialization for LiveState round-trips."""

from __future__ import annotations

from datetime import datetime
from typing import Any

import orjson

from openroleradar.models.state import LiveState

_ORJSON_OPTS = orjson.OPT_SERIALIZE_NUMPY | orjson.OPT_UTC_Z


def _default(obj: Any) -> Any:
    if isinstance(obj, datetime):
        return obj.isoformat()
    raise TypeError(f"Object of type {type(obj).__name__} is not JSON serializable")


def state_to_dict(state: LiveState) -> dict[str, Any]:
    """Convert LiveState to a JSON-compatible dictionary."""
    return state.model_dump(mode="json")


def state_from_dict(data: dict[str, Any]) -> LiveState:
    """Reconstruct LiveState from a dictionary."""
    return LiveState.model_validate(data)


def serialize_state(state: LiveState) -> bytes:
    """Serialize LiveState to compact UTF-8 JSON bytes."""
    payload = state_to_dict(state)
    return orjson.dumps(payload, option=_ORJSON_OPTS, default=_default)


def deserialize_state(data: bytes) -> LiveState:
    """Deserialize LiveState from JSON bytes."""
    parsed = orjson.loads(data)
    if not isinstance(parsed, dict):
        raise ValueError("LiveState payload must be a JSON object")
    return state_from_dict(parsed)


def serialize_pretty(state: LiveState) -> bytes:
    """Serialize LiveState with indentation for debugging."""
    payload = state_to_dict(state)
    return orjson.dumps(
        payload,
        option=_ORJSON_OPTS | orjson.OPT_INDENT_2,
        default=_default,
    )
