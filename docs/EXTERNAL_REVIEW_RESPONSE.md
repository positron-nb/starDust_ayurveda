# Response to the independent technical evaluation (2026-11-09)

Each recommendation was checked against the code and result files at `96efc57` and then acted on.
Classes: **Correct & necessary** · **Correct, lower priority** · **Already implemented** · **Needs modification** · **Not justified**.

## A. Assessment
| # | Recommendation | Verdict | Evidence / comment |
|---|---|---|---|
| 1 | Keep baseline (77) and regression (120) separate | Already implemented | evaluation_report.md §C uses separate columns and says "not an improvement claim" |
| 2 | No further blind RRF/BM25 grid | Correct & necessary | 20-config grid showed no devA gain (RETRIEVAL_EXPERIMENTS.md) |
| 3 | Exp 1: multi-view normalization | Correct, **needs modification** | Implemented as opt-in *views* that add concepts only (original text untouched). IndicXlit **not used**: it is a neural model with heavy dependencies, and the misses were vocabulary (no alias), not script; ITRANS transliteration via the existing indic-transliteration library was used for the "transliteration only" arm. Result: marginal |
| 4 | Reviewed concept dictionary with variants, context restrictions, source ref, negatives | Correct & necessary (partly done) | `roman_hindi_lexicon.yaml` has surface forms, concept, `requires_any` context, source_ref, negative examples — **reviewer status pending**; reviewer approval is the missing part |
| 5 | "fasting" alias must "remain fixed" | **Correction**: it was *not* fixed before | Only documented on 9 Nov morning. Now fixed (bare alias removed, terms `2026.11.09.1`) with 4 regression tests + 1 positive test |
| 6 | First check whether ranking-miss golds are in the candidate pool | Correct & necessary | Measured: pool@30 candidate recall 0.64–0.75 vs final R@5 0.24–0.42 → reranking had headroom |
| 7 | Exp 2: bge-reranker-v2-m3, 2×2, don't co-load with AyurParam | Correct & necessary | Licence Apache-2.0 verified at 953dc6f; run sequentially on GPU (AyurParam stopped). Result: mixed (devA −4, devB +3) → not adopted |
| 8 | Metrics: candidate recall@30/60, R@5, MRR@5, nDCG@5, p50/p95, per language | Implemented | `retrieval_lab pool` and `matrix` |
| 9 | gold_v1_original / gold_v2_adjudicated, direct/contextual/not relevant | Correct & necessary | v1 frozen with sha256; v2 sheet (460 rows) + importer ready; labels pending |
| 10 | Fresh locked benchmark | Already implemented (tooling) | `eval/fresh_benchmark/`, `benchmark_lock.py`, `retrieval_lab fresh` |
| 11 | Hinglish: preserve original, add Devanagari view, don't translate | Correct; implemented as opt-in | Translit view alone did not change Hinglish Hit@5 (3/7); lexicon view +1 (4/7). Need student-written Hinglish |
| 12 | Hinglish regression tests (5 types) | Partly implemented | Out-of-corpus-with-alias (4 tests), Roman/Devanagari pairs in `indic_cases.jsonl`; colloquial/ambiguous set needs native-speaker authorship |
| 13 | Three evaluation layers | Correct & necessary | Added as §10a of the proposal |
| 14 | Withholding is a usefulness cost | Correct & necessary | Proposal §11 now says so; demo must show one useful supported answer (demo A does: AH 13.25 sentence) |
| 15 | Evidence-ledger ablation | Correct; **needs modification** | No new generation needed: A = all generated sentences, B = displayed ones from the *same* audited run. `scripts/ledger_ablation.py` computes it from the audit (withheld sample re-weighted ×316/50). Status: not measured |
| 16 | Narrow scope statements | Correct | Proposal §16 now states 2 texts / 522 passages / one theme |
| 17 | PyTorch 2.8 8/8 ≠ full ZeroGPU compatibility | Correct | Report already says "not tested on ZeroGPU"; kept |
| 18 | Local GPU primary for the finale | Correct | FINAL_DEMO_SCRIPT.md |
| 19 | Docker remains untested | Correct | DOCKER_VALIDATION.md |
| 20 | Eligibility verification | Correct (human task) | COMPETITION_CHECKLIST.md / proposal checklist |
| 21 | "Both retrievers fail" = 22 (13.3%) etc. | Correct numbers | From `retrieval_failures_20261109_154618.json` |
| 22 | Usability study 5–8 | Correct, lower priority than audit | Protocol ready |

## B. Additional findings during verification
1. **Demo login bug** (would have broken a local passcode demo): Secure cookie over http. Fixed — cookie
   `Secure` now follows the request scheme / `X-Forwarded-Proto`; override with `PRAMAAN_COOKIE_SECURE`.
2. **OOC leaks persist** with generic words ("digestion" → agni, "diet" → ahara): 3/23 in every config.
   Removing `ahara` from answerability would trade 2 fixed leaks for 4 new over-refusals — documented, not changed.
3. The reranker's mixed result may come from scoring IAST + English labels (favours label-rich passages);
   unverified hypothesis.

## C. Status after this round
| Item | State |
|---|---|
| Production retrieval defaults | unchanged (no experiment earned adoption) |
| Production terminology | `terms-2026.11.09.1` (fasting alias only) |
| Tests | see final report (all passing) |
| Human claim audit / gold v2 / fresh benchmark | tooling ready, **0 labels** |
| ZeroGPU real run / tunnel / Docker | not done (need account / install / Docker host) |
