# Dockerfile for 123Bot
# 
# Build: docker build -t 123bot:latest .
# Run: docker run -d --name 123bot \
#        -e P123_ACCOUNT_ID="your_id" \
#        -e P123_PASSWORD="your_password" \
#        -e P123_PARENT_ID="0" \
#        -v /path/to/config:/app/config \
#        -v /path/to/tmp:/app/tmp \
#        123bot:latest

FROM python:3.12-slim

# Set maintainer
LABEL maintainer="Bitliker" version="1.0.0"

# Set working directory
WORKDIR /app

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
COPY config ./config

# Set Python environment variables
ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD python -c "import sys; sys.exit(0)" || exit 1

# Entry point
ENTRYPOINT ["python", "-m", "src"]
