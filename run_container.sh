#!/bin/bash

REGISTRY_HOST=harbor.golebiowski.dev
IMAGE_NAME=$REGISTRY_HOST/services/martialmatch-scraper

log() {
  echo "$(date +"%Y-%m-%d %H:%M:%S") - $1"
}

log_error() {
  echo -e "\033[31m$(date +"%Y-%m-%d %H:%M:%S") - Error: $1\033[0m" >&2
}

# Detect OS and set appropriate platforms
if [[ "$OSTYPE" == "darwin"* ]]; then
    PLATFORMS="linux/amd64,linux/arm64"
    log "Detected macOS - building for multiple platforms: $PLATFORMS"
else
    PLATFORMS="linux/amd64"
    log "Detected Linux - building for single platform: $PLATFORMS"
fi

log "Building Docker image with version $VERSION..."

if ! docker build --platform "$PLATFORMS" -t "$IMAGE_NAME:latest" -f Dockerfile .; then
    log_error "Docker build failed"
    exit 1
fi

log "Checking if container is already running..."
if docker ps -q -f name=martialmatch-scraper | grep -q .; then
    log "Container is running, stopping it..."
    docker stop martialmatch-scraper
fi

if docker ps -a -q -f name=martialmatch-scraper | grep -q .; then
    log "Removing existing container..."
    docker rm martialmatch-scraper
fi

log "Running container..."
docker run -p 80:80 -d --name martialmatch-scraper "$IMAGE_NAME:latest"