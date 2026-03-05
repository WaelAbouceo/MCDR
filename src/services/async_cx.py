"""Async wrapper for cx_data_service.

All sync SQLite operations are delegated to a thread pool via asyncio.to_thread(),
preventing the event loop from being blocked in async FastAPI handlers.

Usage in endpoints:
    from src.services.async_cx import cx
    case = await cx.create_case(agent_id=1, subject="test")
"""

import asyncio
import functools
import types

from src.services import cx_data_service


class _AsyncCxProxy:
    """Wraps every public function in cx_data_service with asyncio.to_thread()."""

    def __getattr__(self, name: str):
        attr = getattr(cx_data_service, name, None)
        if attr is None:
            raise AttributeError(f"cx_data_service has no attribute '{name}'")
        if callable(attr) and not name.startswith("_"):
            @functools.wraps(attr)
            async def _async_wrapper(*args, **kwargs):
                return await asyncio.to_thread(attr, *args, **kwargs)
            return _async_wrapper
        return attr


cx = _AsyncCxProxy()
