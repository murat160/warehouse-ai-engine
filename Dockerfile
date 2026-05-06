# Production image for Murat AI (source repo: warehouse-ai-engine).
# Build:  docker build -t murat-ai .
# Run:    handled by docker-compose.yml (see docs/self-hosted-deploy.md).

FROM python:3.11-slim AS base

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    HF_HOME=/app/hf_cache \
    STREAMLIT_HOME=/app/.streamlit \
    STREAMLIT_SERVER_HEADLESS=true \
    STREAMLIT_BROWSER_GATHER_USAGE_STATS=false

# System dependencies: ffmpeg (audio/video pipeline), git (yt-dlp, model downloads),
# build-essential (some wheels build from source), libsndfile1 (soundfile).
RUN apt-get update \
 && apt-get install -y --no-install-recommends \
        ffmpeg \
        git \
        curl \
        ca-certificates \
        build-essential \
        libsndfile1 \
        libpq-dev \
 && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# 1) Install CPU-only torch first (huge wheel — keep it isolated for Docker layer cache).
RUN pip install --no-cache-dir \
        --index-url https://download.pytorch.org/whl/cpu \
        "torch>=2.2,<3.0"

# 2) Install the rest of the requirements (torch is already satisfied).
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt psycopg[binary]

# 3) Copy application source last so code edits do NOT bust the heavy layers.
COPY . ./

# Persistent runtime data (mounted as a volume in production):
#   /app/data           → SQLite DB (when DATABASE_URL is unset), custom voices,
#                         publishing inbox, ffmpeg artefacts.
#   /app/hf_cache       → Hugging Face / NLLB / MMS-TTS / Whisper model cache.
RUN mkdir -p /app/data /app/hf_cache

EXPOSE 8501

# Streamlit-only entry point. The FastAPI service in src/api is intentionally
# NOT exposed on this image; spin it up with a dedicated container if needed.
CMD ["streamlit", "run", "app.py", \
     "--server.address=0.0.0.0", \
     "--server.port=8501", \
     "--server.headless=true", \
     "--server.fileWatcherType=none", \
     "--browser.gatherUsageStats=false"]
