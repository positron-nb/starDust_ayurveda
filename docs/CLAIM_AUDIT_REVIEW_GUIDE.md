# Claim-support audit — reviewer guide

For the Ayurveda team member (BAMS / MD / PhD). Time needed: ~3–4 hours for 107 records (do it in
batches of ~25; see EXECUTION_ROADMAP.md). No software is needed except a spreadsheet program.

## What you are judging
Each record is **one sentence written by AyurParam** and **the one classical verse** PRAMAAN cited for
it. Answer one question only:

> Read in its context, does this verse support this sentence?

You are *not* judging whether the sentence is true in Ayurveda generally, whether it is clinically
useful, or whether the automatic check was right. A sentence can be true and still be unsupported by
*this* verse.

The draft English gloss next to some verses was written by an AI and is unreviewed. Judge against the
Sanskrit. If the gloss is wrong, say so in the comment.

## Populations
- `displayed` — PRAMAAN showed this sentence to the user (all 57 are included).
- `withheld` — PRAMAAN hid it (a 50-sentence sample). Its automatic reason is in `auto_withheld_reason`.
  Withheld does **not** mean wrong; the automatic check is conservative and lexical. Label it the same way.

Do not edit any `auto_*` column. Fill only the last six columns.

## Labels (`human_label`)
| Label | Use when | Example pattern (illustrative only, not a label for any record) |
|---|---|---|
| `supported` | Every substantive part of the sentence is stated in, or directly entailed by, this verse. | Sentence says āma is undigested rasa arising from weak digestive heat; the verse defines āma as undigested first dhātu due to weak ūṣman. |
| `partial` | The core idea is in the verse but the sentence adds at least one detail the verse does not state (e.g. a symptom, a cause, "toxic"). | Sentence lists heaviness and foul odour; the verse lists heaviness but not foul odour. |
| `unsupported` | The verse does not state the sentence's main claim (the verse may be about something else, or the claim is background knowledge). | Sentence about channels being blocked; verse is about food quantity. |
| `passage_misread` | The sentence contradicts the verse or attributes to it the opposite of what it says (negation reversed, wrong subject, wrong doṣa). | Verse says do NOT give pain-relieving medicine in ajīrṇa; sentence says give it. |
| `unresolved` | You cannot decide (ambiguous Sanskrit, needs commentary, needs a senior opinion). Explain why in the comment. | — |

`unresolved` rows are **not** counted as adjudicated. Do not guess to avoid it.

## Other columns
- `exact_supporting_text` — copy the exact Sanskrit words (IAST or Devanagari) that support the sentence.
  Required for `supported` and `partial`. Leave empty for `unsupported`.
- `reviewer_comment` — one line: what is missing, what was misread, or why unresolved.
- `reviewer_name` — your name (stored in the local review log; not published unless the team decides).
- `reviewer_role` — exactly one of `student_bams`, `student_md_phd`, `practitioner`, `engineer`, `other`.
- `review_date` — `YYYY-MM-DD`.

## Rules
1. Do one record at a time; read the full verse (IAST and Devanagari are the same text).
2. If two reviewers label the same file, each uses their own name; disagreements are kept, not averaged.
3. Do not change `record_id`. Do not delete rows; leave unlabelled rows empty (they stay "pending").
4. Students' labels are study annotations, not professional clinical approval.

## Importing (engineer)
```
python scripts/import_claim_audit.py eval/audit/claim_audit_<ts>.csv --dry-run   # check
python scripts/import_claim_audit.py eval/audit/claim_audit_<ts>.csv             # write review log + result file
python scripts/claim_audit_summary.py eval/audit/claim_audit_<ts>.csv            # progress report
```
Import is idempotent (re-importing creates no duplicates); a changed label by the same reviewer is
appended to the history and the latest label is used. The result file
`eval/results/eval_claim_audit_<ts>.json` appears in the Evaluation & Review screen and reports
displayed and withheld populations separately.
