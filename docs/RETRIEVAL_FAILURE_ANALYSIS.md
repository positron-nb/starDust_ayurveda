# Retrieval failure analysis

Date 2026-11-09 · code `ce3176d`+working tree (retrieval defaults unchanged) · corpus `corpus-226ed5c80f0a0612`
Data: `eval/results/retrieval_failures_20261109_154618.json` (`python -m pramaan.eval.retrieval_lab failures`).
Population: the 60 answerable + multilingual cases with gold passages in `eval/cases.jsonl`
(22 original dev + 38 former test). **All 60 have now been inspected; none is a held-out set.**
Gold labels are unreviewed AI candidates.

## 1. How the metrics are computed (verified in code)
| Metric | Code | Definition |
|---|---|---|
| Hit@5 | `eval/run.py::rank_metrics`, `retrieval_lab.evaluate` | 1 if any gold passage is among the first 5 **primary** evidence cards (adjacent-context and context-limiting cards excluded), averaged over cases. |
| Passage Recall@5 | same | |gold ∩ top-5| / |gold| per case, averaged over cases. |
| MRR | same | 1/rank of the first gold passage in the full primary list. |

Checks:
- Multiple acceptable passages per case: **yes** (`relevant_passages` list, 2–7 ids). Any one counts for Hit@5.
- Recall denominator is the full gold list. 13 of 60 cases have more than 5 gold ids, so a perfect
  retriever would still score mean Recall@5 = **0.942**, not 1.0.
- Duplicates: results are de-duplicated by text hash before ranking; no duplicate verse ids occur in gold lists.
- Populations: Hit@5 and Recall@5 are computed over the same cases. The earlier report (§6.1/6.2) used
  the 38 former-test cases only; this analysis also includes the 22 dev cases.
- Recall@5 is low partly because gold lists were written per *topic* (e.g. all 5 sāma-doṣa verses),
  while a question often needs only one or two of them. This is a **label-design issue**, to be fixed in
  the reviewer-authored benchmark (`eval/fresh_benchmark/`).

## 2. Results under the default configuration
Hit@5: devA 20/22 (0.909), devB 23/38 (0.605). Passage Recall@5: devA 0.423, devB 0.239.
By language (all 60): English 29/44 hits, Hindi (Devanagari) 14/16, Roman-script transliterated 4/4.
The Hindi/Roman numbers are small and are pairs of English questions on the same topics; they do not
establish parity (see INDIC_LANGUAGE_EVALUATION.md).

## 3. Classification of the 165 gold passages missing from the top 5
Automatic first pass from the diagnostics (ranks of each gold passage in the full BM25 and dense lists
and curated-concept overlap with the query), then spot-checked by reading the cases listed in §4.

| Cause | Missed gold passages | Taxonomy category |
|---|---:|---|
| Query concepts do not overlap the gold verse's concepts | 70 | 1/4 Sanskrit or English terminology mismatch (incl. curated-pattern gaps) |
| Gold verse is in BM25 or dense top-30 but not in fused top-5 | 68 | 5/7 BM25 / RRF ranking |
| Concept overlap exists but both retrievers rank > 30 | 22 | 6 embedding failure + 5 BM25 (generic concepts such as `agni` occur in 74 passages) |
| Continuation verse with no domain concept of its own | 5 | 9 chunking / context |
| Not in the index | 0 | 10 missing corpus evidence |

Not separately countable automatically but observed in the spot-check: **incorrect / over-broad gold labels**
(category 11), e.g. G12c and G07c ask "according to Charaka" but include Aṣṭāṅgahṛdaya verses; G05 and
G03 list every verse of a topic.

## 4. Representative cases (spot-checked)
| Case | Query (abridged) | Observation | Category |
|---|---|---|---|
| G14a/b/hi | Why is agni the root of life? | Ca Ci 15.3–5 rank ~30 in BM25; 74 indexed passages carry `agni`, nothing distinguishes "root of life" (mūla, āyus) | 1 + 5 |
| G15a | effects of viṣama, tīkṣṇa, sama, manda agni | "sama" is a curated alias of **āma** (sāma); the query is mapped to `ama` | 1 (alias collision) |
| G05c | how much of heavy and light foods | "heavy/light" (guru/laghu) not curated; gold has no query concept | 4 |
| G06a | deficient vs excessive quantity | "deficient" (hīna-mātra) not an alias | 4 |
| G10tr | ajirna ke prakar | "prakar" (types) not mapped to `ajirna_types`; 1/4 gold found | 3 |
| G12b | samashana, adhyashana, vishamashana | terms are not curated concepts; dense ranks gold 13–417 | 1 + 6 |
| G12c, G07c | "according to Charaka" | gold includes AH verses; no source-aware query filter | 8 + 11 |
| G09a | painkiller in ajīrṇa | Ah Sū 8.18 has `ajirna` but ranks 11 (BM25) / 48 (dense) | 5/6 |
| G20a | how each doṣa deranges agni in grahaṇī | 6 gold verses; Ca Ci 15.59/66 have no curated concept | 9 + 11 |

## 5. Conclusions
1. Parameter tuning cannot fix this (RETRIEVAL_EXPERIMENTS.md: no setting beat the default on devA).
2. The largest buckets are vocabulary coverage and ranking among many passages sharing a generic
   concept. Fixes must come from **reviewed terminology** (the BAMS teammate) and better passage
   representations (reviewed glosses), not from tuning on these inspected cases.
3. Gold labels must be rewritten per question (only the verses that answer it), with source constraints
   honoured, in a fresh locked benchmark.
4. "Sama" alias collision (sama vs sāma) is a concrete terminology bug to resolve with the reviewer.
