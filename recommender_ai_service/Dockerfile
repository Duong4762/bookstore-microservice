FROM python:3.11-slim

# Build args
ARG DJANGO_SETTINGS_MODULE=config.settings.dev

# System deps
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    g++ \
    curl \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Install Python dependencies (cached layer)
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Create required directories
RUN mkdir -p ml/checkpoints ml/data

# Environment
ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1
ENV DJANGO_SETTINGS_MODULE=${DJANGO_SETTINGS_MODULE}

EXPOSE 8000

# Dev default: Django dev server
# Production: gunicorn via docker-compose override
CMD ["python", "manage.py", "runserver", "0.0.0.0:8000"]
