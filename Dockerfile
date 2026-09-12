FROM python:3.12-slim

# Set environment
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PORT=8000 \
    HOST=0.0.0.0

WORKDIR /app

# Install system dependencies (including build tools for raw socket and net tools)
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    curl \
    iputils-ping \
    net-tools \
    && rm -rf /var/lib/apt/lists/*

# Install Python requirements
COPY requirements.txt ./
COPY backend/requirements.txt ./backend/
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Copy source code and assets
COPY . .

# Ensure storage directories exist
RUN mkdir -p uploads/avatars static

EXPOSE 8000

CMD ["uvicorn", "backend.main:app", "--host", "0.0.0.0", "--port", "8000"]
