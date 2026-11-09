# Docker validation

**Status: NOT VALIDATED.** Docker is not installed on the build machine (`which docker` → not found,
2026-11-09), so no image was built and no container was started. Nothing below is a measured result.

## What exists (inspected)
| File | Content |
|---|---|
| `deploy/Dockerfile.api` | Node 20 stage builds the UI; Python 3.12 slim stage installs CPU torch 2.7.1 + lockfile (torch/nvidia/triton lines filtered), builds the corpus (verifies SARIT sha256), runs as non-root, exposes 8600 |
| `deploy/Dockerfile.model` | CUDA 12.8 runtime, torch 2.7.1+cu128, transformers 4.53.1; weights **mounted** from `./models/AyurParam` (never baked in) |
| `docker-compose.yml` | `qdrant` (v1.14.1), `api` (→ `QDRANT_URL=http://qdrant:6333`, bound to 127.0.0.1:8600), optional `model` service behind the `gpu` profile |
| `.env.example` | all variables; no secrets |

## Known gaps to fix during validation
- Healthchecks added for `api` (`/api/auth/status`) and `model` (`/health` loaded); Qdrant has none (image tooling not verified).
- With `PRAMAAN_ACCESS_PASSCODE` set, `/api/health` requires auth — use `/api/auth/status` for container health.
- Qdrant server mode path (`QDRANT_URL`) has not been exercised; only embedded mode was used.
- GPU passthrough on Windows requires Docker Desktop + WSL2 + NVIDIA Container Toolkit; untested.

## Validation procedure (to run on a machine with Docker)
| # | Command / check | Expected |
|---|---|---|
| 1 | `docker compose build` | both images build; corpus build prints `corpus-226ed5c8…` |
| 2 | `PRAMAAN_LLM_MODE=off docker compose up -d` | qdrant + api running |
| 3 | `curl 127.0.0.1:8600/api/health` | `api: ok`, `dense.enabled: true` (Qdrant server) |
| 4 | open `http://127.0.0.1:8600` | UI loads |
| 5 | query "What is ama?" | `retrieval_only`, passages with locators |
| 6 | safety: urgent example | `escalated` |
| 7 | `docker compose --profile gpu up -d` (GPU host) | model `/health` loaded; banner LIVE |
| 8 | `docker compose restart api` | recovers; cached runs revalidated |
Record results here with date, Docker version and host.
