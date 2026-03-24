# ============================================================================
# Grin's Irrigation Platform - Production Dockerfile
# Compatible with Railway, Render, and other cloud platforms
# ============================================================================

FROM python:3.12-slim-bookworm

# Install system dependencies
# - libmagic1: required by python-magic for file type detection
# - libpango-1.0-0, libpangocairo-1.0-0, libgdk-pixbuf-2.0-0, libffi-dev, libcairo2: required by WeasyPrint for PDF rendering
RUN apt-get update && apt-get install -y \
    --no-install-recommends \
    ca-certificates \
    curl \
    libmagic1 \
    libpango-1.0-0 \
    libpangocairo-1.0-0 \
    libgdk-pixbuf-2.0-0 \
    libffi-dev \
    libcairo2 \
    && rm -rf /var/lib/apt/lists/*

# Install uv for fast package management
RUN pip install uv

# Create non-root user for security
RUN groupadd -r appuser && useradd -r -g appuser appuser

WORKDIR /app

# Copy dependency files first (better layer caching)
COPY pyproject.toml uv.lock README.md ./

# Install dependencies
RUN uv sync --frozen --no-install-project --no-dev

# Copy application code
COPY . /app

# Install project
RUN uv sync --frozen --no-editable --no-dev

# Create output directories with proper permissions
RUN mkdir -p /app/output /app/logs && \
    chown -R appuser:appuser /app

# Switch to non-root user
USER appuser

# Activate virtual environment
ENV PATH="/app/.venv/bin:$PATH" \
    PYTHONPATH="/app/src:$PYTHONPATH" \
    PYTHONUNBUFFERED=1

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# Expose application port
EXPOSE 8000

# Run migrations then start application
CMD ["sh", "-c", "/app/.venv/bin/alembic upgrade head && /app/.venv/bin/uvicorn grins_platform.main:app --host 0.0.0.0 --port 8000"]
