# GPU-enabled image for Chroma-4B TTS (requires ~24GB VRAM)
FROM nvidia/cuda:12.1.0-cudnn8-devel-ubuntu22.04

# Install system dependencies including Python and audio libs
RUN apt-get update && apt-get install -y --no-install-recommends \
    python3.11 python3.11-venv python3-pip \
    ffmpeg git libsndfile1 && \
    apt-get clean && rm -rf /var/lib/apt/lists/*

# Set python3.11 as default
RUN update-alternatives --install /usr/bin/python3 python3 /usr/bin/python3.11 1 && \
    update-alternatives --install /usr/bin/python python /usr/bin/python3.11 1

WORKDIR /app

# Install Python dependencies
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Create directories
RUN mkdir -p /app/audio/tts

ENV PYTHONUNBUFFERED=1
ENV HF_HOME=/app/.cache/huggingface

CMD ["python", "stream_url.py"]
