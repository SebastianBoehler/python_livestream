# Lightweight default image for continuous livestreaming
FROM python:3.11-slim-bookworm

# Install system dependencies for FFmpeg, Chromium, and Xvfb capture
RUN apt-get update && apt-get install -y --no-install-recommends \
    ffmpeg git xvfb \
    libglib2.0-0 libnss3 libnspr4 libdbus-1-3 libatk1.0-0 libatk-bridge2.0-0 \
    libcups2 libdrm2 libxkbcommon0 libatspi2.0-0 libxcomposite1 libxdamage1 \
    libxfixes3 libxrandr2 libgbm1 libasound2 libpango-1.0-0 libcairo2 libgtk-3-0 \
    libx11-xcb1 libxcursor1 libxi6 libxrender1 libxtst6 ca-certificates && \
    apt-get clean && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Install Python dependencies for the streaming path only
COPY requirements-stream.txt ./
RUN pip install --no-cache-dir -r requirements-stream.txt
RUN python -m playwright install chromium

# Copy application code
COPY . .

# Create directories
RUN mkdir -p /app/audio/tts

ENV PYTHONUNBUFFERED=1
ENV HF_HOME=/app/.cache/huggingface

CMD ["python", "stream_url.py"]
