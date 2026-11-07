# PRAMAAN — Ayurveda Evidence & Safety Workbench

**प्रमाण** (*pramāṇa*, "means of valid knowledge"). A study and clinician-support workbench for the
**AyushTech Innovate: National Open Ayurveda AI Challenge** (Techfest IIT Bombay 2026–27).

PRAMAAN helps an Ayurveda student or Vaidya examine a classical-text question or an educational case
while keeping five things visibly separate:

1. facts the user supplied (tri-state: present / absent / **unknown**),
2. original Sanskrit passages with edition-specific locators (Caraka, Aṣṭāṅgahṛdaya — SARIT TEI),
3. AyurParam's draft explanations, each bound to the one passage it was generated from,
4. evidence that is supporting, context-limiting, missing or insufficient,
5. a separately-sourced safety review and questions needing human judgment.

It is **not** a diagnosis, prescribing, dosing or safety-clearance tool.

## What is real in this repository
- **Live AyurParam** (`bharatgenai/AyurParam` @ `27c69ee`, 2.9B) running on a local GPU through a
  separate model server; used for query/concept expansion and per-passage explanations. Verified by
  `model_server/smoke_test.py` (results in `eval/results/smoke_*.json`).
- **Real classical sources**: 16,980 TEI segments parsed from pinned, checksum-verified SARIT files;
  522 passages indexed for the Agni / Āma / Ajīrṇa module + aśvagandhā mentions.
- **Evidence ledger**: every displayed generated sentence carries server-built citations, citation-integrity
  checks, an automatic (heuristic) support assessment and a pending review status; failing sentences
  are withheld and listed with reasons.
- **Safety policy outside the model**: structured rules (`data/rules/safety_rules.yaml`), escalation
  template, NCCIH-sourced aśvagandhā cautions, "not assessed" for unsupported interactions.
- **Evidence Integrity Lab**: fault injection (retraction, text tampering, irrelevant swap, forged
  citations, prompt injection) on disposable snapshots using the production validator.
- **Evaluation**: 120 synthetic candidate cases (unreviewed), dev/test split, three configurations,
  all numbers from actual runs in `eval/results/`.

## Quick start
See [docs/DEPLOYMENT.md](docs/DEPLOYMENT.md) for full native (Windows-friendly) and Docker instructions.
```
uv venv .venv --python 3.12 && .venv\Scripts\activate
uv pip install torch==2.7.1 --index-url https://download.pytorch.org/whl/cu128
uv pip install -r backend/requirements.lock.txt
cd backend && python -m pramaan.corpus.build && python -m pytest -q && cd ..
cd frontend && npm ci && npm run build && cd ..
python model_server/server.py          # AyurParam on :8601 (needs weights in models/AyurParam)
python -m uvicorn --app-dir backend pramaan.api:app --port 8600   # open http://127.0.0.1:8600
```

## Repository map
| Path | Contents |
|---|---|
| `backend/pramaan/` | corpus ingestion (`corpus/`), retrieval, safety, ledger, LLM adapters, pipeline, API, Integrity Lab, export, evaluation |
| `model_server/` | AyurParam inference service, smoke test, prompt probes |
| `frontend/` | React + TypeScript + Tailwind workbench (Workspace, Source Explorer, Integrity Lab, Evaluation & Review) |
| `data/` | source manifest + pinned raw TEI, curated module selection, draft glosses, terminology, safety rules |
| `eval/` | case generator, 120 cases, frozen test-split hash, results |
| `docs/` | proposal, technical & impact report, clinical review checklist, demo script, deployment, competition checklist |

## Licences
Code: Apache-2.0 (`LICENSE`). Classical text and derived corpus: CC BY-SA 3.0 (`DATA_NOTICE.md`).
Third-party components: `THIRD_PARTY_NOTICES.md`. No institutional affiliation or endorsement is implied.

## Status
Prototype. Clinical/domain review: **0 items reviewed**. Hosting: **not set up**. See
[docs/TECHNICAL_IMPACT_REPORT.md](docs/TECHNICAL_IMPACT_REPORT.md) for measured results and limitations
and [BUILD_STATE.md](BUILD_STATE.md) for the current build state.
