#!/bin/bash

# Get the latest version from git tags and increment minor version
CURRENT_VERSION=$(git describe --tags --abbrev=0 2>/dev/null | sed 's/v//' || echo "1.0")
MAJOR=$(echo $CURRENT_VERSION | cut -d. -f1)
MINOR=$(echo $CURRENT_VERSION | cut -d. -f2)
NEW_MINOR=$((MINOR + 1))
VERSION="$MAJOR.$NEW_MINOR"

REGISTRY_HOST=harbor.golebiowski.dev
IMAGE_NAME=$REGISTRY_HOST/services/martialmatch-scraper

# Detect OS and set appropriate platforms
if [[ "$OSTYPE" == "darwin"* ]]; then
    PLATFORMS="linux/amd64,linux/arm64"
    log "Detected macOS - building for multiple platforms: $PLATFORMS"
else
    PLATFORMS="linux/amd64"
    log "Detected Linux - building for single platform: $PLATFORMS"
fi

_log() {
  local output_stream=${2:-1}
  echo "$(date +"%Y-%m-%d %H:%M:%S") - $1" >&$output_stream
}

log() {
  _log "$1" 1
}

log_error() {
  _log "Error: $1" 2
}

if ! docker info > /dev/null 2>&1; then
    log_error "Docker daemon is not running"d
    exit 1
fi

log "Building Docker image with version $VERSION..."
if ! docker build --platform "$PLATFORMS" --build-arg VERSION="$VERSION" -t "$IMAGE_NAME:$VERSION" -f Dockerfile .; then
    log_error "Docker build failed"
    exit 1
fi

log "Pushing Docker image to registry..."

log "Checking connectivity to registry host: $REGISTRY_HOST"
if ping -c 1 -W 5 "$REGISTRY_HOST" > /dev/null 2>&1; then
    if docker push "$IMAGE_NAME:$VERSION"; then
        log "Docker image pushed successfully"
    else
        log_error "Failed to push Docker image to registry"
    fi
else
    log_error "Cannot reach registry host $REGISTRY_HOST."
fi

log "Updating version in kustomization..."
if [[ "$OSTYPE" == "darwin"* ]]; then
    sed -i '' "s|$IMAGE_NAME:.*|$IMAGE_NAME:$VERSION|" kustomization/deployment.yaml
else
    sed -i "s|$IMAGE_NAME:.*|$IMAGE_NAME:$VERSION|" kustomization/deployment.yaml
fi

log "Committing version to the repository..."
git add kustomization/deployment.yaml
git commit -m "Release version $VERSION"
git tag v$VERSION

log "Deployment completed successfully. Now push commit and tag to the repository."
