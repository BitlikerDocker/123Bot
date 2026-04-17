# Dockerfile for 123Bot
# 
# Build with default paths:
#   docker build -t 123bot:latest .
#
# Build with custom paths:
#   docker build -t 123bot:latest \
#     --build-arg MEDIA_PATH=/custom/media \
#     --build-arg CONFIG_PATH=/custom/config .
#
# Run:
#   docker run -d --name 123bot \
#     -e P123_ACCOUNT_ID="your_id" \
#     -e P123_PASSWORD="your_password" \
#     -e P123_PARENT_ID="0" \
#     -v /path/to/config:/app/config \
#     -v /path/to/media:/app/media \
#     123bot:latest

FROM python:3.12-slim


# Set maintainer
LABEL maintainer="Bitliker" version="1.0.0"

# Set working directory
WORKDIR /app

# Set environment variables from build arguments
ENV MEDIA_PATH=/app/media
ENV CONFIG_PATH=/app/config
ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    make \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements file
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY src ./src

# Create required directories
RUN mkdir -p ${MEDIA_PATH} ${CONFIG_PATH}

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD ["python", "-c", "import sys; sys.exit(0)"]

# Entry point
ENTRYPOINT ["python", "src/__main__.py"]