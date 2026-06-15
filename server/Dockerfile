# TYPEFASTER server image.
# Build context must be the repository ROOT (it needs ./shared and ./server):
#   docker build -f server/Dockerfile -t typefaster-server .
FROM python:3.12-slim AS base

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

WORKDIR /app

# Install the shared package first (better layer caching), then the server.
COPY shared /app/shared
RUN pip install /app/shared

COPY server /app/server
RUN pip install /app/server

# Run as a non-root user.
RUN useradd --create-home --uid 10001 appuser
USER appuser

EXPOSE 8000

# Container-level healthcheck hits the readiness endpoint.
HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD python -c "import urllib.request,sys; sys.exit(0 if urllib.request.urlopen('http://127.0.0.1:8000/healthz').status==200 else 1)"

# uvicorn handles SIGTERM for graceful shutdown; --proxy-headers for the reverse
# proxy. --limit-concurrency caps in-flight requests so a flood returns 503
# instead of OOM-ing the 1 GB box; --timeout-keep-alive frees idle sockets.
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", \
     "--proxy-headers", "--forwarded-allow-ips", "*", \
     "--limit-concurrency", "200", "--timeout-keep-alive", "15"]
