# Retrieval experiments

Command: `cd backend && python -m pramaan.eval.retrieval_lab experiments`
Result files: `eval/results/retrieval_exp_20261109_154821.json` (grid), `retrieval_exp_20261109_154909.json`
(inheritance runs). An earlier grid file was **invalid** (embedded-Qdrant lock made every second
configuration silently BM25-only) and is kept in `eval/results/invalid/` with an explanation.

| Field | Value |
|---|---|
| Git commit | working tree on top of `ce3176d` (retrieval knobs added; defaults identical) |
| Corpus / terms | `corpus-226ed5c80f0a0612` / `terms-2026.11.07.5` |
| Dataset | `eval/cases.jsonl`, 60 answerable+multilingual cases with gold lists, dataset hash `9d3a8ba39d4a4926` |
| Populations | **devA** = 22 original-dev cases (used to select) · **devB** = 38 former-test cases (inspected 2026-11-07; reported as a check only) |
| Labels | unreviewed AI candidates |
| Retrieval | retrieval path of the production `Engine` with `use_model=False` (no AyurParam expansion) |
| Hardware | AMD Ryzen 9 270, CPU retrieval, Python 3.12.10, multilingual-e5-small @ 614241f |
| Latency | p50 of `Engine.run` (normalise + facts + rules + retrieval + cards), devB |

| Experiment | devA Hit@5 | devA R@5 | devB Hit@5 | devB R@5 | p50 ms |
|---|---:|---:|---:|---:|---:|
| B0 default hybrid (RRF k60, k1 1.5, b 0.75, concept ×2) | 0.909 | 0.423 | 0.605 | 0.239 | 33 |
| B1 BM25 only | 0.864 | 0.416 | 0.526 | 0.229 | 8 |
| B2 dense only | 0.727 | 0.244 | 0.474 | 0.160 | 29 |
| R1 RRF k=20 | 0.909 | 0.434 | 0.579 | 0.236 | 33 |
| R2 RRF k=100 | 0.909 | 0.423 | 0.605 | 0.239 | 33 |
| K1 BM25 k1=1.2 | 0.909 | 0.423 | 0.605 | 0.245 | 33 |
| K2 BM25 k1=2.0 | 0.909 | 0.400 | 0.605 | 0.239 | 32 |
| K3 BM25 b=0.5 | 0.909 | 0.423 | 0.579 | 0.239 | 33 |
| K4 BM25 b=0.9 | 0.909 | 0.423 | 0.605 | 0.239 | 33 |
| C1 concept weight 1 | 0.909 | 0.400 | 0.605 | 0.223 | 33 |
| C4 concept weight 4 | 0.818 | 0.385 | 0.500 | 0.211 | 33 |
| W1 weighted RRF BM25×2 | 0.864 | 0.400 | 0.579 | 0.241 | 33 |
| W2 weighted RRF dense×2 | 0.864 | 0.389 | 0.579 | 0.234 | 32 |
| P1 candidate pool 60 | 0.909 | 0.423 | 0.605 | 0.239 | 34 |
| N1 next-verse expansion, top 2 | 0.636 | 0.390 | 0.500 | 0.245 | 34 |
| N2 next-verse expansion, top 1 | 0.864 | 0.429 | 0.579 | 0.270 | 33 |
| D1 dense text without concept labels | 0.864 | 0.377 | 0.395 | 0.119 | 33 |
| I1 inherit previous-verse concepts ×1 | 0.909 | 0.423 | 0.605 | 0.245 | 35 |
| I2 inherit previous-verse concepts ×2 | 0.909 | 0.423 | 0.605 | 0.250 | 36 |
| I1+N2 | 0.864 | 0.434 | 0.579 | 0.262 | 35 |

## Interpretation
- No configuration improves devA Hit@5, and the best devA Recall@5 gain is +0.011 (one passage across
  22 cases). Differences on devB (n = 38) are within one or two cases. **Defaults are kept unchanged.**
- Concept labels in the dense text matter a lot (D1 halves devB Recall@5): the e5 model does not read
  IAST Sanskrit well on its own. Reviewed glosses would likely help dense retrieval more than any knob.
- Neighbour expansion trades Hit@5 for Recall@5 (it pushes other hits out of the top 5).
- Reranking was not tried: no evidence yet that candidates are the bottleneck rather than vocabulary,
  and a cross-encoder adds a dependency and latency (see failure analysis §3).
- None of these numbers is a held-out result. The next comparable measurement must use the fresh,
  locked, reviewer-authored benchmark (`eval/fresh_benchmark/README.md`).
