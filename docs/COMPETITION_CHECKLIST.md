# Competition checklist — AyushTech Innovate (Techfest IIT Bombay 2026–27)

Source: the competition brief PDF supplied by the team (5 pages). Re-check the official portal
(techfest.org) and announcement emails before every submission; this file is not authoritative.
**PRAMAAN tooling does not submit anything and must not be used to act as the Team Leader.**

## Key dates (from the brief)
| Date | Event | Status |
|---|---|---|
| 15 Nov 2026 | Registration closes | ☐ Team Leader to register at techfest.org → receive Team ID |
| 22 Nov 2026 | Phase 1 proposal deadline | ☐ Submit `docs/PHASE1_PROPOSAL.md` (exported to the required format) via portal |
| 25 Nov 2026 | Phase 1 shortlist announced | ☐ |
| 1 Dec 2026 | Phase 2: repository link + **live hosted app link** + technical-clinical report | ☐ Hosting NOT done (see DEPLOYMENT.md) |
| 15–18 Dec 2026 | Grand Finale at IIT Bombay | ☐ Demo per `docs/DEMO_SCRIPT.md`, offline replay prepared |

## Team and eligibility (humans only — software cannot satisfy these)
- ☐ 2–4 members.
- ☐ ≥1 actively enrolled BAMS / MD (Ayurveda) / PhD (Ayurveda) student from an NCISM-recognised institution.
- ☐ Proof of enrolment (student ID / NCISM institution letter) uploaded at registration.
- ☐ Remaining members from engineering / data science / CS / related disciplines.
- ☐ Designate the Team Leader (only they submit via the portal).
- ☐ Clinical/technical queries go to the portal's Doubt section; watch announcements from the address given in the brief.

## Required deliverables (brief §"Scope & Required Deliverables")
| # | Deliverable | Where in this repo | State |
|---|---|---|---|
| 1 | Open-source repo with install + deployment docs | `README.md`, `docs/DEPLOYMENT.md` | Code ready locally; **not yet pushed** to GitHub/GitLab (needs the team's account) |
| 2 | Functional application integrating AyurParam | `backend/`, `model_server/`, `frontend/` | Works locally with live AyurParam on GPU; **hosted link missing** |
| 3 | Grounding & safety architecture documentation | `docs/TECHNICAL_IMPACT_REPORT.md` §3–5, `data/rules/safety_rules.yaml` | Written |
| 4 | Technical & impact report | `docs/TECHNICAL_IMPACT_REPORT.md` | Written with measured numbers; clinical review sections pending humans |
| – | Phase 1 proposal | `docs/PHASE1_PROPOSAL.md` | Draft ready; team to edit names/roles |
| – | Licence MIT or Apache-2.0 | `LICENSE` (Apache-2.0) | Done for code. Corpus is CC BY-SA 3.0 (separate `DATA_NOTICE.md`) — **ask organisers via Doubt section whether bundling CC BY-SA data is acceptable**, or ship data via the fetch script only |
| – | AyurParam as a core component | `model_server/server.py`, `backend/pramaan/llm.py` | Live inference verified at pinned revision 27c69ee |

## Points from the brief that this prototype does NOT fully meet (be upfront with judges)
- "Hallucination-free": not claimed. PRAMAAN withholds sentences that fail automatic checks and
  measures how often AyurParam adds unsupported content; that is mitigation, not elimination.
- Sushruta Saṃhitā is named in the criteria; only Caraka and Aṣṭāṅgahṛdaya are indexed.
- Anupāna and seasonal restrictions are named as contraindication examples; not implemented.
- "Multiple Indian languages": English + Hindi output; Sanskrit shown as source text only; no other
  regional languages.
- Clinical validity: no qualified reviewer has assessed any passage, rule or case yet.

## Before 1 December
- ☐ Ayurveda teammate reviews glosses, terminology, 20 safety cases, module passages (Evaluation & Review screen).
- ☐ Practitioner review of `data/rules/safety_rules.yaml` and the urgent-care template.
- ☐ Push repo; set up hosting (DEPLOYMENT.md options); record fixtures for offline replay.
- ☐ Re-run `python -m pramaan.eval.run full --split test` after reviews; update report numbers.
