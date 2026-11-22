# Why this run is invalid

`eval_full_pramaan_all_20261122_174109.json` must not be reported.

- The API server held the embedded Qdrant index, so the dense retriever could not open it
  (`Storage folder ... is already accessed by another instance of Qdrant client`): the run is BM25-only,
  which is not the production configuration.
- Only 5 of 120 cases ran live AyurParam inference (`n_live_inference`), because the GPU was shared
  with another training job and the model server was stopped before the run finished.

Valid full-pipeline numbers remain those in `eval/results/eval_full_pramaan_all_20261109_160413.json`.
To re-run: stop the API server (frees the Qdrant lock), make sure the model server has the GPU, then
`python -m pramaan.eval.run full --split all`.
