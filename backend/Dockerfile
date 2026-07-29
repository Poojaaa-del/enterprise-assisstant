# # backend/Dockerfile
# # ── Stage 1: Build & install dependencies ──
# FROM python:3.11-slim AS builder

# ENV PYTHONDONTWRITEBYTECODE=1
# ENV PYTHONUNBUFFERED=1

# WORKDIR /app

# RUN apt-get update && apt-get install -y --no-install-recommends \
#     build-essential \
#     curl \
#     && rm -rf /var/lib/apt/lists/*

# # 1. Upgrade pip and force lightweight CPU-only PyTorch first (Prevents OOM / Status 137)
# RUN pip install --no-cache-dir --upgrade pip && \
#     pip install --no-cache-dir torch --index-url https://download.pytorch.org/whl/cpu

# # 2. Install remaining requirements
# COPY requirements.txt .
# RUN pip install --no-cache-dir --default-timeout=1000 --retries 10 --user -r requirements.txt

# # ── Stage 2: Production Runtime ──
# FROM python:3.11-slim AS runner

# ENV PYTHONDONTWRITEBYTECODE=1
# ENV PYTHONUNBUFFERED=1
# ENV PATH=/root/.local/bin:$PATH
# ENV PYTHONPATH=/root/.local/lib/python3.11/site-packages:$PYTHONPATH

# WORKDIR /app

# RUN apt-get update && apt-get install -y --no-install-recommends \
#     curl \
#     && rm -rf /var/lib/apt/lists/*

# COPY --from=builder /root/.local /root/.local
# COPY . /app

# # Run Uvicorn listening dynamically on Render's $PORT
# CMD ["sh", "-c", "uvicorn main:app --host 0.0.0.0 --port ${PORT:-8000}"]
# backend/Dockerfile
FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
# ⚡ Memory optimization for Linux/Docker containers on Render
ENV MALLOC_ARENA_MAX=2
ENV PYTHONUNBUFFERED=1

WORKDIR /app

# Install system build dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    curl \
    && rm -rf /var/lib/apt/lists/*

# 1. Upgrade pip and force CPU-only PyTorch
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir torch --index-url https://download.pytorch.org/whl/cpu

# 2. Install requirements
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 3. Copy application code
COPY . /app

# Expose Hugging Face default port
EXPOSE 8080

CMD ["sh", "-c", "uvicorn main:app --host 0.0.0.0 --port ${PORT:-8080}"]