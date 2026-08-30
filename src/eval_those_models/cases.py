"""Stable identities for immutable evaluation cases."""

from __future__ import annotations

import hashlib
import json
from collections.abc import Mapping
from typing import Any


def canonical_case_json(fields: Mapping[str, Any]) -> str:
    """Serialize case-defining fields deterministically."""
    return json.dumps(fields, ensure_ascii=False, separators=(",", ":"), sort_keys=True)


def case_id(fields: Mapping[str, Any]) -> str:
    """Return a content-addressed identifier for a complete case definition."""
    payload = canonical_case_json(fields).encode("utf-8")
    return f"case_{hashlib.sha256(payload).hexdigest()}"
