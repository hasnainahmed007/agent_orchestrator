FROM python:3.12-slim

WORKDIR /app

# Install system dependencies for git
RUN apt-get update && apt-get install -y --no-install-recommends \
    git \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy source code
COPY . .

# Create default project directory
RUN mkdir -p /app/projects/default

# Expose API port
EXPOSE 8000

# Default command: CLI mode
CMD ["python", "main.py", "--mode", "cli"]
