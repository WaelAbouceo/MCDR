"""Comprehensive request-level audit logging middleware.

Logs every API request with: user identity, method, path, query params,
request body (for writes), response status, IP address, and timing.
Designed for regulated industries where full traceability is required.
"""

import json
import logging
import re
import time

from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.requests import Request
from starlette.responses import Response

from src.database import CxSessionLocal
from src.models.audit import AuditLog

logger = logging.getLogger("mcdr.audit")

SKIP_PATHS = {"/api/health", "/health", "/health/ready", "/docs", "/openapi.json", "/favicon.ico"}

SENSITIVE_FIELDS = frozenset({
    "password", "hashed_password", "new_password", "old_password", "confirm_password",
    "access_token", "refresh_token", "token", "api_key", "apikey",
    "secret", "secret_key", "client_secret",
    "authorization", "cookie",
    "credit_card", "card_number", "cvv", "ssn", "national_id",
    "pin", "otp", "verification_code",
})

_RESOURCE_ID_PATTERN = re.compile(
    r"/api/(?:cx/)?(?:cases|calls|escalations|investors|agents|users|qa/evaluations|qa/case|qa/agent|sla/breaches)/(\d+)"
)


def _extract_resource_id(path: str) -> int | None:
    m = _RESOURCE_ID_PATTERN.search(path)
    return int(m.group(1)) if m else None


def _get_client_ip(request: Request) -> str | None:
    forwarded = request.headers.get("x-forwarded-for")
    if forwarded:
        ip = forwarded.split(",")[0].strip()
        if ip and len(ip) <= 45:
            return ip
    return request.client.host if request.client else None


def _sanitize_deep(data, depth: int = 0):
    """Recursively sanitize sensitive fields at any nesting level."""
    if depth > 5:
        return "[nested]"
    if isinstance(data, dict):
        return {
            k: "***" if k.lower() in SENSITIVE_FIELDS else _sanitize_deep(v, depth + 1)
            for k, v in data.items()
        }
    if isinstance(data, list):
        return [_sanitize_deep(item, depth + 1) for item in data[:20]]
    return data


class AuditMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        if request.url.path in SKIP_PATHS or not request.url.path.startswith("/api/"):
            return await call_next(request)

        body_bytes = b""
        if request.method in ("POST", "PUT", "PATCH", "DELETE"):
            body_bytes = await request.body()

        start = time.monotonic()
        response = await call_next(request)
        elapsed_ms = round((time.monotonic() - start) * 1000)

        try:
            user_id = getattr(request.state, "user_id", None)
            username = getattr(request.state, "username", None)
            role = getattr(request.state, "role", None)

            resource_id = _extract_resource_id(request.url.path)

            query_str = str(request.url.query) if request.url.query else None

            body_summary = None
            if body_bytes:
                try:
                    parsed = json.loads(body_bytes)
                    parsed = _sanitize_deep(parsed)
                    body_summary = json.dumps(parsed)[:1000]
                except (json.JSONDecodeError, UnicodeDecodeError):
                    body_summary = "(binary or unparsable)"

            detail_parts = [
                f"status={response.status_code}",
                f"elapsed={elapsed_ms}ms",
            ]
            if username:
                detail_parts.append(f"user={username}")
            if role:
                detail_parts.append(f"role={role}")
            if query_str:
                detail_parts.append(f"query={query_str}")
            if body_summary:
                detail_parts.append(f"body={body_summary}")

            detail = " | ".join(detail_parts)

            ip = _get_client_ip(request)

            async with CxSessionLocal() as session:
                session.add(
                    AuditLog(
                        user_id=user_id,
                        action=request.method,
                        resource=request.url.path,
                        resource_id=resource_id,
                        detail=detail,
                        ip_address=ip,
                    )
                )
                await session.commit()
        except Exception as e:
            logger.error("Audit log write failed: %s", e, exc_info=True)

        return response
