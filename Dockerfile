# Lightweight default image for continuous terminal livestreaming
FROM python:3.11-slim-bookworm

# Install system dependencies for FFmpeg, Chromium, and Xvfb capture
RUN apt-get update && apt-get install -y --no-install-recommends \
    ffmpeg git tini xvfb fonts-liberation fonts-noto-core \
    libglib2.0-0 libnss3 libnspr4 libdbus-1-3 libatk1.0-0 libatk-bridge2.0-0 \
    libcups2 libdrm2 libxkbcommon0 libatspi2.0-0 libxcomposite1 libxdamage1 \
    libxfixes3 libxrandr2 libgbm1 libasound2 libpango-1.0-0 libcairo2 libgtk-3-0 \
    libx11-xcb1 libxcursor1 libxi6 libxrender1 libxtst6 ca-certificates && \
    apt-get clean && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Install Python dependencies for the streaming path only
COPY requirements-stream.txt ./
ENV PLAYWRIGHT_BROWSERS_PATH=/ms-playwright
RUN pip install --no-cache-dir -r requirements-stream.txt
RUN python -m playwright install chromium && chmod -R a+rX /ms-playwright

# Copy application code
RUN groupadd --system stream && \
    useradd --system --gid stream --create-home --home-dir /home/stream stream
COPY --chown=stream:stream . .

# Create writable runtime directories before dropping privileges
RUN mkdir -p /app/.cache /app/audio/tts /tmp/stream-runtime && \
    chown -R stream:stream /app/.cache /app/audio/tts /tmp/stream-runtime && \
    chmod 700 /tmp/stream-runtime

ENV PYTHONUNBUFFERED=1
ENV HF_HOME=/app/.cache/huggingface
ENV HOME=/home/stream
ENV XDG_RUNTIME_DIR=/tmp/stream-runtime

USER stream
ENTRYPOINT ["tini", "--"]
CMD ["python", "stream_terminal.py"]
