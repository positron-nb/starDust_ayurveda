# Deployment

**Status: hosting is NOT done.** No authorised hosting target was configured for this build, so no
public URL exists. A local app does not satisfy the competition's "live hosted app link" deliverable.

## 1. What was actually tested (build machine, 2026-11-07)
| Item | Result |
|---|---|
| OS / hardware | Windows 11, AMD Ryzen 9 270 (8C/16T), 15.3 GB RAM, NVIDIA RTX 5060 Laptop 8 GB (sm_120) |
| AyurParam load | bf16 on CUDA, 27–28 s from local SSD, **5.49 GB** VRAM after load, ~5.5–5.8 GB peak during generation (`eval/results/smoke_*.json`) |
| Generation speed | ~13–14 tokens/s with KV cache (greedy). Per-passage explanation ≈ 6–9 s each; full answered query ≈ 25–45 s end-to-end |
| PyTorch | 2.7.1+cu128 (Blackwell sm_120 requires CUDA 12.8 wheels) |
| Native run | Yes (commands below) |
| Docker / Compose | **Not tested** — Docker is not installed on the build machine |
| CPU-only inference | **Not tested.** FP32 weights alone are 11.4 GB; with 15 GB system RAM this is unlikely to fit alongside the OS. `AYURPARAM_CPU_BF16=1` (≈5.7 GB) is supported by the server but unmeasured |

## 2. Native setup (Windows-friendly; Linux/macOS equivalent)
```powershell
# Python 3.12 + uv (https://docs.astral.sh/uv/) ; Node 20+
uv venv .venv --python 3.12
.venv\Scripts\activate
uv pip install torch==2.7.1 --index-url https://download.pytorch.org/whl/cu128   # or /whl/cpu
uv pip install -r backend\requirements.lock.txt
# AyurParam weights (11.4 GB) at the pinned revision
python -c "from huggingface_hub import snapshot_download as s; s('bharatgenai/AyurParam', revision='27c69eeef492bbc9e2c0048fc1e95959ffc0820e', local_dir='models/AyurParam')"
cd backend; python -m pramaan.corpus.build; python -m pytest -q; cd ..
cd frontend; npm ci; npm run build; cd ..
# two processes
python model_server\server.py                                                       # :8601
python -m uvicorn --app-dir backend pramaan.api:app --host 127.0.0.1 --port 8600   # :8600 → open http://127.0.0.1:8600
```
If uv's torch download stalls (it did on the build machine), download the wheel with a resumable
`curl -C -` from `https://download-r2.pytorch.org/whl/cu128/` and `uv pip install <file>.whl`.

Modes (`PRAMAAN_LLM_MODE`): `http` (live AyurParam), `fixture` (replay of outputs recorded from
live runs — banner says FIXTURE REPLAY, never "live"), `off` (retrieval-only, visibly degraded).

## 3. Docker Compose (untested here)
```
docker compose --profile gpu up --build     # needs NVIDIA Container Toolkit; weights mounted from ./models/AyurParam
PRAMAAN_LLM_MODE=off docker compose up --build   # retrieval-only, no GPU
```
The API image builds the corpus at build time and verifies the pinned SARIT checksums.

## 4. Hosting options for the competition link (choose one; none set up)
| Option | AyurParam live? | Cost | Notes |
|---|---|---|---|
| A. Team GPU machine + tunnel (e.g. Cloudflare Tunnel) exposing **only** :8600 | Yes | Free | Machine must stay on; set `PRAMAAN_DEPLOY_MODE=public_demo`; keep :8601 bound to localhost. |
| B. Hugging Face Space (Docker), CPU basic | Only fixture/retrieval-only realistically | Free tier | Label as FIXTURE REPLAY. Check Space hardware limits before relying on it. |
| C. Cloud GPU VM (≥8 GB VRAM) | Yes | Paid | Not created (no paid resources without explicit approval). |

Public-demo hardening already implemented: read-only mode (`PRAMAAN_DEPLOY_MODE=public_demo`) disables
review/admin routes, lists runs only per browser session, per-IP POST rate limit (30/min default),
64 KB body cap, query/case length caps, CSP / nosniff / no-referrer headers, model server bound to
127.0.0.1 with no auth (never expose it), disposable Integrity-Lab snapshots deleted after each run.

## 5. Offline / venue fallback
1. Run everything locally on the GPU laptop (no internet needed after setup; Google Fonts fall back to
   system fonts such as Nirmala UI for Devanagari).
2. If the GPU fails: `PRAMAAN_LLM_MODE=fixture` replays outputs recorded from live runs for the demo
   prompts (record with `python scripts/record_demo_fixtures.py` while the model server is up). The
   banner shows **FIXTURE REPLAY — NOT live inference**.
3. Last resort: `PRAMAAN_LLM_MODE=off` — retrieval, safety rules, ledger and Integrity Lab still work.

## 6. Resource notes
- Disk: weights 11.4 GB + torch ≈ 5 GB + corpus/index < 100 MB.
- The API process loads multilingual-e5-small on CPU (~0.5 GB RAM) and builds the Qdrant index on first start (~30 s).
- Concurrency: the model server serialises generation (one request at a time). Expect queueing with multiple users.
