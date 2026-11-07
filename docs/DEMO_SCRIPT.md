# Three-minute demo script

Setup (before the slot): model server loaded (banner **LIVE AyurParam**), API at http://127.0.0.1:8600,
browser zoom 110 %, Workspace tab open, Integrity Lab primed with one answered run. Keep the fixture
fallback ready (`PRAMAAN_LLM_MODE=fixture`, banner turns amber: **FIXTURE REPLAY — NOT live**).
Live generation takes ~25–45 s per answered query: start demo A while speaking the first line.

| Time | Action | What to say |
|---|---|---|
| 0:00–0:20 | Title screen / Workspace | "Students and Vaidyas get fluent AI answers about Agni and Āma, but cannot tell which sentence comes from Caraka or Vāgbhaṭa, which is the model's own background, and what is unsafe for *this* patient. PRAMAAN keeps those apart." |
| 0:20–0:55 | Click **A · Classical evidence (EN)** → *Retrieve & explain*. Point at the green **LIVE AyurParam** banner and the run trace. | "AyurParam 2.9B runs locally at a pinned revision. It first expands the query into Ayurveda terms, then explains each retrieved verse separately, so every sentence is tied to the single passage the model saw." |
| 0:55–1:20 | Click the **[E#] AH Sū 13.25** chip → Source Explorer. | "Original IAST from the SARIT edition, Devanagari derived, xml:id locator, file hash, variants kept separate, adjacent verses, licence. The English gist is labelled an unreviewed AI draft — not a translation." |
| 1:20–1:40 | Back → open **Audit: N sentences withheld**. | "Most of what AyurParam writes is withheld: e.g. it calls āma 'toxic' and says it 'clogs channels', which this verse does not say. We measured this rate across the test set." (quote the number from the report) |
| 1:40–2:10 | Click **B · Ashwagandha safety** → run (pregnancy *unknown*: missing-information questions). Toggle Pregnancy → **present** → *Re-run with these facts*. | "Unknown is not 'no'. With pregnancy present, a sourced NCCIH rule withholds positive use and shows its scope. Classical mentions of aśvagandhā are shown as text only, never as clearance." |
| 2:10–2:35 | Integrity Lab → *retract passage* on the run from A → Run. | "On a disposable snapshot we retract the only supporting verse. The same validator now fails the citation, the claim disappears, and the cached answer is invalidated because cache keys include the corpus version. The real corpus is untouched." |
| 2:35–2:50 | Workspace → **D · Invented verse**, then **E · Urgent input**. | "A non-existent 'Charaka Sūtra 45.12' is refused. Emergency wording switches to an urgent-care message and the model is never called." |
| 2:50–3:00 | Evaluation & Review tab. | "All numbers come from logged runs on a frozen held-out split, with denominators. Clinical review is pending and shown as pending — our Ayurveda teammate's next job." |

## Reset between demos
- Workspace: load another example (clears result). Session runs: `POST /api/session/reset?session_id=…` (Lab uses snapshots that are deleted automatically).
- Admin reset (local only): `POST /api/admin/reset` clears cached runs and lab snapshots, keeps the review log.

## Likely judge questions — evidence-backed answers
| Question | Answer (with evidence) |
|---|---|
| Is AyurParam really running, or another model? | Banner + run trace show model id, revision `27c69ee`, device, `inference_ran=true`; smoke test log in `eval/results/smoke_*.json`. No other LLM is used at runtime. |
| Why not let AyurParam answer directly? | Measured: prompt probes (`eval/results/prompt_probe*.json`) show it rarely emits citation labels and adds background knowledge even with one passage. Config-1 (raw) outputs are stored for comparison and are never shown in the app. |
| Is it hallucination-free? | No, and we do not claim that. We withhold sentences that fail automatic checks and report the withheld rate; semantic support still needs human adjudication (not yet measured). |
| How good is retrieval? | Report the held-out test numbers from `eval/results/eval_full_pramaan_test_*.json` and the retrieval ablation; they are below our 0.85 target and the labels are unreviewed candidates. |
| Hindi / Sanskrit? | Hindi queries and output; Devanagari↔IAST transliteration; Sanskrit only as source text. Multilingual consistency is measured (top-5 Jaccard). No claim of evaluated Sanskrit understanding. |
| Why only Caraka and Aṣṭāṅgahṛdaya? | Structured, licensed TEI with real verse locators. Suśruta and other texts are future work; OCR-heavy sources were avoided for provenance reasons. |
| What about licences? | Code Apache-2.0; SARIT text CC BY-SA 3.0 kept separate with attribution; NCCIH public domain paraphrased; AyurParam licence metadata conflict recorded. |
| Clinical validation? | None yet. Review workflow exists (append-only log); checklist in `docs/CLINICAL_REVIEW_CHECKLIST.md`. |
| Business model? | Free open-source core; optional institutional hosting / curation / support. All adoption and revenue figures are assumptions until a usability study is run. |
