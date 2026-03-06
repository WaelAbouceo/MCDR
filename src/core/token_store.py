"""Token management: refresh tokens, token revocation, and token families.

Uses Redis when available, falls back to in-memory for development.
"""

import logging
import secrets
import time
from datetime import datetime, timedelta, timezone
from typing import Optional

logger = logging.getLogger("mcdr.tokens")

REFRESH_TOKEN_BYTES = 32
REFRESH_TOKEN_EXPIRE_DAYS = 7
REFRESH_TOKEN_MAX_USES = 1  # single-use rotation

_redis = None

_mem_refresh: dict[str, dict] = {}
_mem_revoked: set[str] = set()


def set_redis_client(client) -> None:
    global _redis
    _redis = client


def generate_refresh_token() -> str:
    return secrets.token_urlsafe(REFRESH_TOKEN_BYTES)


# ─── Refresh token storage ───────────────────────────────────

async def store_refresh_token(token: str, user_id: int, family_id: str) -> None:
    """Store a refresh token linked to a user and token family."""
    data = {
        "user_id": str(user_id),
        "family_id": family_id,
        "created_at": datetime.now(timezone.utc).isoformat(),
    }
    ttl = REFRESH_TOKEN_EXPIRE_DAYS * 86400

    if _redis:
        try:
            key = f"refresh:{token}"
            await _redis.hset(key, mapping=data)
            await _redis.expire(key, ttl)
            await _redis.sadd(f"user_tokens:{user_id}", token)
            await _redis.expire(f"user_tokens:{user_id}", ttl)
            return
        except Exception as e:
            logger.debug("Redis unavailable for refresh store: %s", e)

    _mem_refresh[token] = {**data, "expires_at": time.time() + ttl}


async def validate_refresh_token(token: str) -> Optional[dict]:
    """Validate and consume a refresh token (single-use). Returns user data or None."""
    if _redis:
        try:
            key = f"refresh:{token}"
            data = await _redis.hgetall(key)
            if not data:
                return None
            await _redis.delete(key)
            await _redis.srem(f"user_tokens:{data['user_id']}", token)
            return data
        except Exception as e:
            logger.debug("Redis unavailable for refresh validate: %s", e)

    data = _mem_refresh.pop(token, None)
    if not data:
        return None
    if data.get("expires_at", 0) < time.time():
        return None
    return data


async def invalidate_family(user_id: int, family_id: str) -> None:
    """Invalidate all refresh tokens in a family (reuse detection)."""
    if _redis:
        try:
            tokens = await _redis.smembers(f"user_tokens:{user_id}")
            pipe = _redis.pipeline()
            for t in tokens:
                key = f"refresh:{t}"
                data = await _redis.hgetall(key)
                if data and data.get("family_id") == family_id:
                    await pipe.delete(key)
                    await pipe.srem(f"user_tokens:{user_id}", t)
            await pipe.execute()
            logger.warning("Token family %s invalidated for user %d (reuse detected)", family_id, user_id)
            return
        except Exception as e:
            logger.debug("Redis unavailable for family invalidation: %s", e)

    to_remove = [k for k, v in _mem_refresh.items()
                 if v.get("family_id") == family_id and v.get("user_id") == str(user_id)]
    for k in to_remove:
        _mem_refresh.pop(k, None)
    logger.warning("Token family %s invalidated for user %d (reuse detected)", family_id, user_id)


# ─── Access token revocation (logout) ────────────────────────

async def revoke_access_token(jti: str, ttl: int) -> None:
    """Add a JWT ID to the revocation blocklist."""
    if _redis:
        try:
            await _redis.setex(f"revoked:{jti}", ttl, "1")
            return
        except Exception as e:
            logger.debug("Redis unavailable for token revoke: %s", e)

    _mem_revoked.add(jti)


async def is_token_revoked(jti: str) -> bool:
    if _redis:
        try:
            return await _redis.exists(f"revoked:{jti}") > 0
        except Exception as e:
            logger.debug("Redis unavailable for revocation check: %s", e)

    return jti in _mem_revoked


async def revoke_all_user_tokens(user_id: int) -> int:
    """Revoke all refresh tokens for a user (forced logout)."""
    count = 0
    if _redis:
        try:
            tokens = await _redis.smembers(f"user_tokens:{user_id}")
            if tokens:
                pipe = _redis.pipeline()
                for t in tokens:
                    await pipe.delete(f"refresh:{t}")
                await pipe.delete(f"user_tokens:{user_id}")
                await pipe.execute()
                count = len(tokens)
            return count
        except Exception as e:
            logger.debug("Redis unavailable for user token revocation: %s", e)

    to_remove = [k for k, v in _mem_refresh.items() if v.get("user_id") == str(user_id)]
    for k in to_remove:
        _mem_refresh.pop(k, None)
    return len(to_remove)
