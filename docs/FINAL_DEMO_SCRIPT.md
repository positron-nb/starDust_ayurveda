# Final three-minute demonstration

Core question: **"How do we know whether an AI-generated Ayurveda explanation is genuinely supported by the classical text?"**
This supersedes `DEMO_SCRIPT.md` (kept only for the judge Q&A table).

## Before the slot (T-30 min)
| Check | How | Expected |
|---|---|---|
| GPU model server | `python model_server/server.py`; `curl 127.0.0.1:8601/health` | `"loaded": true`, revision 27c69ee |
| API + UI | `uvicorn --app-dir backend pramaan.api:app --port 8600`; open http://127.0.0.1:8600 | green **LIVE AyurParam** banner |
| Warm-up | run demo A once (first call loads caches) | `answered` |
| Lab base run | keep that demo-A run in the session | Lab dropdown shows it |
| Fallback A | second terminal ready: `PRAMAAN_LLM_MODE=fixture` | amber **FIXTURE REPLAY — NOT live** banner |
| Fallback B | screen recording of this exact script (record the day before) | file on desktop |
| Display | browser zoom 110 %, notifications off, Wi-Fi not required | — |
Stable inputs are the six Workspace example buttons (A-en, A-hi, B, D1, D2, E); fixture replay covers A-en, A-hi, B (unknown/present/absent), D1, D2.

## Script
| Time | Screen | Action | Say (≈) | Expected on screen |
|---|---|---|---|---|
| 0:00–0:20 | Workspace | — | "AI can write fluent Ayurveda. The question is whether a sentence is actually supported by Caraka or Vāgbhaṭa. PRAMAAN makes that checkable." | banner LIVE AyurParam · rev 27c69ee |
| 0:20–0:55 | Workspace | Click **A · Classical evidence (EN)** → **Retrieve & explain** (≈25–45 s; keep talking) | "AyurParam 2.9B runs locally. It explains one retrieved verse at a time; the backend attaches the source." Point at evidence cards. | E1 = AH Sūtrasthāna 13.25 with Devanagari, IAST and `xml:id Ah.1.13.025a–025c` |
| 0:55–1:30 | Workspace | Point at the shown sentence chips; open **Audit: N withheld** | "This sentence passed: citation checked, interpretation still pending human review. These were withheld — e.g. the model called āma 'toxic' and said it 'clogs channels'; this verse says neither." | 1 shown claim, ~9 withheld with reasons |
| 1:30–2:05 | Integrity Lab | Experiment **retract passage** on the demo-A run → Run | "On a disposable copy we delete the supporting verse. Same validator: the claim fails and the cached answer is invalidated. The real corpus is untouched." | before pass/yes → after **fail/no**; `cached result still valid = false`; main corpus modified false |
| 2:05–2:35 | Workspace | **B · Ashwagandha** → run (pregnancy *unknown*) → toggle Pregnancy **present** → Re-run; then **E · Urgent input** | "Unknown is not 'no' — it asks. With pregnancy present, an NCCIH-sourced rule withholds use. Emergency wording switches to urgent care and the model is never called." | R-PREG-ASHWA-002 → R-PREG-ASHWA-001 with scope; E: red Urgent-care panel |
| 2:35–3:00 | Evaluation & Review | Scroll the measured runs | "Every number is from a logged run: 81/81 displayed citations intact, 0 forged citations accepted — and our weakness, passage Recall@5 0.24. Human review is next and shown as pending." | review coverage 0/…; smoke test PASS |
Closing line: **"PRAMAAN does not ask practitioners to trust an AI-generated answer. It enables them to inspect the evidence, challenge the claim and retain control over clinical interpretation."**

## Failure recovery
| Failure | Recovery (≤10 s) |
|---|---|
| Model server not loaded / CUDA error | restart API with `PRAMAAN_LLM_MODE=fixture`; say "this is a labelled replay of recorded live outputs" |
| Generation slow (>60 s) | continue narrating the evidence cards (retrieval already shown); or switch to fixture |
| All sentences withheld | show the **Source-only fallback** — it is a feature: "no supported sentence, so we show the verses" |
| Browser/UI issue | play the screen recording; offer live Q&A on the recording |
| Laptop failure | recording on a second device/USB |
Never present fixture replay or the recording as live inference.

## Judge Q&A
See `DEMO_SCRIPT.md` → "Likely judge questions". Update the retrieval answer with: Hit@5 0.58–0.61 and
passage Recall@5 0.24 (77 inspected cases); a fresh reviewer-authored locked benchmark is in progress.
