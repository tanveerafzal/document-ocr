#!/bin/bash
# Build and push the base image to Artifact Registry
# Run this once, or when dependencies change

set -e

# Configuration
PROJECT_ID="id-verification-481302"
REGION="northamerica-northeast2"
REPO="ocr-base"
IMAGE="ocr-base"

# Full image path
IMAGE_PATH="${REGION}-docker.pkg.dev/${PROJECT_ID}/${REPO}/${IMAGE}"

echo "=== Building OCR Base Image ==="
echo "Image: ${IMAGE_PATH}"

# Create Artifact Registry repository if it doesn't exist
echo "Creating Artifact Registry repository (if not exists)..."
gcloud artifacts repositories create ${REPO} \
    --repository-format=docker \
    --location=${REGION} \
    --description="OCR API base images" \
    2>/dev/null || echo "Repository already exists"

# Configure Docker to use gcloud credentials
echo "Configuring Docker authentication..."
gcloud auth configure-docker ${REGION}-docker.pkg.dev --quiet

# Build the base image
echo "Building base image (this will take 10-15 minutes)..."
docker build -f Dockerfile.base -t ${IMAGE_PATH}:latest .

# Push to Artifact Registry
echo "Pushing to Artifact Registry..."
docker push ${IMAGE_PATH}:latest

# Tag with date for versioning
DATE_TAG=$(date +%Y%m%d)
docker tag ${IMAGE_PATH}:latest ${IMAGE_PATH}:${DATE_TAG}
docker push ${IMAGE_PATH}:${DATE_TAG}

echo ""
echo "=== Base image built and pushed successfully ==="
echo "Image: ${IMAGE_PATH}:latest"
echo ""
echo "Now update your Dockerfile to use this base image:"
echo "  ARG BASE_IMAGE=${IMAGE_PATH}:latest"
echo ""
echo "Future deploys will be ~30 seconds!"
