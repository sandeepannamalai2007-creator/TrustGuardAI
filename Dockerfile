# Production Dockerfile for TrustGuard AI
FROM python:3.11-slim

# Prevent Python from writing .pyc files and enable unbuffered stdout/stderr logging
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

# Install system dependencies (curl required for container healthcheck)
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    build-essential \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Create dedicated non-root user and group
RUN groupadd -r trustguard && useradd -r -g trustguard -m -d /home/trustguard trustguard

WORKDIR /app

# Copy and install Python dependencies
COPY requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir -r /app/requirements.txt

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
