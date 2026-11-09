# Fresh reviewer-authored retrieval benchmark

Why: the original 120 cases were written by an AI and all of them have been inspected. Any honest
held-out retrieval number now needs questions and gold passages written by the Ayurveda teammate
**before** anyone tunes on them.

## Target
40–50 questions; at least 20 go to the locked test split. Mix English, Hindi (Devanagari) and Roman
Hindi written the way students actually ask. Only Agni / Āma / Ajīrṇa topics covered by the indexed
chapters (Caraka Vi 2, Ci 15, Sū 5; AH Sū 8, Sū 13) — plus a few deliberately out-of-coverage
questions marked `coverage: none`.

## How to write it (reviewer)
1. Copy `template.csv` → `questions.csv`; one row per question.
2. Find gold passages in the app's Source Explorer (chapter reader / search) and copy the passage id
   (e.g. `Ah.1.13.25`). List **only** verses that actually answer the question.
   - `gold_passages`: verses that answer it (semicolon-separated)
   - `acceptable_passages`: verses that would also be acceptable (optional)
   - `source_constraint`: `caraka`, `ah` or blank if the question names a text
3. `split`: write `dev` or `test` yourself *before* showing the file to the engineer (≥20 `test`).
4. Do not look at PRAMAAN's answers for `test` questions while writing them.

## Lock, then evaluate (engineer)
```
python scripts/benchmark_lock.py eval/fresh_benchmark/questions.csv     # validates ids, writes questions.jsonl + LOCK
cd backend && python -m pramaan.eval.retrieval_lab fresh               # refuses if the file changed after locking
```
The lock records the sha256 of the test rows. Tuning is allowed on `dev` rows only; the evaluator
reports `dev` and `test` separately and flags any hash mismatch.
