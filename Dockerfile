# Use Python 3.11 slim as base image
FROM python:3.11-slim

# Set environment variables
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    DEBIAN_FRONTEND=noninteractive

# Install system dependencies, FFmpeg, and fonts
RUN apt-get update && apt-get install -y --no-install-recommends \
    ffmpeg \
    libsdl2-2.0-0 \
    libsdl2-mixer-2.0-0 \
    # Required fonts
    fonts-dejavu-core \
    # Required by Playwright
    libnss3 \
    libnspr4 \
    libatk1.0-0 \
    libatk-bridge2.0-0 \
    libcups2 \
    libdrm2 \
    libdbus-1-3 \
    libxkbcommon0 \
    libxcomposite1 \
    libxdamage1 \
    libxfixes3 \
    libxrandr2 \
    libgbm1 \
    libpango-1.0-0 \
    libcairo2 \
    libasound2 \
    libatspi2.0-0 \
    && rm -rf /var/lib/apt/lists/*

# Create and set working directory
WORKDIR /app

# Copy requirements first for better cache utilization
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Install Playwright and browsers with proper permissions
RUN mkdir -p /ms-playwright && \
    chown -R root:root /ms-playwright && \
    chmod -R 777 /ms-playwright && \
    PLAYWRIGHT_BROWSERS_PATH=/ms-playwright playwright install chromium --with-deps && \
    chmod -R 777 /ms-playwright

# Set Playwright path permanently
ENV PLAYWRIGHT_BROWSERS_PATH=/ms-playwright

# Copy application code
COPY . .

# Create audio directory with proper permissions
RUN mkdir -p /app/audio && chmod 777 /app/audio

# Run as non-root user for security
RUN groupadd -r appuser && useradd -r -g appuser -G audio,video appuser \
    && chown -R appuser:appuser /app
USER appuser

# Command to run the application
CMD ["python", "main.py"]
