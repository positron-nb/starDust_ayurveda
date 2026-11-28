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

## Phase 2 submission (team StarDust, TM-FAD5308E454)
| Deliverable | Link |
|---|---|
| Live hosted app (always on) | https://stardustayurveda-kappa.vercel.app/ — verses, citations, safety layer, Integrity Lab; shows a **"Live AyurParam demo"** button whenever the team GPU demo is running |
| Technical-clinical report | [docs/submission/TECHNICAL_CLINICAL_REPORT.pdf](docs/submission/TECHNICAL_CLINICAL_REPORT.pdf) (source: [docs/TECHNICAL_CLINICAL_REPORT.md](docs/TECHNICAL_CLINICAL_REPORT.md)) |
| Open-source repository | this repository, Apache-2.0 |

Start the full live AyurParam demo on the team machine with one command (`-Stop` to stop):
```
powershell -ExecutionPolicy Bypass -File scripts\start_live_demo.ps1
```

## What is real in this repository
- **Live AyurParam** (`bharatgenai/AyurParam` @ `27c69ee`, 2.9B) running on a local GPU through a
  separate model server; used for query/concept expansion and per-passage explanations. Verified by
  `model_server/smoke_test.py` (results in `eval/results/smoke_*.json`).
- **Real classical sources**: 16,980 TEI segments parsed from pinned, checksum-verified SARIT files;
  882 verse-level passages indexed in five curated modules (Agni–Āma–Ajīrṇa, Prakṛti, Svasthavṛtta,
  foundational concepts, aśvagandhā mentions): 20 core topics, with a curated definition verse shown
  first for "what is X" questions.
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
| Phase 1 proposal | [docs/PHASE1_PROPOSAL.md](docs/PHASE1_PROPOSAL.md) · PDF: [docs/submission/PHASE1_PROPOSAL.pdf](docs/submission/PHASE1_PROPOSAL.pdf) (rebuild: `python scripts/build_proposal.py`) |
| User guide for testers (Hinglish) | [docs/PRAMAAN_Project_Guide.pdf](docs/PRAMAAN_Project_Guide.pdf) |
| **Phase 2 technical-clinical report** | [docs/TECHNICAL_CLINICAL_REPORT.md](docs/TECHNICAL_CLINICAL_REPORT.md) · PDF: [docs/submission/TECHNICAL_CLINICAL_REPORT.pdf](docs/submission/TECHNICAL_CLINICAL_REPORT.pdf) (rebuild: `python scripts/build_proposal.py --src docs/TECHNICAL_CLINICAL_REPORT.md --name TECHNICAL_CLINICAL_REPORT`) |
| Expert validation (50 live answers, two independent raters) | `eval/expert_validation/`, `scripts/expert_validation.py`, reviewer workbooks in `docs/review/` |
| Earlier technical & impact report (v0.1, 7 Nov) | [docs/TECHNICAL_IMPACT_REPORT.md](docs/TECHNICAL_IMPACT_REPORT.md) |
| Latest evaluation & regression | [docs/evaluation_report.md](docs/evaluation_report.md) |
| Retrieval failures / experiments | [docs/RETRIEVAL_FAILURE_ANALYSIS.md](docs/RETRIEVAL_FAILURE_ANALYSIS.md), [docs/RETRIEVAL_EXPERIMENTS.md](docs/RETRIEVAL_EXPERIMENTS.md) |
| Hindi / Hinglish | [docs/INDIC_LANGUAGE_EVALUATION.md](docs/INDIC_LANGUAGE_EVALUATION.md) |
| Clinical safety & human review | [docs/CLINICAL_REVIEW_CHECKLIST.md](docs/CLINICAL_REVIEW_CHECKLIST.md), [docs/CLAIM_AUDIT_REVIEW_GUIDE.md](docs/CLAIM_AUDIT_REVIEW_GUIDE.md), `data/rules/safety_rules.yaml` |
| Dataset lineage & licences | [DATA_NOTICE.md](DATA_NOTICE.md), `data/sources/manifest.json`, [THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md) |
| Deployment / demo hosting / Docker / ZeroGPU | [docs/DEPLOYMENT.md](docs/DEPLOYMENT.md), [docs/DEMO_HOSTING.md](docs/DEMO_HOSTING.md), [docs/DOCKER_VALIDATION.md](docs/DOCKER_VALIDATION.md), [docs/ZEROGPU_COMPATIBILITY_REPORT.md](docs/ZEROGPU_COMPATIBILITY_REPORT.md) |
| Usability pilot | [docs/USABILITY_STUDY_PROTOCOL.md](docs/USABILITY_STUDY_PROTOCOL.md) |
| Finale demo / roadmap / competition | [docs/FINAL_DEMO_SCRIPT.md](docs/FINAL_DEMO_SCRIPT.md), [docs/EXECUTION_ROADMAP.md](docs/EXECUTION_ROADMAP.md), [docs/COMPETITION_CHECKLIST.md](docs/COMPETITION_CHECKLIST.md) |

## Testing
`cd backend && python -m pytest -q` (77 tests; no GPU needed). Live evaluation: `python -m pramaan.eval.run full --split all`
with the model server running. Retrieval experiments: `python -m pramaan.eval.retrieval_lab experiments`.

## Status (28 Nov 2026)
Latest full evaluation with live AyurParam (`eval/results/eval_full_pramaan_all_20261128_144035.json`, 120 cases):
displayed claims with a resolvable citation 78/78, fabricated citations accepted 0/4, emergency escalation 6/6
with 0/114 false alarms, safety-rule expectations 23/23, retrieval Hit@5 0.62 (37/60). Expert validation of
50 answers by our clinical lead and an external Ayurveda expert is underway; results go into §7 of the report.
Educational tool only: not a diagnosis, prescription or safety clearance.
