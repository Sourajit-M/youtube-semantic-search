FROM ghcr.io/astral-sh/uv:latest AS uv_bin
FROM python:3.11-slim AS builder

WORKDIR /app

# Enable bytecode compilation
ENV UV_COMPILE_BYTECODE=1
# Copy uv from official image
COPY --from=uv_bin /uv /uvx /bin/

# Install build dependencies
RUN apt-get update && apt-get install -y \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Install dependencies
COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-dev

FROM python:3.11-slim AS runtime

WORKDIR /app

# Install runtime dependencies (ffmpeg for audio processing, curl for health checks, nodejs for yt-dlp)
RUN apt-get update && apt-get install -y \
    ffmpeg \
    curl \
    nodejs \
    && rm -rf /var/lib/apt/lists/*

COPY --from=builder /app/.venv /app/.venv 
COPY app/ ./app/
COPY eval/ ./eval/
COPY main.py ./
COPY start.sh ./
COPY data.zip ./
RUN chmod +x start.sh

# Make venv the active Python
ENV PATH="/app/.venv/bin:$PATH"
ENV PYTHONPATH="/app"

# Render uses dynamic PORT, falling back to 7860
EXPOSE 7860
CMD ["./start.sh"]