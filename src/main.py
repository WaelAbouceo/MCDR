import logging
import sys
import uuid

from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from contextlib import asynccontextmanager
from slowapi import Limiter
from slowapi.errors import RateLimitExceeded
from starlette.exceptions import HTTPException as StarletteHTTPException
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.responses import Response

from src.api.router import api_router, legacy_router
from src.config import get_settings
from src.core.rate_limit import get_client_ip, set_redis_client as set_rate_limit_redis
from src.core.token_store import set_redis_client as set_token_redis
from src.database import init_db, cx_engine, customer_engine, CxSessionLocal
from src.middleware.audit import AuditMiddleware

settings = get_settings()


# ─── Structured Logging ──────────────────────────────────────

def _configure_logging():
    root = logging.getLogger()
    root.setLevel(settings.log_level)
    root.handlers.clear()

    handler = logging.StreamHandler(sys.stdout)
    handler.setLevel(settings.log_level)

    if settings.is_production:
        try:
            from pythonjsonlogger.json import JsonFormatter
            formatter = JsonFormatter(
                fmt="%(asctime)s %(levelname)s %(name)s %(message)s",
                rename_fields={"asctime": "timestamp", "levelname": "level", "name": "logger"},
            )
        except ImportError:
            formatter = logging.Formatter("%(asctime)s %(levelname)s %(name)s %(message)s")
    else:
        formatter = logging.Formatter("%(asctime)s %(levelname)s %(name)s %(message)s")

    handler.setFormatter(formatter)
    root.addHandler(handler)


_configure_logging()
logger = logging.getLogger("mcdr")


# ─── Rate Limiter (slowapi) ──────────────────────────────────

limiter = Limiter(key_func=get_client_ip, default_limits=["200/minute"])


# ─── Lifespan ────────────────────────────────────────────────

@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("MCDR CX Platform starting (env=%s)", settings.environment)

    try:
        from src.core.redis_client import get_redis
        redis = await get_redis()
        set_rate_limit_redis(redis)
        set_token_redis(redis)
        logger.info("Redis connected — distributed rate limiting and token store active")
    except Exception as e:
        logger.warning("Redis unavailable — using in-memory fallback: %s", e)

    await init_db()
    logger.info("Database tables ready")
    yield
    logger.info("MCDR CX Platform shutting down — disposing connections")
    await cx_engine.dispose()
    await customer_engine.dispose()
    try:
        from src.core.redis_client import close_redis
        await close_redis()
    except Exception:
        pass
    logger.info("Shutdown complete")


app = FastAPI(
    title="MCDR CX Platform",
    description="Misr for Central Clearing, Depository and Registry — CX Operation API",
    version="2.0.0",
    lifespan=lifespan,
    docs_url="/docs" if settings.environment != "production" else None,
    redoc_url=None,
)
app.state.limiter = limiter


# ─── Security Headers ────────────────────────────────────────

class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        response = await call_next(request)
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-XSS-Protection"] = "1; mode=block"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        response.headers["Cache-Control"] = "no-store, no-cache, must-revalidate, private"
        response.headers["Pragma"] = "no-cache"
        response.headers["Content-Security-Policy"] = (
            "default-src 'self'; "
            "script-src 'self'; "
            "style-src 'self' 'unsafe-inline'; "
            "img-src 'self' data:; "
            "font-src 'self'; "
            "connect-src 'self'; "
            "frame-ancestors 'none'; "
            "base-uri 'self'; "
            "form-action 'self'"
        )
        response.headers["Permissions-Policy"] = (
            "camera=(), microphone=(), geolocation=(), payment=()"
        )
        if settings.environment == "production":
            response.headers["Strict-Transport-Security"] = (
                "max-age=31536000; includeSubDomains; preload"
            )
        return response


# ─── Request ID ──────────────────────────────────────────────

class RequestIdMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        request_id = request.headers.get("X-Request-ID") or str(uuid.uuid4())[:12]
        request.state.request_id = request_id
        response = await call_next(request)
        response.headers["X-Request-ID"] = request_id
        return response


# ─── Middleware stack (order matters: outermost first) ───────

app.add_middleware(SecurityHeadersMiddleware)
app.add_middleware(RequestIdMiddleware)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type", "X-Request-ID"],
)
app.add_middleware(AuditMiddleware)
app.include_router(api_router)
app.include_router(legacy_router)


# ─── Health Checks (registered before SPA catch-all so /health and /health/ready work) ─
@app.get("/health")
async def health():
    """Liveness check — process is running."""
    return {"status": "ok", "environment": settings.environment, "version": "2.0.0"}


@app.get("/health/ready")
async def readiness():
    """Readiness check — verifies DB connectivity."""
    checks = {}
    healthy = True

    try:
        async with CxSessionLocal() as session:
            result = await session.execute(
                __import__("sqlalchemy").text("SELECT 1")
            )
            result.scalar()
            checks["cx_database"] = "ok"
    except Exception as e:
        logger.error("CX database health check failed: %s", e)
        checks["cx_database"] = "unavailable"
        healthy = False

    try:
        import sqlite3
        conn = sqlite3.connect(settings.mcdr_core_db_path, timeout=5)
        conn.execute("SELECT 1")
        conn.close()
        checks["core_database"] = "ok"
    except Exception as e:
        logger.error("Core database health check failed: %s", e)
        checks["core_database"] = "unavailable"
        healthy = False

    try:
        from src.core.redis_client import get_redis
        redis = await get_redis()
        await redis.ping()
        checks["redis"] = "ok"
    except Exception:
        checks["redis"] = "unavailable (non-critical)"

    status_code = 200 if healthy else 503
    return JSONResponse(
        status_code=status_code,
        content={"status": "ok" if healthy else "degraded", "checks": checks},
    )


# ─── Serve frontend SPA (when running in Docker / single container) ─
def _frontend_index_path() -> Path | None:
    """Resolve frontend dist path (works from /app in Docker or repo root locally)."""
    for base in (
        Path(__file__).resolve().parent.parent,
        Path("/app"),
    ):
        index = base / "frontend" / "dist" / "index.html"
        if index.is_file():
            return index
    return None


_frontend_index = _frontend_index_path()
if _frontend_index is not None:
    _frontend_dist = _frontend_index.parent
    _assets = _frontend_dist / "assets"
    if _assets.is_dir():
        app.mount("/assets", StaticFiles(directory=str(_assets)), name="assets")

    # Explicit routes for logo and favicon so they always serve from dist (avoids path/cache issues)
    _logo = _frontend_dist / "mcdr-logo.svg"
    _favicon = _frontend_dist / "favicon.svg"
    if _logo.is_file():
        @app.get("/mcdr-logo.svg", include_in_schema=False)
        async def serve_logo():
            return FileResponse(str(_logo))
    if _favicon.is_file():
        @app.get("/favicon.svg", include_in_schema=False)
        async def serve_favicon():
            return FileResponse(str(_favicon))

    @app.get("/", include_in_schema=False)
    async def serve_root():
        return FileResponse(str(_frontend_index))

    @app.get("/{full_path:path}", include_in_schema=False)
    async def serve_spa(full_path: str):
        if full_path.startswith("api"):
            return JSONResponse(status_code=404, content={"detail": "Not found"})
        # Serve static files from dist root (logo, favicon, etc.) so they load on EC2
        safe_path = full_path.split("?")[0].lstrip("/")
        if ".." in safe_path:
            return FileResponse(str(_frontend_index))
        static_file = (_frontend_dist / safe_path).resolve()
        base = _frontend_dist.resolve()
        if static_file.is_file() and base in static_file.parents:
            return FileResponse(str(static_file))
        return FileResponse(str(_frontend_index))
else:
    @app.get("/", include_in_schema=False)
    async def serve_root_missing():
        return JSONResponse(
            status_code=503,
            content={"detail": "Frontend not built. Run: cd frontend && npm run build"},
        )

# ─── Global Exception Handlers ──────────────────────────────

def _error_response(status_code: int, code: str, message: str, request_id: str, details=None):
    content = {"error": {"code": code, "message": message, "request_id": request_id}}
    if details is not None:
        content["error"]["details"] = details
    return JSONResponse(status_code=status_code, content=content)


@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception):
    request_id = getattr(request.state, "request_id", "unknown")
    logger.error(
        "Unhandled error [request_id=%s] %s: %s",
        request_id, type(exc).__name__, exc,
        exc_info=True,
    )
    return _error_response(500, "INTERNAL_ERROR",
                           "An unexpected error occurred. Please try again.", request_id)


@app.exception_handler(StarletteHTTPException)
async def http_exception_handler(request: Request, exc: StarletteHTTPException):
    request_id = getattr(request.state, "request_id", "unknown")
    return _error_response(exc.status_code, f"HTTP_{exc.status_code}",
                           str(exc.detail), request_id)


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    request_id = getattr(request.state, "request_id", "unknown")
    return _error_response(422, "VALIDATION_ERROR",
                           "Request validation failed", request_id,
                           details=exc.errors())


@app.exception_handler(RateLimitExceeded)
async def rate_limit_handler(request: Request, exc: RateLimitExceeded):
    request_id = getattr(request.state, "request_id", "unknown")
    return _error_response(429, "RATE_LIMIT_EXCEEDED",
                           "Too many requests. Please slow down.", request_id)


