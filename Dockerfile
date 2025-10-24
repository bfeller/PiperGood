# syntax=docker/dockerfile:1.7-labs

FROM python:3.11-slim AS base

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=0

WORKDIR /app

# System dependencies for Piper
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Install Python deps with cache mounts for speed
COPY requirements.txt /app/requirements.txt
RUN --mount=type=cache,target=/root/.cache/pip \
    pip install --upgrade pip && pip install -r /app/requirements.txt

# Copy app code
COPY app /app/app

# Copy voice models
COPY voice /app/voice

EXPOSE 8000

ENV VOICE_MODEL=/app/voice/edwin.onnx
ENV VOICE_CONFIG=/app/voice/edwin.onnx.json

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
