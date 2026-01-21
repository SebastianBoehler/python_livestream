#!/bin/bash
# Deploy Chroma-4B TTS to GCloud VM with GPU
# Requires: gcloud CLI configured, Docker installed

set -e

# Configuration
PROJECT_ID="${GCLOUD_PROJECT_ID:-your-project-id}"
ZONE="${GCLOUD_ZONE:-us-central1-a}"
INSTANCE_NAME="${GCLOUD_INSTANCE:-chroma-tts-gpu}"
MACHINE_TYPE="n1-standard-8"  # 8 vCPUs, 30GB RAM
GPU_TYPE="nvidia-tesla-a100"  # A100 has 40GB VRAM, sufficient for Chroma-4B
GPU_COUNT=1
IMAGE_NAME="chroma-tts"
IMAGE_TAG="latest"

echo "=== Chroma-4B GPU Deployment ==="
echo "Project: $PROJECT_ID"
echo "Zone: $ZONE"
echo "Instance: $INSTANCE_NAME"
echo "GPU: $GPU_TYPE x $GPU_COUNT"

# Build Docker image
echo "Building Docker image..."
docker build -t gcr.io/$PROJECT_ID/$IMAGE_NAME:$IMAGE_TAG .

# Push to Google Container Registry
echo "Pushing to GCR..."
docker push gcr.io/$PROJECT_ID/$IMAGE_NAME:$IMAGE_TAG

# Create VM with GPU (if not exists)
if ! gcloud compute instances describe $INSTANCE_NAME --zone=$ZONE --project=$PROJECT_ID &>/dev/null; then
    echo "Creating GPU VM instance..."
    gcloud compute instances create $INSTANCE_NAME \
        --project=$PROJECT_ID \
        --zone=$ZONE \
        --machine-type=$MACHINE_TYPE \
        --accelerator=type=$GPU_TYPE,count=$GPU_COUNT \
        --maintenance-policy=TERMINATE \
        --image-family=cos-stable \
        --image-project=cos-cloud \
        --boot-disk-size=100GB \
        --scopes=cloud-platform \
        --metadata=google-logging-enabled=true
    
    echo "Waiting for instance to be ready..."
    sleep 30
fi

# Install NVIDIA drivers and Docker on the VM
echo "Setting up GPU drivers..."
gcloud compute ssh $INSTANCE_NAME --zone=$ZONE --project=$PROJECT_ID --command="
    # Install NVIDIA Container Toolkit
    sudo cos-extensions install gpu
    sudo mount --bind /var/lib/nvidia /var/lib/nvidia
    sudo mount -o remount,exec /var/lib/nvidia
"

# Run the container
echo "Deploying container..."
gcloud compute ssh $INSTANCE_NAME --zone=$ZONE --project=$PROJECT_ID --command="
    # Pull and run the container with GPU
    docker-credential-gcr configure-docker
    docker pull gcr.io/$PROJECT_ID/$IMAGE_NAME:$IMAGE_TAG
    
    # Stop existing container if running
    docker stop chroma-tts 2>/dev/null || true
    docker rm chroma-tts 2>/dev/null || true
    
    # Run with GPU support
    docker run -d \
        --name chroma-tts \
        --gpus all \
        -e HF_TOKEN=\$HF_TOKEN \
        -v /tmp/audio:/app/audio \
        gcr.io/$PROJECT_ID/$IMAGE_NAME:$IMAGE_TAG
"

echo "=== Deployment complete ==="
echo "SSH into VM: gcloud compute ssh $INSTANCE_NAME --zone=$ZONE --project=$PROJECT_ID"
echo "View logs: gcloud compute ssh $INSTANCE_NAME --zone=$ZONE --project=$PROJECT_ID --command='docker logs -f chroma-tts'"
