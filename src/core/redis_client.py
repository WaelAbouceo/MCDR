"""Shared Redis connection for rate limiting, token revocation, and caching."""

import logging
from typing import Optional

import redis.asyncio as aioredis

from src.config import get_settings

logger = logging.getLogger("mcdr.redis")

_pool: Optional[aioredis.Redis] = None


async def get_redis() -> aioredis.Redis:
    global _pool
    if _pool is None:
        settings = get_settings()
        _pool = aioredis.from_url(
            settings.redis_url,
            decode_responses=True,
            socket_connect_timeout=5,
            retry_on_timeout=True,
        )
        logger.info("Redis connection pool created: %s", settings.redis_url)
    return _pool


async def close_redis() -> None:
    global _pool
    if _pool is not None:
        await _pool.aclose()
        _pool = None
        logger.info("Redis connection pool closed")
