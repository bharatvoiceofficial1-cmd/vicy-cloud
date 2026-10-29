FROM python:3.11-slim-bookworm

# Install Linux system packages (bash, git, curl, build tools, procps)
RUN apt-get update && apt-get install -y --no-install-recommends \
    bash \
    curl \
    git \
    procps \
    build-essential \
    ca-certificates \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Copy requirements and install
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Create workspace directory
RUN mkdir -p /workspace /app/data

# Copy application files
COPY . /app/

ENV WORKSPACE_DIR=/workspace
ENV TASKS_DB_PATH=/app/data/tasks.json
ENV PORT=10000
ENV PYTHONUNBUFFERED=1

EXPOSE 10000

CMD ["python", "container_server.py"]
