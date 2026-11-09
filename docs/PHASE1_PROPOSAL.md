# PRAMAAN: An AyurParam-Powered Ayurveda Evidence and Safety Workbench for Classical Text Exploration and Practitioner-Assisted Review

**AyushTech Innovate: National Open Ayurveda AI Challenge — Techfest, IIT Bombay 2026–27 · Phase 1 proposal**
Team ID: _[to fill]_ · Team Leader: _[name]_ · Ayurveda member (BAMS / MD (Ayu) / PhD (Ayu), NCISM-recognised institution): _[name, institution, enrolment proof uploaded? yes/no]_ · Engineering members: _[names]_
Repository: https://github.com/positron-nb/starDust_ayurveda (branch `pramaan-prototype`) · Licence: Apache-2.0 (code); CC BY-SA 3.0 (classical corpus, separate notice)

> Status labels used throughout: **Implemented & tested** · **Implemented, not yet validated** · **Planned**.
> Nothing in PRAMAAN has been clinically validated. All evaluation labels so far are synthetic and unreviewed.

---

## 1. Executive summary
AI answers about Ayurveda are fluent but hard to verify: a reader cannot tell which sentence comes from
Caraka or Vāgbhaṭa, which is the model's own background, and what was assumed about the person.
PRAMAAN is **not a chatbot**. It is a workbench in which AyurParam explains **one retrieved classical
verse at a time**, the backend attaches the citation, every sentence passes citation-integrity and
support checks, unsupported sentences are **withheld with a visible reason**, and a model-independent
safety layer handles pregnancy, medication, emergencies and missing information. When generation fails,
users still get the original verses (**source-only fallback**). A human-review workflow and an
**Integrity Lab** let reviewers challenge the system. The prototype runs end-to-end with live AyurParam
on an 8 GB laptop GPU.

## 2. Problem statement
Students and Vaidyas need to (a) locate the verse that actually addresses a question, (b) see whether an
explanation is supported by that verse, and (c) avoid unsafe generalisation to a specific person.
Measured on our own prototype: when given a verse, AyurParam adds content the verse does not contain in
most sentences (85% of 557 generated sentences failed our automatic support check, §15). Traceability
therefore has to be enforced by the system, not assumed from the model.

## 3. Intended users and use cases
Primary (first release): **BAMS/MD students and faculty** reviewing classical evidence on Agni, Āma and
Ajīrṇa. Secondary, bounded: **Vaidyas** checking what the texts say and which safety facts are missing
for an educational case. Out of scope: patients, diagnosis, prescription, dosing, safety clearance.

## 4. Proposed solution — workflow (Implemented & tested)
Question or synthetic case → extracted facts shown as present / absent / unknown (user can edit) →
hybrid retrieval of original passages → AyurParam explains each passage → evidence ledger → safety
alerts and missing-information questions → review / export packet (JSON, printable HTML).
English and Hindi questions and output; Sanskrit shown as original text (IAST + derived Devanagari).

## 5. Innovation and novelty
We do not claim to have invented RAG or provenance. Our contribution is the combination, applied to
classical Ayurveda and made inspectable:
1. **Verse-level AyurParam explanation** with server-bound citations — the model never writes citation metadata.
2. **Claim-level evidence ledger**: integrity (deterministic), support (automatic, provisional), human review (separate).
3. **Withhold-and-explain**: unsupported sentences are removed from the answer and listed with reasons.
4. **Source-only fallback** keeps the tool useful when generation fails.
5. **Model-independent safety** with explicit present/absent/**unknown** facts; unknown is never treated as no.
6. **Integrity Lab**: retract or tamper with a verse, forge a citation or inject instructions on a disposable
   snapshot and watch dependent claims and caches invalidate through the production validator.
7. **Honest evaluation**: "not measured" instead of placeholder numbers; displayed vs withheld populations separated.
None of this guarantees factual correctness.

## 6. Corpus and dataset provenance (Implemented & tested)
SARIT TEI editions of the Carakasaṃhitā (Trikamji 1941 e-text) and Aṣṭāṅgahṛdayasaṃhitā (Das &
Emmerick base text), pinned commit and sha256-verified; CC BY-SA 3.0 with attribution. 16,980 segments
parsed; **522 indexed** for the module (Caraka Vi 2, Ci 15, Sū 5; AH Sū 8, Sū 13; + aśvagandhā mentions).
Locators are the encoded `xml:id`s (e.g. AH Sūtrasthāna 13.25 = `Ah.1.13.025a–c`); no verse or page
number is invented; variant readings are kept separate. Modern safety example: NCCIH aśvagandhā page
(public domain), paraphrased with scope and access date. 15 English gists are unreviewed AI drafts and
labelled as such. Open questions: SARIT header also says `status="restricted"`; AyurParam metadata says
Apache-2.0 while its card shows CC-BY-4.0 — both recorded, not resolved.

## 7. AyurParam architecture and integration (Implemented & tested)
`bharatgenai/AyurParam` @ `27c69ee` (2.86 B parameters, custom `parambharatgen` Llama-style GQA) is the
**only** language model at runtime. Separate model server; bf16 on GPU; custom code sha256-checked before
`trust_remote_code`; 2048-token window (`config.json`) enforced with the real tokenizer; the chat template
drops system messages (verified), so instructions go in the documented `<context>` block. Roles:
(a) Ayurveda term expansion (few-shot, only curated concepts accepted), (b) per-passage explanation.
Every run trace shows model id, revision, whether inference ran, timings and corpus/rule versions.
PyTorch 2.8 tested in isolation: 8/8 outputs byte-identical to 2.7.1 (§17).

## 8. Hybrid retrieval design (Implemented & tested; quality is our main weakness)
BM25 over ASCII-folded IAST tokens plus curated concept tokens, and multilingual-e5-small dense vectors
(IAST + curated English concept labels) in Qdrant, fused by reciprocal rank fusion; answerability gate
requiring a queried domain concept with lexical support (threshold chosen on the dev split).
A 20-configuration controlled study found no parameter setting that beats the default on the selection
set; the failure analysis attributes misses mainly to terminology coverage, ranking among many passages
sharing generic concepts, and over-broad gold labels (§15, docs/RETRIEVAL_FAILURE_ANALYSIS.md).

## 9. Evidence ledger (Implemented & tested)
Each claim stores id, text, type, evidence ids, exact support spans, source locations, interpretation
status, citation integrity, support assessment, review status, limitations and producing model/prompt/
corpus versions. Results are revalidated on every display/export; a changed corpus marks them stale.

## 10. Citation integrity verification (Implemented & tested)
Passage exists and is not revoked; source file hash equals the manifest pin; text hash equals the hash at
answer time; locator resolves; quoted spans match. Invented references ("Charaka Sūtrasthāna 45.12") and
labels the model was not shown are rejected. **Integrity is structural, not semantic correctness.**

## 11. Claim withholding (Implemented & tested; heuristic)
A sentence is shown only if its citation passes and every curated concept it mentions is present in the
cited verse; dose wording, pregnancy-safety assertions and (when a safety rule is active) positive-use
wording are always withheld. The check is lexical: it misses relations, negation and qualifiers, so a
shown sentence can still overstate the verse — hence the human audit (§14).

## 12. Source-only fallback (Implemented, browser-checked)
If AyurParam is unavailable or every sentence is withheld, the top verses, their gloss status and an
explicit evidence-gap note are shown instead of an empty answer.

## 13. Safety architecture (Implemented & tested; clinical review pending)
13 YAML rules evaluated outside the model, each labelled product policy / modern safety source /
classical source. Emergency wording → urgent-care template, model never called. Pregnancy, lactation,
age, medication, comorbidity → sourced caution or missing-information question. A question *about*
pregnancy keeps pregnancy unknown; only an explicit statement or the case box sets it present. Doses,
prescriptions and advice to stop medicines are refused; unsupported herbs/interactions are "not assessed".
Retrieved text is sanitised against prompt injection. Optional passcode-protected public demo mode.

## 14. Evaluation methodology
120 synthetic candidate cases (40 answerable, 20 multilingual, 20 safety, 20 unanswerable, 20 adversarial),
grouped dev/test split. **The 77-case test split was inspected during failure analysis and is now treated as
development data.** Next: (1) human claim-support audit of 107 records (57 displayed + 50 withheld) by our
Ayurveda member using five labels including *unresolved*; (2) a **fresh, reviewer-authored, locked
retrieval benchmark** (40–50 questions, ≥20 locked test); (3) a 5–8 student usability pilot. Tooling for
all three is implemented (import is idempotent; the locked set refuses evaluation if altered).

## 15. Actual measured results (synthetic, unreviewed labels; not held-out)
Baseline reported on 2026-11-07 (77 former-test cases, live AyurParam, RTX 5060 Laptop):

| Metric | Result |
|---|---|
| Evaluation cases / former-test cases | 120 / 77 |
| Hit@5 (≥1 relevant passage in top 5) | 0.58–0.61 |
| Passage Recall@5 (fraction of relevant passages recovered) | **0.24** (target 0.85 — not met) |
| Displayed claims passing citation integrity | 57/57 |
| Generated sentences withheld | 316/373 |
| Useful answers on answerable cases | 23/38 |
| Fabricated citations accepted | 0/2 |
| Emergency escalation / false alarms | 4/4 · 0/73 |
| Correct abstention on unanswerable | 10/13 |
| Latency p50 | 8.2 s |
| Human-judged claim support | **NOT MEASURED** |
| Clinical/domain validation | **NOT COMPLETED** |

Regression run on 2026-11-09, all 120 cases (dev + inspected; a different population, not an improvement
claim): citation integrity 81/81, withheld 476/557, useful answers 35/60, fabricated citations accepted
0/4, escalation 6/6 with 0/114 false alarms, abstention 17/20, p50 8.5 s; safety-rule expectations 23/23
after a stop-medication fix. Hindi/Hinglish: Devanagari close to English on a small set, Roman Hinglish
clearly worse (2/7 vs 6/7 Hit@5 with the model) — **parity not established**.

## 16. Limitations
Weak retrieval recall; automatic support check is lexical; zero human or clinical review so far; labels
synthetic; Hindi parity unproven; Suśruta, Anupāna and seasonal rules not covered; single-GPU,
single-request inference; Docker untested; public hosting not yet live; licence questions above.

## 17. Deployment plan
(a) **Primary demo**: team laptop (RTX 5060) + passcode-protected Cloudflare tunnel exposing only the API
— application controls implemented and tested, tunnel to be set up (Planned). (b) **Experiment**:
inference-only Gradio Space on Hugging Face ZeroGPU behind an interchangeable adapter with automatic
local fallback — PyTorch 2.8 compatibility and the Space code verified locally; a real ZeroGPU run is
Planned (requires the team's eligible HF account). (c) Docker Compose files exist; validation Planned.

## 18. Open-source contribution
Apache-2.0 code: secure TEI ingestion with verse locators, evidence-ledger and integrity checks,
idempotent human-audit tooling, locked-benchmark tooling, Integrity Lab, evaluation runners with explicit
"not measured" states. Data kept under its own licence with attribution.

## 19. Real-world impact (hypotheses, to be measured)
For students: faster location of the relevant verse and clearer separation of text vs interpretation.
For teachers: review packets that show sources, withheld claims and open questions. We will measure
task completion, time and misinterpretation in the usability pilot; no adoption, cost or revenue figure
is claimed. Business hypothesis: free self-hostable core; optional institutional hosting, curated
reviewed modules and support — subject to CC BY-SA terms.

## 20. Roadmap (dates in docs/EXECUTION_ROADMAP.md)
By 22 Nov: complete the human claim audit, terminology review, fresh benchmark authored and locked.
By 1 Dec: retrieval improvements measured on the locked set, hosted demo link, usability pilot, Docker
validation, updated report. After: more chapters with reviewed glosses, Suśruta, Anupāna/seasonal rules,
reranking only if measured benefit.

## Eligibility checklist (team to confirm — software cannot)
☐ 2–4 members · ☐ ≥1 actively enrolled BAMS / MD (Ayurveda) / PhD (Ayurveda) student from an
NCISM-recognised institution · ☐ enrolment proof uploaded at registration · ☐ Team Leader designated
(only they submit) · ☐ registration completed by 15 Nov.
