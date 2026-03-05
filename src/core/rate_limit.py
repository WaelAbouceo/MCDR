"""Redis-backed rate limiting for login brute-force and general API protection.

Falls back to in-memory limiting when Redis is unavailable (development).
"""

import logging
import threading
import time
from collections import defaultdict
from typing import Optional

logger = logging.getLogger("mcdr.rate_limit")

MAX_ATTEMPTS = 5
WINDOW_SECONDS = 300
LOCKOUT_SECONDS = 600

_redis = None


def set_redis_client(client) -> None:
    """Inject the async Redis client (called during app startup)."""
    global _redis
    _redis = client


# ─── In-memory fallback (single-process dev) ─────────────────

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


# ─── Redis-backed login limiter (multi-worker safe) ──────────

async def is_locked_out_async(key: str) -> bool:
    if _redis is None:
        return is_locked_out(key)
    try:
        lockout = await _redis.get(f"lockout:{key}")
        return lockout is not None
    except Exception as e:
        logger.warning("Redis unavailable for rate check, falling back to memory: %s", e)
        return is_locked_out(key)


async def record_failure_async(ip: str, username: str) -> bool:
    if _redis is None:
        return record_failure(ip, username)
    try:
        locked = False
        for key in [f"ip:{ip}", f"user:{username}"]:
            pipe = _redis.pipeline()
            rkey = f"login_attempts:{key}"
            now = time.time()
            await pipe.zadd(rkey, {str(now): now})
            await pipe.zremrangebyscore(rkey, 0, now - WINDOW_SECONDS)
            await pipe.zcard(rkey)
            await pipe.expire(rkey, WINDOW_SECONDS)
            results = await pipe.execute()
            count = results[2]
            if count >= MAX_ATTEMPTS:
                await _redis.setex(f"lockout:{key}", LOCKOUT_SECONDS, "1")
                locked = True
        return locked
    except Exception as e:
        logger.warning("Redis unavailable for rate record, falling back to memory: %s", e)
        return record_failure(ip, username)


async def record_success_async(ip: str, username: str) -> None:
    if _redis is None:
        return record_success(ip, username)
    try:
        pipe = _redis.pipeline()
        for key in [f"ip:{ip}", f"user:{username}"]:
            await pipe.delete(f"login_attempts:{key}")
            await pipe.delete(f"lockout:{key}")
        await pipe.execute()
    except Exception as e:
        logger.warning("Redis unavailable for rate clear, falling back to memory: %s", e)
        record_success(ip, username)


# ─── General API rate limit key function (for slowapi) ───────

def get_client_ip(request) -> str:
    forwarded = request.headers.get("x-forwarded-for", "")
    if forwarded:
        ip = forwarded.split(",")[0].strip()
        if ip and len(ip) <= 45:
            return ip
    return request.client.host if request.client else "unknown"
