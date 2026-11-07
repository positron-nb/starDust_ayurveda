# Evaluation

- `build_cases.py` → `cases.jsonl` (120 synthetic candidate cases: 40 answerable, 20 multilingual,
  20 safety, 20 unanswerable, 20 adversarial). **All labels are candidate labels written by the build
  assistant; none has been reviewed by a domain expert or practitioner.**
- Split by `group` (a question and its translations share a split). `FROZEN_TEST_SHA256` is the hash of
  the test split; every result file records `frozen_test_split_unchanged`.
- Tuning (terminology additions, answerability threshold `min_bm25 = 6.0`) used the **dev** split only.
  The test split was evaluated after tuning stopped.
- Runner: `python -m pramaan.eval.run {retrieval|full|dense_rag|raw} --split {dev|test|all}` from `backend/`.
  Results: `results/eval_<config>_<split>_<timestamp>.json` (metrics with numerators/denominators,
  per-case records, failures). Metrics needing humans are written as `value: null` with a reason and
  shown as "not measured" in the app.
- Earlier result files are kept as history (their `corpus_version` differs); the newest file per
  config/split is the current one.
- `fixtures/ayurparam_replay.jsonl`: outputs recorded from live AyurParam runs for demo prompts; used
  only in `PRAMAAN_LLM_MODE=fixture`, which the UI labels as FIXTURE REPLAY.
