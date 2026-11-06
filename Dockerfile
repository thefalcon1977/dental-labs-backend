# Multi-stage Dockerfile for FastAPI application
# Stage 1: Builder - Install dependencies and build
FROM python:3.12-slim as builder

# Set environment variables
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PIP_DEFAULT_TIMEOUT=100

# Install system dependencies required for building Python packages
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Create and set working directory
WORKDIR /app

# Copy requirements file
COPY requirements/prod.txt requirements.txt

# Build wheels for runtime install
RUN python -m pip install --no-cache-dir --upgrade pip && \
    python -m pip wheel --no-cache-dir --wheel-dir /wheels -r requirements.txt

# Stage 2: Runtime - Minimal image with only runtime dependencies
FROM python:3.12-slim

# Set environment variables
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PATH="/home/appuser/.local/bin:$PATH" \
    PYTHONPATH="/app"

# Install runtime system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq5 \
    postgresql-client \
    netcat-openbsd \
    iputils-ping \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Create non-root user for security
RUN groupadd -r appuser && useradd -r -g appuser -u 1000 appuser \
    && mkdir -p /app /home/appuser \
    && chown -R appuser:appuser /app /home/appuser

# Set working directory
WORKDIR /app

# Copy pre-built wheels and install them
COPY --from=builder /wheels /wheels
COPY requirements/prod.txt requirements.txt

# Install Python dependencies as root (will switch to appuser later)
RUN python -m pip install --no-cache-dir --upgrade pip && \
    python -m pip install --no-cache-dir --no-index --find-links=/wheels -r requirements.txt && \
    rm -rf /root/.cache/pip /wheels

# Copy entrypoint script and make it executable
COPY --chown=appuser:appuser docker/entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

# Switch to non-root user
USER appuser

# Expose port (default FastAPI port)
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# Use entrypoint script
ENTRYPOINT ["/entrypoint.sh"]

# Default command
CMD ["python", "manage.py", "runserver"]
