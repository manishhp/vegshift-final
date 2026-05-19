from __future__ import annotations

import json
from pathlib import Path
from threading import Lock
from typing import Any, Dict


DATA_PATH = Path(__file__).resolve().parents[1] / "data" / "output" / "frontend_payload.json"
EVIDENCE_PATH = Path(__file__).resolve().parents[1] / "docs" / "evidence_sources.json"

_payload_cache: Dict[str, Any] | None = None
_lock = Lock()


def _inject_evidence(payload: Dict[str, Any]) -> Dict[str, Any]:
    """Overlay evidence from the tracked docs/evidence_sources.json into the payload."""
    if not EVIDENCE_PATH.exists():
        return payload
    with EVIDENCE_PATH.open("r", encoding="utf-8") as f:
        evidence: Dict[str, Any] = json.load(f)
    city_detail = payload.get("city_detail", {})
    for city, items in evidence.items():
        if city in city_detail:
            city_detail[city]["evidence"] = items
    summary = payload.get("summary", [])
    for entry in summary:
        city = entry.get("city", "")
        items = evidence.get(city, [])
        entry["evidence_missing"] = not items or all(i.get("is_placeholder") for i in items)
    return payload


def load_payload() -> Dict[str, Any]:
    if not DATA_PATH.exists():
        raise FileNotFoundError(
            f"Frontend payload not found at {DATA_PATH}. Run tools/build_frontend_payload.py first."
        )
    with DATA_PATH.open("r", encoding="utf-8") as handle:
        payload = json.load(handle)
    return _inject_evidence(payload)


def get_payload() -> Dict[str, Any]:
    global _payload_cache
    if _payload_cache is None:
        with _lock:
            if _payload_cache is None:
                _payload_cache = load_payload()
    return _payload_cache


def reload_payload() -> Dict[str, Any]:
    global _payload_cache
    with _lock:
        _payload_cache = load_payload()
    return _payload_cache
