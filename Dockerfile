FROM mcr.microsoft.com/playwright/python:v1.42.0-jammy

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    ffmpeg git && \
    apt-get clean && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Install Python dependencies
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt && \
    playwright install chromium

# Copy application code
COPY . .

ENV PYTHONUNBUFFERED=1

CMD ["python", "stream_url.py"]
