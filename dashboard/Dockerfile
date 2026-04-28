# ──────────────────────────────────────────────
# Stage 1: Build — install Python deps
# ──────────────────────────────────────────────
FROM python:3.12-slim-bookworm AS builder

RUN apt-get update && apt-get install -y --no-install-recommends \
        gcc \
        g++ \
        python3-dev \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Copy everything first so requirements.txt is always available
# regardless of whether Railway uses /dashboard or / as build context.
COPY . .

RUN pip install --no-cache-dir --upgrade pip \
 && pip install --no-cache-dir -r requirements.txt

# ──────────────────────────────────────────────
# Stage 2: Runtime — lean image (no gcc/g++)
# ──────────────────────────────────────────────
FROM python:3.12-slim-bookworm

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

COPY --from=builder /usr/local/lib/python3.12/site-packages \
                    /usr/local/lib/python3.12/site-packages
COPY --from=builder /usr/local/bin /usr/local/bin

# Build context:
#   Railway        → Root Directory = /dashboard → копирует только dashboard/
#   docker-compose → context = ./dashboard       → то же самое
# settings.json НЕ включён в образ намеренно:
#   Railway  → все настройки берутся из env vars
#   локально → settings.json монтируется через volume в docker-compose.yml
COPY . .

RUN mkdir -p logs

CMD ["python", "-u", "main.py"]
