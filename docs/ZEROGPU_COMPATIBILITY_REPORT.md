# PyTorch 2.8 / Hugging Face ZeroGPU compatibility report

Date 2026-11-09. Branch `experiment/zerogpu-pt28` (inference-only Space + `ZeroGPUAdapter`).
`pramaan-prototype` and its `.venv` (torch 2.7.1) were not changed; the experiment used a separate
`.venv-pt28`.

## Decision
| Question | Answer |
|---|---|
| Does AyurParam (custom `parambharatgen`, pinned 27c69ee, reviewed remote code) run on PyTorch 2.8? | **YES — locally verified** |
| Does the Space code run and serve the PRAMAAN backend? | **YES — locally**, via `gradio_client`, full pipeline answered |
| Does it run on actual Hugging Face ZeroGPU hardware? | **NOT TESTED** — needs the team's HF account (eligibility below) |
| Recommendation | **GO for a deployment attempt**, with the laptop + tunnel path (DEMO_HOSTING.md) kept as the demo fallback. Do not migrate anything else until a real ZeroGPU run passes. |

## Official requirements (read 2026-11-09 from huggingface.co/docs/hub/spaces-zerogpu, spaces-overview, spaces-gpus; the URL /docs/zero-gpu/index returned 404)
- Hosting: free personal accounts in good standing (verified email, account older than 30 days) can host
  up to 2 ZeroGPU Spaces; PRO up to 10. Creating Gradio/Docker Spaces on other compute needs a paid plan.
- SDK: Gradio only (4+). Python 3.12.12 or 3.10.13 listed. PyTorch "almost all versions from 2.8.0"
  (2.8.0 … 2.13.0 listed). 2.7.1 is **not** listed — hence this experiment.
- Hardware: half NVIDIA RTX Pro 6000 Blackwell, 48 GB (`large`, default) or full 96 GB (`xlarge`).
- Pattern: `import spaces`; model placed on `cuda` **at module level**; GPU work inside
  `@spaces.GPU(duration=…)` (default 60 s); decorator is a no-op outside ZeroGPU. `torch.compile`
  unsupported (AoT on 2.8+ is).
- Daily visitor quota: unauthenticated 2 min, free account 5 min, PRO 40 min. Remaining quota affects
  queue priority. Not documented: bf16, `trust_remote_code`, cold starts, gradio_client access.

## Local compatibility test (RTX 5060 Laptop 8 GB, Windows 11)
| Item | torch 2.7.1 (production) | torch 2.8.0 (experiment) |
|---|---|---|
| Python | 3.12.10 | 3.12.10 |
| torch / CUDA | 2.7.1+cu128 / 12.8 | 2.8.0+cu128 / 12.8 |
| transformers | 4.53.1 | 4.53.1 |
| Remote-code sha256 | 4745b5bc… / 9d89451d… (checked) | same (checked before load) |
| Load (bf16, local SSD) | 27.8 s | 23.3 s (smoke) / 22.0 s (Space) |
| VRAM after load | 5,488 MB | 5,488 MB |
| Greedy outputs, 4 prompts × cache on/off | — | **8/8 byte-identical to 2.7.1** (`smoke_20261107_231253` vs `smoke_20261109_161130`) |
| Chat template drops system message | yes | yes |

## Space test (local, `deploy/zerogpu_space/app.py`, gradio 5.50.0, spaces 0.51.3, gradio_client 1.14.0)
| Test | Result |
|---|---|
| Process start → port open (incl. weight load) | ~4 min on this laptop (first import of gradio + load) |
| First call, 123-token prompt, 90 new tokens | 5.6 s wall (5.1 s generation) |
| Warm calls | 6.5 s, 3.9 s, 3.9 s |
| Prompt + max_new_tokens > 2048 | rejected: "prompt 4201 + max_new_tokens 90 exceeds 2048" |
| Invalid parameters | rejected |
| Full PRAMAAN pipeline via `ZeroGPUAdapter` (demo A) | `answered`, `inference_ran=true`, hardware tagged `zerogpu:…`, same shown claim as the local server |
| Space unreachable and local server down | `retrieval_only` (visible degradation, no silent substitution) |

These are local numbers; ZeroGPU cold starts, queueing and Blackwell-48 GB latency are unknown.

## Risks
1. Quota: an answered query needs 1 expansion + up to 3 explanation calls (~15–25 s of GPU). A free
   visitor's 5 min/day ≈ 12–20 answered queries; anonymous visitors (2 min) far fewer. Judges should
   log in or the team should consider PRO for the finale window.
2. Each `@spaces.GPU` call may queue; latency can exceed the local 8 s p50 substantially.
3. `trust_remote_code` behaviour on ZeroGPU is undocumented; the Space refuses to load if the
   downloaded code hash differs from the reviewed one.
4. The Space is a raw inference endpoint with no safety layer; it must stay private or be called only
   by the PRAMAAN backend (HF token server-side in `HF_TOKEN`; never in the frontend).
5. CUDA emulation outside `@spaces.GPU` might affect tokenizer-only code paths — untested.

## Steps for the team (needs your HF account)
1. Confirm account eligibility (verified email, >30 days old).
2. Create a **private** Gradio Space; push `deploy/zerogpu_space/` from `experiment/zerogpu-pt28`; select ZeroGPU hardware.
3. First build downloads 11.4 GB of weights; watch logs for the hash check and "Loading checkpoint shards".
4. From the laptop: `PRAMAAN_LLM_MODE=zerogpu AYURPARAM_SPACE=<user>/<space> HF_TOKEN=<read token>` and run demo A.
5. Record cold start, warm latency, queue time and quota use here; only then decide whether to merge the adapter.
