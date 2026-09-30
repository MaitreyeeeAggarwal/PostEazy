import hashlib
import json
from typing import Any
from pydantic import BaseModel


def canonical_json(obj: Any) -> str:
    """Converts a dict or Pydantic model into canonical sorted JSON string."""
    if isinstance(obj, BaseModel):
        data = obj.model_dump(mode="json")
    elif isinstance(obj, dict):
        data = obj
    else:
        data = obj
    return json.dumps(data, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def hash_obj(obj: Any) -> str:
    """Computes SHA256 hash of canonical JSON representation of object."""
    json_str = canonical_json(obj)
    return hashlib.sha256(json_str.encode("utf-8")).hexdigest()


def hash_bytes(data: bytes) -> str:
    """Computes SHA256 hash of raw byte payload."""
    return hashlib.sha256(data).hexdigest()


def hash_stage_input(inputs: Any, stage_version: str = "v1", config_extra: str = "") -> str:
    """Computes a content-addressed cache key fingerprint for a stage execution."""
    raw = f"{canonical_json(inputs)}|{stage_version}|{config_extra}"
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()
