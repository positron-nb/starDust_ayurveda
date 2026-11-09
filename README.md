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

## Documentation
| Topic | Document |
|---|---|
| Current architecture and feature status (from code) | [docs/REPOSITORY_AUDIT.md](docs/REPOSITORY_AUDIT.md) |
| Phase 1 proposal | [docs/PHASE1_PROPOSAL.md](docs/PHASE1_PROPOSAL.md) |
| Technical & impact report (architecture, model/data cards, results) | [docs/TECHNICAL_IMPACT_REPORT.md](docs/TECHNICAL_IMPACT_REPORT.md) |
| Latest evaluation & regression | [docs/evaluation_report.md](docs/evaluation_report.md) |
| Retrieval failures / experiments | [docs/RETRIEVAL_FAILURE_ANALYSIS.md](docs/RETRIEVAL_FAILURE_ANALYSIS.md), [docs/RETRIEVAL_EXPERIMENTS.md](docs/RETRIEVAL_EXPERIMENTS.md) |
| Hindi / Hinglish | [docs/INDIC_LANGUAGE_EVALUATION.md](docs/INDIC_LANGUAGE_EVALUATION.md) |
| Clinical safety & human review | [docs/CLINICAL_REVIEW_CHECKLIST.md](docs/CLINICAL_REVIEW_CHECKLIST.md), [docs/CLAIM_AUDIT_REVIEW_GUIDE.md](docs/CLAIM_AUDIT_REVIEW_GUIDE.md), `data/rules/safety_rules.yaml` |
| Dataset lineage & licences | [DATA_NOTICE.md](DATA_NOTICE.md), `data/sources/manifest.json`, [THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md) |
| Deployment / demo hosting / Docker / ZeroGPU | [docs/DEPLOYMENT.md](docs/DEPLOYMENT.md), [docs/DEMO_HOSTING.md](docs/DEMO_HOSTING.md), [docs/DOCKER_VALIDATION.md](docs/DOCKER_VALIDATION.md), [docs/ZEROGPU_COMPATIBILITY_REPORT.md](docs/ZEROGPU_COMPATIBILITY_REPORT.md) |
| Usability pilot | [docs/USABILITY_STUDY_PROTOCOL.md](docs/USABILITY_STUDY_PROTOCOL.md) |
| Finale demo / roadmap / competition | [docs/FINAL_DEMO_SCRIPT.md](docs/FINAL_DEMO_SCRIPT.md), [docs/EXECUTION_ROADMAP.md](docs/EXECUTION_ROADMAP.md), [docs/COMPETITION_CHECKLIST.md](docs/COMPETITION_CHECKLIST.md) |

## Testing
`cd backend && python -m pytest -q` (43 tests; no GPU needed). Live evaluation: `python -m pramaan.eval.run full --split all`
with the model server running. Retrieval experiments: `python -m pramaan.eval.retrieval_lab experiments`.

## Status (9 Nov 2026)
Prototype; not clinically validated; not hallucination-free. Human claim-support review: **0 records labelled**.
Retrieval passage Recall@5 0.24 on inspected cases (target 0.85 not met). Public hosting: **not live**.
Docker: **not validated**. PyTorch 2.8 / ZeroGPU: verified locally on branch `experiment/zerogpu-pt28`, not yet on Hugging Face.
