# BUILD_STATE — PRAMAAN (living file; update after each milestone)

Last update: 2026-11-09 ~16:30 local (round 2: audit, retrieval study, auth, ZeroGPU experiment).

## Environment (build machine)
- Windows 11, Ryzen 9 270, 15.3 GB RAM, RTX 5060 Laptop 8 GB (sm_120).
- `.venv` (uv, Python 3.12): torch 2.7.1+cu128 (installed from a resumable-downloaded wheel), transformers 4.53.1,
  sentence-transformers 4.1.0. Lockfile: `backend/requirements.lock.txt`. Node 24; `frontend/package-lock.json`.
- AyurParam weights at `models/AyurParam` (pinned 27c69ee, 11.4 GB, git-ignored). Docker not installed.

## Working commands (all verified on this machine)
```
cd backend && ../.venv/Scripts/python -X utf8 -m pramaan.corpus.build        # stop the API first (Windows file lock)
cd backend && ../.venv/Scripts/python -X utf8 -m pytest -q                   # 27 passed
.venv/Scripts/python -X utf8 model_server/smoke_test.py                      # PASS (eval/results/smoke_*.json)
.venv/Scripts/python -X utf8 model_server/server.py                          # :8601
.venv/Scripts/python -X utf8 -m uvicorn --app-dir backend pramaan.api:app --port 8600
cd frontend && npm run build
cd backend && ../.venv/Scripts/python -X utf8 -m pramaan.eval.run {retrieval|full|dense_rag|raw} --split test
.venv/Scripts/python -X utf8 scripts/record_demo_fixtures.py                 # 16 records written
```

## Milestones
1. DONE model smoke test + TEI ingestion (16,980 segments; 522 indexed; corpus-226ed5c80f0a0612).
2. DONE query → retrieval → AyurParam (per-passage) → validated ledger response (live).
3. DONE safety rules, tri-state facts, abstention, escalation, fabricated-locator refusal.
4. DONE workbench UI (4 views), source reader, review workflow; browser-checked demos A, B (counterfactual), D, E,
   Lab retraction/forge/swap/inject; no overflow at 768 px and 1440 px. Visual screenshots NOT taken (pane hidden).
5. DONE evaluation (120 cases; test split frozen; 3 configs + retrieval ablation), docs, Docker/CI files.

## Key measured results (test split, 77 cases, unreviewed candidate labels)
Hybrid Hit@5 0.605 (no expansion) / 0.579 (with AyurParam expansion); 57/57 displayed claims pass integrity;
316/373 generated sentences withheld; 0/2 fabricated citations accepted; escalation 4/4, false 0/73;
abstention 10/13; latency p50 8.2 s. Baselines in docs/TECHNICAL_IMPACT_REPORT.md §6.3.

## Known issues / blockers
- Hosting not set up (no authorised target). Repo not pushed; nothing committed yet (git initialised).
- Docker Compose untested; CPU-only inference unmeasured.
- 0 clinical/domain reviews. All eval labels are candidates.
- Retrieval below 0.85 target; fact extractor treats "safe in pregnancy?" as pregnancy=present (S17).
- 82 sentences withheld because of the 90-token output cap — try 120.
- Fixture replay must be re-recorded after any corpus/terms/prompt change.
- Model server serialises requests; an OOM incident (fixed) is documented in the report §8.

## Next human actions
1. Ayurveda teammate: review glosses, labelled passages, safety cases (Evaluation & Review screen).
2. Practitioner: review safety_rules.yaml + urgent template.
3. Team Leader: register (by 15 Nov), push repo, choose hosting option (DEPLOYMENT.md §4), submit Phase 1 by 22 Nov.

## Round 2 (2026-11-09)
- Stable branch `pramaan-prototype`; experiment branch `experiment/zerogpu-pt28` (Gradio Space + ZeroGPUAdapter).
- `.venv-pt28` (torch 2.8.0+cu128, gradio 5.50.0, spaces 0.51.3) is separate; production `.venv` unchanged.
- Tests: 43 passed. Live regression: eval/results/eval_full_pramaan_all_20261109_160413.json.
- New commands: `python scripts/export_claim_audit.py`, `import_claim_audit.py`, `claim_audit_summary.py`,
  `scripts/benchmark_lock.py`, `python -m pramaan.eval.retrieval_lab {experiments|failures|indic [--model]|fresh}`.
- Known: embedded Qdrant allows one client per folder per process (now shared); a second PROCESS opening it
  fails — stop the API before running retrieval_lab, or use Qdrant server.
- Blocked on people: claim audit labels, fresh benchmark, practitioner rule review, HF account, cloudflared install, Docker host.
