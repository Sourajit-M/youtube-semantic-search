FROM ghcr.io/astral-sh/uv:latest AS uv_bin

# ── Stage 1: Build the React frontend ──
FROM node:20-slim AS frontend-builder
WORKDIR /app/frontend
# Copy package manifests (optional wildcard for package-lock)
COPY frontend/package.json frontend/package-lock.json* ./
RUN npm install
COPY frontend/ ./
RUN npm run build

# ── Stage 2: Build Python dependencies ──
FROM python:3.11-slim AS python-builder
WORKDIR /app
ENV UV_COMPILE_BYTECODE=1
COPY --from=uv_bin /uv /uvx /bin/

RUN apt-get update && apt-get install -y \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-dev

# Pre-download FastEmbed models to bake them into the image, bypassing runtime HF requests
ENV FASTEMBED_CACHE_PATH=/app/fastembed_cache
RUN .venv/bin/python -c "from fastembed import TextEmbedding; from fastembed.rerank.cross_encoder import TextCrossEncoder; TextEmbedding(); TextCrossEncoder(model_name='Xenova/ms-marco-MiniLM-L-6-v2')"

# ── Stage 3: Runtime container ──
FROM python:3.11-slim AS runtime
WORKDIR /app

# Install runtime dependencies (ffmpeg for audio, curl for health checks, nodejs for yt-dlp)
RUN apt-get update && apt-get install -y \
    ffmpeg \
    curl \
    nodejs \
    && rm -rf /var/lib/apt/lists/*

# Copy virtual environment, React static build, and Python modules
COPY --from=python-builder /app/.venv /app/.venv 
COPY --from=python-builder /app/fastembed_cache /app/fastembed_cache
COPY --from=frontend-builder /app/frontend/dist ./frontend/dist
COPY app/ ./app/
COPY eval/ ./eval/
COPY main.py ./
COPY start.sh ./
COPY data.zip ./
RUN chmod +x start.sh

# Make venv active
ENV PATH="/app/.venv/bin:$PATH"
ENV PYTHONPATH="/app"
ENV FASTEMBED_CACHE_PATH=/app/fastembed_cache

# Render standard port exposure
EXPOSE 8000
CMD ["./start.sh"]