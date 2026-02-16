# Dockerfile for LiveKit Voice Agent
# Optimized for LiveKit Cloud Agents deployment

FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Set environment variables
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

# Install system dependencies
# - gcc: Required for compiling Python packages
# - postgresql-client: For database operations and debugging
# - curl: For health checks and debugging
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    g++ \
    postgresql-client \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first for better layer caching
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Create logs directory
RUN mkdir -p logs

# Expose port for health checks (if needed)
# EXPOSE 8080

# Health check (optional - can be implemented as HTTP endpoint)
# HEALTHCHECK --interval=30s --timeout=5s --start-period=30s --retries=3 \
#   CMD curl -f http://localhost:8080/health || exit 1

# Run the agent
# The 'start' command runs the agent in production mode
CMD ["python", "main.py", "start"]
