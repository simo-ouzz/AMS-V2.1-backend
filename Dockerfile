# =============================================================================
# inventotrackV2 - Dev/Testing Dockerfile
# Python 3.12 slim — backend only (no frontend, no nginx)
# =============================================================================

FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    DEBIAN_FRONTEND=noninteractive

# System dependencies needed for psycopg2 and healthcheck
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    postgresql-client \
    libpq-dev \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Non-root user
RUN useradd --create-home --shell /bin/bash appuser

WORKDIR /app

# Install Python deps first (layer caching)
COPY requirements/ requirements/
RUN pip install --no-cache-dir -r requirements/dev.txt

# Copy application code
COPY --chown=appuser:appuser . .

# Directories & permissions
RUN mkdir -p /app/static /app/media \
    && chown -R appuser:appuser /app \
    && chmod +x /app/entrypoint.sh

USER appuser

ENV DJANGO_SETTINGS_MODULE=config.settings.dev

EXPOSE 8000

ENTRYPOINT ["/app/entrypoint.sh"]
CMD ["python", "manage.py", "runserver", "0.0.0.0:8000"]
