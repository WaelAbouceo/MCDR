"""In-memory rate limiter for login brute-force protection.

Tracks failed login attempts per IP and per username.
Locks out after MAX_ATTEMPTS within the WINDOW.
"""

import threading
import time
from collections import defaultdict

MAX_ATTEMPTS = 5
WINDOW_SECONDS = 300  # 5 minutes
LOCKOUT_SECONDS = 600  # 10 minutes lockout after exceeding

_lock = threading.Lock()
_attempts: dict[str, list[float]] = defaultdict(list)
_lockouts: dict[str, float] = {}


def _clean(key: str, now: float) -> None:
    _attempts[key] = [t for t in _attempts[key] if now - t < WINDOW_SECONDS]


def is_locked_out(key: str) -> bool:
    now = time.time()
    with _lock:
        lockout_until = _lockouts.get(key, 0)
        if now < lockout_until:
            return True
        if now >= lockout_until and key in _lockouts:
            del _lockouts[key]
            _attempts[key] = []
        return False


def record_failure(ip: str, username: str) -> bool:
    """Record a failed attempt. Returns True if account is now locked out."""
    now = time.time()
    with _lock:
        for key in [f"ip:{ip}", f"user:{username}"]:
            _clean(key, now)
            _attempts[key].append(now)
            if len(_attempts[key]) >= MAX_ATTEMPTS:
                _lockouts[key] = now + LOCKOUT_SECONDS
                return True
    return False


def record_success(ip: str, username: str) -> None:
    """Clear attempts on successful login."""
    with _lock:
        for key in [f"ip:{ip}", f"user:{username}"]:
            _attempts.pop(key, None)
            _lockouts.pop(key, None)


def remaining_attempts(ip: str, username: str) -> int:
    now = time.time()
    with _lock:
        worst = 0
        for key in [f"ip:{ip}", f"user:{username}"]:
            _clean(key, now)
            worst = max(worst, len(_attempts[key]))
        return max(0, MAX_ATTEMPTS - worst)
