"""Cross-process chaos flags for OpsAI stage-2 demo (local only).

Admin (8081) and Portal (8085) run as separate uvicorn processes; in-memory
state is not shared. Persist portal-500 expiry to a JSON file both can read.
"""

from __future__ import annotations

import json
import threading
import time
from pathlib import Path

_lock = threading.Lock()
_STATE_FILE = Path(__file__).resolve().parents[2] / "data" / "chaos_state.json"


def _load_portal_500_until() -> float:
    try:
        if not _STATE_FILE.is_file():
            return 0.0
        payload = json.loads(_STATE_FILE.read_text(encoding="utf-8"))
        return float(payload.get("portal_500_until") or 0.0)
    except (OSError, json.JSONDecodeError, TypeError, ValueError):
        return 0.0


def _save_portal_500_until(until: float) -> None:
    _STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
    payload = {"portal_500_until": until, "updated_at": time.time()}
    _STATE_FILE.write_text(json.dumps(payload), encoding="utf-8")


def set_portal_500(enable: bool, duration_seconds: int = 180) -> None:
    with _lock:
        if enable:
            _save_portal_500_until(time.time() + max(duration_seconds, 1))
        else:
            _save_portal_500_until(0.0)


def portal_500_active() -> bool:
    with _lock:
        until = _load_portal_500_until()
        if until <= 0:
            return False
        if time.time() >= until:
            _save_portal_500_until(0.0)
            return False
        return True
