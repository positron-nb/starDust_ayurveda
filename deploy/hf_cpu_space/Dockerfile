# PRAMAAN on a free Hugging Face CPU Space (Docker SDK).
# Builds the app from the public GitHub repository at a pinned commit; AyurParam weights are
# downloaded at start-up (pinned revision, remote code hash-checked by model_server/server.py).
ARG REPO=https://github.com/positron-nb/starDust_ayurveda.git
ARG REF=pramaan-prototype

FROM node:20.18.1-bookworm-slim AS src
ARG REPO
ARG REF
RUN apt-get update && apt-get install -y --no-install-recommends git ca-certificates && rm -rf /var/lib/apt/lists/*
RUN git clone "$REPO" /src && cd /src && git checkout "$REF" && git rev-parse HEAD > /src/BUILD_COMMIT
WORKDIR /src/frontend
RUN npm ci --no-audit --no-fund && npm run build

FROM python:3.12.8-slim-bookworm
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 PYTHONUTF8=1
RUN useradd -m -u 1000 user
WORKDIR /home/user/app
RUN pip install --no-cache-dir torch==2.7.1 --index-url https://download.pytorch.org/whl/cpu
COPY --from=src /src/backend/requirements.lock.txt backend/requirements.lock.txt
RUN grep -viE '^(torch|nvidia-|triton)' backend/requirements.lock.txt > /tmp/req.txt && pip install --no-cache-dir -r /tmp/req.txt
COPY --from=src /src/backend backend
COPY --from=src /src/model_server model_server
COPY --from=src /src/data data
COPY --from=src /src/eval eval
COPY --from=src /src/BUILD_COMMIT BUILD_COMMIT
COPY --from=src /src/frontend/dist frontend/dist
# Build the corpus at image build time (verifies the pinned sha256 of the SARIT files).
RUN cd backend && python -m pramaan.corpus.build
COPY start.sh start.sh
RUN mkdir -p data/runtime /home/user/models && chown -R user:user /home/user
USER user
ENV HOME=/home/user \
    PRAMAAN_DEPLOY_MODE=public_demo \
    PRAMAAN_LLM_MODE=http \
    PRAMAAN_RATE_LIMIT=20 \
    PRAMAAN_FRAME_ANCESTORS="https://huggingface.co" \
    PRAMAAN_EXPLAIN_PASSAGES=1 \
    PRAMAAN_EXPLAIN_TOKENS=80 \
    PRAMAAN_AYURPARAM_EXPAND=0 \
    AYURPARAM_TIMEOUT_S=900 \
    AYURPARAM_DEVICE=cpu \
    AYURPARAM_CPU_BF16=1 \
    AYURPARAM_CPU_THREADS=2 \
    AYURPARAM_LOCAL_DIR=/home/user/models/AyurParam
EXPOSE 7860
CMD ["bash", "start.sh"]
