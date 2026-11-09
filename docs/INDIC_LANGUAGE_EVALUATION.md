# Hindi / Hinglish evaluation

**Conclusion: parity is NOT established.** Devanagari Hindi is close to English on this small set;
Roman-script Hinglish is clearly worse. Sample sizes are tiny and the questions were written by the
build assistant, not by native-speaker students.

## Data
`eval/indic_cases.jsonl`: 8 intents × 3 variants = 24 questions (English, Hindi in Devanagari, Roman
Hinglish), written fresh (not translations of the 120 earlier cases). 7 intents have candidate gold
passages; 1 intent (intermittent-fasting apps) is deliberately out of corpus. Labels unreviewed.

## Metrics (defined per variant, then across the three variants of the same intent)
- Hit@5 / Recall@5: as in RETRIEVAL_FAILURE_ANALYSIS.md, per variant (n = 7 answerable each).
- Out-of-corpus abstention: status `insufficient_evidence` on the out-of-corpus intent (n = 1 each).
- Status agreement: all three variants of an intent end in the same status (n = 8 intents).
- Top-5 Jaccard: overlap of the top-5 passage sets, English vs each other variant.
Answer quality is **not** measured here (needs human review); evidence-status agreement is.

## Results (commit `5a3fd70` + working tree; files `eval/results/indic_eval_retrieval_20261109_160526.json`, `indic_eval_model_20261109_160934.json`)
| | English | Hindi (Devanagari) | Roman Hinglish |
|---|---|---|---|
| Hit@5, retrieval only (no AyurParam) | 4/7 | 3/7 | 3/7 |
| Hit@5, with live AyurParam expansion | 6/7 | 5/7 | **2/7** |
| Out-of-corpus abstained (retrieval only) | 0/1 | 1/1 | 0/1 |
| Out-of-corpus abstained (with model) | 0/1 | 1/1 | 0/1 |

| Across variants | Retrieval only | With model |
|---|---|---|
| Status agreement (all three equal) | 6/8 | 5/8 |
| Top-5 Jaccard EN vs HI | 0.521 | 0.334 |
| Top-5 Jaccard EN vs Hinglish | 0.491 | 0.279 |

Earlier measurement on the original 20 translated pairs (live, all 120 cases, `eval_full_pramaan_all_20261109_160413.json`):
status agreement 9/20, top-5 Jaccard 0.368.

## Errors observed
1. **Roman Hinglish vocabulary**: "apach", "painkiller", "kitna khana", "zindagi" map to no curated concept;
   I2-hinglish mapped to *no* concept at all and was declared insufficient.
2. **Out-of-corpus leak**: "fasting" is a curated alias of laṅghana, so "intermittent fasting apps" became
   answerable in English and Hinglish; only Devanagari abstained. A general-language word turned a
   modern-product question into a classical one.
3. **AyurParam expansion helps English/Hindi but not Hinglish** in this sample (it adds Sanskrit terms
   for well-formed questions but not for code-mixed ones), and it lowers cross-variant overlap because it
   adds different terms per variant.
4. **Definition questions (I1)**: none of the variants ranks AH Sū 13.25 in the top 5 without expansion.

## Next steps (need the Ayurveda teammate)
- Collect 30+ questions written by students in their own Hinglish; add reviewed Roman spellings to the
  terminology (with the over-match notes).
- Remove or qualify the bare "fasting" alias (only "laṅghana"-context phrases).
- Re-measure on the fresh locked benchmark with `language` per row.
