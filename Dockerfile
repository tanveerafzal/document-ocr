# Use pre-built base image with all dependencies
ARG BASE_IMAGE=northamerica-northeast2-docker.pkg.dev/id-verification-481302/ocr-base/ocr-base:latest
FROM ${BASE_IMAGE}

# Copy only application code (dependencies already in base image)
COPY app/ ./app/
COPY scripts/ ./scripts/

# Set environment variables
ENV PORT=8080

# Expose port
EXPOSE 8080

# Run the application
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8080"]
