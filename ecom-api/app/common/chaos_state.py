"""In-memory chaos flags for OpsAI stage-2 demo (local only)."""

from __future__ import annotations

import threading
import time

_lock = threading.Lock()
_portal_500_until: float = 0.0


def set_portal_500(enable: bool, duration_seconds: int = 180) -> None:
    global _portal_500_until
    with _lock:
        if enable:
            _portal_500_until = time.time() + max(duration_seconds, 1)
        else:
            _portal_500_until = 0.0


def portal_500_active() -> bool:
    with _lock:
        if _portal_500_until <= 0:
            return False
        if time.time() >= _portal_500_until:
            _portal_500_until = 0.0
            return False
        return True
