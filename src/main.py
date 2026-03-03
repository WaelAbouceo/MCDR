import logging
import uuid

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from contextlib import asynccontextmanager
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.responses import Response

from src.api.router import api_router
from src.config import get_settings
from src.database import init_db, CxSessionLocal
from src.middleware.audit import AuditMiddleware

settings = get_settings()

logging.basicConfig(
    level=settings.log_level,
    format="%(asctime)s %(levelname)s %(name)s %(message)s",
)
logger = logging.getLogger("mcdr")


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("MCDR CX Platform starting (env=%s)", settings.environment)
    await init_db()
    logger.info("Database tables ready")
    yield
    logger.info("MCDR CX Platform shutting down")


app = FastAPI(
    title="MCDR CX Platform",
    description="Mobile Customer Dispute Resolution — CX Operation API",
    version="1.0.0",
    lifespan=lifespan,
    docs_url="/docs" if settings.environment != "production" else None,
    redoc_url=None,
)


# ─── Security Headers ────────────────────────────────────────────

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


# ─── Request ID ──────────────────────────────────────────────────

class RequestIdMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        request_id = request.headers.get("X-Request-ID") or str(uuid.uuid4())[:12]
        request.state.request_id = request_id
        response = await call_next(request)
        response.headers["X-Request-ID"] = request_id
        return response


# ─── Middleware stack (order matters: outermost first) ───────────

app.add_middleware(SecurityHeadersMiddleware)
app.add_middleware(RequestIdMiddleware)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PATCH", "DELETE", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type", "X-Request-ID"],
)
app.add_middleware(AuditMiddleware)
app.include_router(api_router)


# ─── Global Exception Handlers ──────────────────────────────────

@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception):
    request_id = getattr(request.state, "request_id", "unknown")
    logger.error(
        "Unhandled error [request_id=%s] %s: %s",
        request_id, type(exc).__name__, exc,
        exc_info=True,
    )
    return JSONResponse(
        status_code=500,
        content={
            "error": {
                "code": "INTERNAL_ERROR",
                "message": "An unexpected error occurred. Please try again.",
                "request_id": request_id,
            }
        },
    )


@app.exception_handler(422)
async def validation_exception_handler(request: Request, exc):
    request_id = getattr(request.state, "request_id", "unknown")
    return JSONResponse(
        status_code=422,
        content={
            "error": {
                "code": "VALIDATION_ERROR",
                "message": "Request validation failed",
                "details": exc.errors() if hasattr(exc, "errors") else str(exc),
                "request_id": request_id,
            }
        },
    )


# ─── Health Checks ───────────────────────────────────────────────

@app.get("/health")
async def health():
    """Liveness check — process is running."""
    return {"status": "ok", "environment": settings.environment}


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
        checks["cx_database"] = f"error: {e}"
        healthy = False

    import sqlite3
    try:
        conn = sqlite3.connect(settings.mcdr_core_db_path)
        conn.execute("SELECT 1")
        conn.close()
        checks["core_database"] = "ok"
    except Exception as e:
        checks["core_database"] = f"error: {e}"
        healthy = False

    status_code = 200 if healthy else 503
    return JSONResponse(
        status_code=status_code,
        content={"status": "ok" if healthy else "degraded", "checks": checks},
    )
