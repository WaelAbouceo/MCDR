# ── Stage 1: Build frontend ──────────────────────────────────
FROM node:20-alpine AS frontend-build
WORKDIR /build
COPY frontend/package.json frontend/package-lock.json* ./
RUN npm ci --ignore-scripts 2>/dev/null || npm install
COPY frontend/ .
RUN npm run build && test -f /build/dist/index.html || (echo "Frontend build failed: no index.html" && exit 1)
# Ensure public assets (logo, favicon) are in dist — Vite may not copy them in all setups
RUN cp -r public/. dist/ 2>/dev/null || true

# ── Stage 2: Python API ─────────────────────────────────────
FROM python:3.12-slim AS runtime

RUN groupadd -r mcdr && useradd -r -g mcdr -s /usr/sbin/nologin mcdr

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY src/ src/
COPY db/ db/

COPY --from=frontend-build /build/dist/ frontend/dist/
RUN test -f /app/frontend/dist/index.html || (echo "Frontend not in image" && exit 1)

RUN chown -R mcdr:mcdr /app

USER mcdr

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/health')" || exit 1

CMD ["gunicorn", "src.main:app", \
     "-k", "uvicorn.workers.UvicornWorker", \
     "-w", "4", \
     "-b", "0.0.0.0:8000", \
     "--timeout", "120", \
     "--graceful-timeout", "30", \
     "--access-logfile", "-", \
     "--error-logfile", "-", \
     "--proxy-protocol", \
     "--forwarded-allow-ips", "*"]
