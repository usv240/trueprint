# Trueprint — single container that serves the landing, the app, and the API.
FROM python:3.12-slim

# OpenCV (headless) + Pillow runtime deps
RUN apt-get update && apt-get install -y --no-install-recommends \
        libglib2.0-0 libgl1 \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app
COPY backend/requirements.txt ./requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

COPY backend ./backend
COPY frontend ./frontend
COPY assets/samples ./assets/samples
COPY assets/CREDITS.md ./assets/CREDITS.md

ENV PYTHONUNBUFFERED=1
EXPOSE 8000
# Host provides $PORT (Render/Railway); default 8000 locally.
CMD ["sh", "-c", "uvicorn backend.app.main:app --host 0.0.0.0 --port ${PORT:-8000}"]
