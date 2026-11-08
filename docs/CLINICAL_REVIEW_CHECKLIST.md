# Clinical & domain review checklist

Nothing in PRAMAAN has been clinically or domain reviewed yet. Every item below is **pending** and is
shown as pending in the app. Reviews are recorded in the append-only review log (Evaluation & Review
screen, or `POST /api/reviews`), which stores reviewer name, self-declared role, decision, note,
timestamp and the previous decision. Roles are not verified by software; a student review is not
professional clinical approval.

## Reviewer record (fill per reviewer)
| Field | Value |
|---|---|
| Name | |
| Role | BAMS student / MD-PhD Ayurveda student / registered practitioner / other |
| Institution (optional) | |
| Registration no. (practitioners only, optional) | |
| Scope reviewed | |
| Date range | |
| Conflicts of interest | |

## A. Corpus and source text (Ayurveda teammate)
| Item | Count | Acceptance condition |
|---|---|---|
| Indexed passages (5 chapters + aśvagandhā mentions) | 522 | Locator (sthāna.adhyāya.verse) matches the cited edition; base text not mixed with variants; module membership sensible. Sample at least the 60 passages used as relevance labels in `eval/cases.jsonl`. |
| Module selection (`data/curated/modules.yaml`) | 5 chapters | Chapters are appropriate for Agni / Āma / Ajīrṇa teaching; note important missing chapters. |
| Draft English gists (`data/curated/glosses_draft.yaml`) | 15 | Accept / correct / reject each. Mark which are close to the text vs interpretive. Rejected gists must be removed before demo. |
| Terminology (`data/terminology/terminology.yaml`) | 37 concepts (33 domain + 4 question-intent markers) | English/Hindi aliases acceptable as search aids; no alias implies a modern diagnosis; patterns do not over-match (check notes on āma, ajīrṇa, ūṣman). |

## B. Safety rules (qualified practitioner)
For each rule in `data/rules/safety_rules.yaml`: is the scope correct, is the outcome proportionate,
is the basis labelled correctly (product policy vs modern source vs classical source)?

| Rule | Basis | Specific question for reviewer |
|---|---|---|
| R-EMERG-001 + template T-URGENT-001 | product policy | Are the red-flag phrases adequate and not alarming for common benign phrasing? Is the template wording appropriate for India (no phone numbers are shown by design)? |
| R-PREG-ASHWA-001/002 | NCCIH / product policy | Is "withhold positive use when pregnancy is present or unknown" appropriate? |
| R-LACT-ASHWA-001/002 | NCCIH / product policy | Same for lactation. |
| R-MED-ASHWA-001/002 | NCCIH | Wording "not assessed" acceptable? |
| R-COMORB-ASHWA-001 | NCCIH | Comorbidity list complete for this example? |
| R-PED-001/002 | product policy | Age threshold 18 appropriate? |
| R-HERB-UNSUPPORTED-001 | product policy | — |
| R-DOSE-001, R-STOPMED-001 | product policy | — |

## C. Evaluation cases (`eval/cases.jsonl`, 120 synthetic candidates)
| Category | n | What the reviewer confirms |
|---|---|---|
| answerable | 40 | Question is answerable from the module; candidate `relevant_passages` are correct and complete enough. |
| multilingual | 20 | Hindi / transliterated phrasing is natural and equivalent to its English pair. |
| safety | 20 | Expected rules (`must_fire`) are clinically right; nothing important is missing. **Requires practitioner.** |
| unanswerable | 20 | Truly outside the indexed corpus (note: some are in other parts of Caraka that are not indexed). |
| adversarial | 20 | Escalation cases are genuinely urgent; fabricated locators are genuinely non-existent. |

Acceptance for reporting "expert-reviewed" metrics: ≥80% of the test split reviewed, all safety cases
reviewed by a practitioner, disagreements resolved and documented.

## D. Generated claims (human adjudication of semantic support)
Ready-made sheet: `python scripts/export_claim_audit.py` → `eval/audit/claim_audit_<ts>.csv` + printable
`.html` (all 57 shown claims + 50 withheld sentences, each with its verse in IAST and Devanagari).
Fill `support_label` (supported / partial / unsupported / passage_misread), `exact_supporting_text`,
`reason`, `reviewer_name`, `reviewer_role`, `review_date`, then
`python scripts/import_claim_audit.py <filled.csv>` — this writes the labels to the review log and
produces `eval/results/eval_claim_audit_*.json` (the first real support metric).

Sample ≥50 shown claims from `eval/results/eval_full_pramaan_test_*.json` (`per_case[].shown`) and
≥50 withheld sentences. For each: does the cited passage actually support the sentence in context?
(Yes / partially / no / passage misread.) This yields the "human-adjudicated claim support" metric,
currently **not measured**.

## E. Things the reviewer should challenge
- Any place the UI could be read as diagnosis, prescription, dose or safety clearance.
- Context-limiting candidates labelled "potential difference; review needed" — are any genuine contradictions?
- Whether classical aśvagandhā mentions are displayed in a way that could be read as endorsement.
