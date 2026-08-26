# Multi-Stage Production Dockerfile for TrustGuard AI

# -----------------------------------------------------------------------------
# Stage 1: Build & Dependencies Compiler Stage
# -----------------------------------------------------------------------------
FROM python:3.11-slim AS builder

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

# Install build tools required to compile C extensions (e.g. psycopg2)
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /build

COPY requirements.txt /build/requirements.txt
RUN pip install --no-cache-dir --prefix=/install -r /build/requirements.txt


# -----------------------------------------------------------------------------
# Stage 2: Final Lean Production Runtime Stage
# -----------------------------------------------------------------------------
FROM python:3.11-slim AS runtime

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

# Install only essential runtime packages (curl for healthcheck, libpq5 for PostgreSQL driver)
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    libpq5 \
    && rm -rf /var/lib/apt/lists/*

# Copy compiled Python packages from builder stage
COPY --from=builder /install /usr/local

# Create dedicated non-root user and group
RUN groupadd -r trustguard && useradd -r -g trustguard -m -d /home/trustguard trustguard

WORKDIR /app

# Ensure ML artifacts storage directory structure exists with dedicated write permissions for non-root user
RUN mkdir -p /app/ml/artifacts/production /app/ml/artifacts/candidates /app/ml/artifacts/archive \
    && chown -R trustguard:trustguard /app

# Copy application source, migrations, and entrypoint script
COPY --chown=trustguard:trustguard backend /app/backend
COPY --chown=trustguard:trustguard ml /app/ml
COPY --chown=trustguard:trustguard alembic /app/alembic
COPY --chown=trustguard:trustguard alembic.ini /app/alembic.ini
COPY --chown=trustguard:trustguard docker-entrypoint.sh /app/docker-entrypoint.sh

RUN chmod +x /app/docker-entrypoint.sh

# Container Healthcheck using /live probe
HEALTHCHECK --interval=15s --timeout=5s --start-period=10s --retries=3 \
    CMD curl -f http://localhost:8000/live || exit 1

EXPOSE 8000

# Run container under non-root user
USER trustguard

ENTRYPOINT ["/app/docker-entrypoint.sh"]
