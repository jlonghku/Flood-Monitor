"""Shared schema primitives."""

from __future__ import annotations

from datetime import datetime, timezone
from hashlib import sha1
from typing import Any

JsonDict = dict[str, Any]
Point = tuple[float, float]
BBox = tuple[float, float, float, float]


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def stable_id(prefix: str, *parts: object, length: int = 12) -> str:
    raw = "|".join("" if part is None else str(part) for part in parts)
    return f"{prefix}-{sha1(raw.encode('utf-8')).hexdigest()[:length]}"


def clamp01(value: float) -> float:
    return max(0.0, min(1.0, float(value)))
