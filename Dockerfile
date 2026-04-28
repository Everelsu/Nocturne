# ──────────────────────────────────────────────
# Stage 1: Build — install Python deps
# ──────────────────────────────────────────────
FROM python:3.12-slim-bookworm AS builder

RUN apt-get update && apt-get install -y --no-install-recommends \
        gcc \
        python3-dev \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip \
 && pip install --no-cache-dir -r requirements.txt

# ──────────────────────────────────────────────
# Stage 2: Runtime — lean image
# ──────────────────────────────────────────────
FROM python:3.12-slim-bookworm

# Keeps Python from writing .pyc files and enables stdout/stderr unbuffered
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

# Copy installed packages from builder
COPY --from=builder /usr/local/lib/python3.12/site-packages \
                    /usr/local/lib/python3.12/site-packages
COPY --from=builder /usr/local/bin /usr/local/bin

# Copy application source (secrets come via Railway env vars, not baked in)
COPY . .

# Create logs directory so the bot doesn't crash on first start
RUN mkdir -p logs

CMD ["python", "-u", "main.py"]
