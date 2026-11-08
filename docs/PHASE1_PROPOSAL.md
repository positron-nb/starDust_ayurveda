# PRAMAAN — Phase 1 Proposal
**AyushTech Innovate: National Open Ayurveda AI Challenge · Techfest IIT Bombay 2026–27**
Team: _[Team ID]_ · Team Leader: _[name]_ · Ayurveda member (BAMS/MD/PhD, NCISM-recognised institution): _[name, institution]_ · Engineering members: _[names]_

> Status labels used below: **Implemented** = runs in the current prototype and is covered by tests or
> logged runs; **Planned** = not yet built. No clinical validation has been performed.

## 1. Problem
Ayurveda students and Vaidyas increasingly ask general chatbots about classical concepts such as
Agni, Āma and Ajīrṇa. The answers are fluent but untraceable: the reader cannot tell which statement
comes from Caraka or Vāgbhaṭa, which is the model's background knowledge, which is a modern safety
statement, and what was assumed about the patient (for example, an unstated pregnancy). Errors
here are both academic (misattributed teaching) and clinical (unsafe herb suggestions).

## 2. Proposed solution
PRAMAAN is an evidence and safety workbench built around AyurParam. For a question or an educational
case it shows, side by side and never merged:
1. **Case facts** the user supplied, as present / absent / **unknown** (unknown is never treated as "no").
2. **Original passages** (Sanskrit IAST + derived Devanagari) with edition-specific locators and a source reader.
3. **AyurParam draft explanations**, one per passage, each bound by the backend to the only passage the model saw.
4. An **evidence ledger** per sentence: citation integrity (deterministic), support assessment (automatic heuristic, provisional), human review status, and a visible reason when a sentence is withheld.
5. A **safety review** from structured rules outside the model, with modern safety sources and product policy labelled separately from classical text.

### Innovation (our contribution — not the invention of RAG or provenance)
- **Per-passage generation with server-bound citations**: the model cannot invent citation metadata. (Implemented)
- **Withhold-and-show-why ledger**: generated sentences that introduce concepts absent from their passage are removed from the answer and listed with the reason; the withheld rate is itself a measured quality signal of the model. (Implemented)
- **Evidence Integrity Lab**: judges can retract a verse, tamper with its text, forge citations or inject instructions on a disposable snapshot and watch dependent claims and caches invalidate through the production validator. (Implemented)
- **Counterfactual safety**: flipping one fact (pregnancy unknown → present) changes the outcome through a cited rule, without ever implying that "absent/unknown" means safe. (Implemented)
- **Transparent evaluation** with "not measured" states instead of placeholder percentages. (Implemented)

## 3. User workflow
Enter question or synthetic case → confirm extracted facts → retrieve passages → read evidence and
missing facts → review safety alerts → record review / export a JSON or printable review packet.
Languages: English and Hindi questions and output; Sanskrit as source text. (Implemented)

## 4. Architecture (modular monolith + separate model process)
```
React/TS UI ──► FastAPI API ──► normalise → facts (tri-state) → safety precheck/escalation
                                → AyurParam concept expansion (HTTP) → hybrid retrieval
                                  (BM25 + concept tokens, e5-small dense in Qdrant, RRF)
                                → answerability gate → evidence selection under 2048-token budget
                                → AyurParam per-passage explanation (HTTP) → ledger validation
                                → render / cache (key includes model, prompt, corpus, rules versions)
            Model server (separate process): AyurParam @ pinned revision, bf16 GPU
            SQLite: corpus snapshot + append-only review log
```

## 5. AyurParam's role (Implemented, live)
`bharatgenai/AyurParam` @ `27c69eeef492…` is the only language model at runtime. Verified facts that
shaped the design: the chat template drops system messages (instructions are placed in the
documented `<context>` block); the context window is 2048 tokens (`config.json`), enforced with the
real tokenizer; EOS handling covers both declared EOS ids; the custom model code was reviewed and
hash-pinned before `trust_remote_code`. AyurParam performs (a) Ayurveda term expansion and (b)
evidence-bounded explanations. Every run trace records model id, revision, whether inference ran,
timings and corpus/rule versions.

## 6. Corpus and lineage (Implemented)
SARIT TEI editions of the Carakasaṃhitā and Aṣṭāṅgahṛdayasaṃhitā (pinned commit, sha256-verified,
CC BY-SA 3.0, attribution preserved). 16,980 segments parsed; 522 indexed for the initial module
(Caraka Vi 2, Ci 15, Sū 5; AH Sū 8, Sū 13; plus aśvagandhā mentions). Locators come from encoded
xml:ids; no verse or page number is invented. Variant readings are kept separate. Modern safety
example: NCCIH aśvagandhā page (public domain), paraphrased with scope and access date.

## 7. Safety design (Implemented; clinical review Planned)
Structured rules with scope, condition, outcome, basis type and review status; emergency wording →
urgent-care template and no model call; pregnancy / lactation / paediatric / medication / comorbidity
→ sourced caution or missing-information request; no doses, prescriptions or advice to stop
medicines; unsupported interactions → "not assessed", never "safe"; retrieved text treated as data
(control tokens neutralised); public demo read-only.

## 8. Evaluation plan
120 synthetic candidate cases (40 answerable, 20 multilingual, 20 safety, 20 unanswerable,
20 adversarial), grouped dev/test split with a frozen test hash; three configurations (raw AyurParam;
AyurParam + dense RAG; full PRAMAAN). Metrics: Hit@5 (≥1 relevant passage in top 5) and passage Recall@5 (fraction of relevant passages recovered) reported separately, MRR, resolved-citation rate,
fabricated-citation acceptance, withheld-sentence rate, correct abstention and over-refusal,
rule-expectation accuracy, multilingual consistency, latency p50/p95. Human-adjudicated support and
practitioner-reviewed safety are reported as **not measured** until reviews exist. Current measured
results: see §11.

## 9. Team roles
| Role | Responsibility |
|---|---|
| Ayurveda member (BAMS/MD/PhD) | Review passages, glosses, terminology, eval labels; co-design safety rules; clinical narrative in finale |
| ML/retrieval engineer | AyurParam integration, retrieval quality, evaluation |
| Full-stack engineer | UI, API, deployment, hosting |
| (Optional) 4th member | Usability study, documentation, business model |

## 10. Timeline
| Date | Milestone |
|---|---|
| by 15 Nov | Registration, enrolment proof upload |
| 15–22 Nov | Teammate review of glosses + 20 safety cases; proposal submission |
| 23–30 Nov | Extend reviewed passages to 100–200; hosting; re-run evaluation; usability pilot (opt-in, ≤10 students) |
| 1 Dec | Repo + hosted link + technical-clinical report |
| 2–14 Dec | Finale rehearsal, offline fallback |

## 11. Feasibility and current prototype status (7 Nov 2026)
Measured on the frozen held-out split (77 synthetic cases, unreviewed candidate labels; details in
`docs/TECHNICAL_IMPACT_REPORT.md`): 57/57 displayed generated claims pass citation integrity; 0/2
fabricated citations accepted; 4/4 emergency inputs escalated with 0/73 false escalations; 0/10
positive-use and 0/7 dose wordings shown where prohibited (regex proxies); 10/13 unanswerable
questions abstained; hybrid retrieval Hit@5 0.58–0.61 but passage Recall@5 only 0.22–0.24 (our target was Recall@5 ≥ 0.85, so it is clearly not met); useful-answer coverage 23/38 answerable cases; 85% of AyurParam's
generated sentences were withheld by the automatic checks (a cost, not a success rate: 13/38 answerable
cases ended with no generated text shown). Human-adjudicated support and
practitioner-reviewed safety: not measured yet. The full workflow runs locally
with live AyurParam on an 8 GB laptop GPU (load 28 s, 5.5 GB VRAM, ~25–45 s per answered query).
Hosting, clinical review and Suśruta / Anupāna / seasonal rules are not done.

## 12. Impact and business hypothesis (assumptions until measured)
Free open-source core (self-hostable by colleges and clinics); optional paid institutional hosting,
onboarding, curated/reviewed corpus modules and support. No users, partners or endorsements exist
today; adoption, time saved and revenue are **assumptions** to be tested in an opt-in usability study.
Commercial use must respect the CC BY-SA terms of the classical corpus.
