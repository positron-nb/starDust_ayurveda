# PRAMAAN — Technical & Clinical Impact Report
Version 0.1 · 7 November 2026 · prototype status. Every number below is taken from a result file in
`eval/results/` (file names given). Items that need human judgment are reported as **not measured**.
No clinical or domain review has been performed yet.

## 1. Problem and scope
Students and Vaidyas need to check what Caraka and Vāgbhaṭa actually say about Agni, Āma and Ajīrṇa,
and whether a proposed herb is appropriate for a specific person, without trusting an untraceable
chatbot paragraph. PRAMAAN is a study / clinician-support workbench, **not** a diagnostic,
prescribing, dosing or clearance tool. Initial module: Agni / Āma / Ajīrṇa (5 classical chapters) and
one bounded herb-safety example (aśvagandhā + pregnancy, from NCCIH).

## 2. Architecture
```
frontend (React/TS/Tailwind)  ──HTTP──►  API (FastAPI, backend/pramaan)
   Workspace · Source Explorer             pipeline.Engine.run():
   Integrity Lab · Evaluation & Review       1 normalise (NFC, Devanagari→IAST, curated aliases)
                                             2 tri-state facts (rule-based; user confirms/edits)
                                             3 safety precheck → escalation template (stop)
                                             4 AyurParam concept expansion  ──HTTP──► model_server
                                             5 hybrid retrieval: BM25(+concept tokens) ∥ e5-small/Qdrant → RRF
                                             6 answerability gate (min_bm25 = 6.0, dev-calibrated)
                                             7 evidence cards (+adjacent half-verse, +context-limiting candidate,
                                               +herb textual mentions)
                                             8 safety rules (YAML, outside the model)
                                             9 AyurParam per-passage explanation ──HTTP──► model_server
                                            10 ledger validation (integrity, support heuristic, policy filters)
                                            11 cache (key: input, facts, model rev, prompt, corpus, rules, terms) + render
   storage: corpus.sqlite (read-only snapshot), app.sqlite (runs cache + append-only review log)
model_server: AyurParam @ 27c69ee, bf16 CUDA, greedy decoding, enforces prompt+output ≤ 2048
```
Design choices: a modular monolith with plain functions (no orchestration framework); the model runs
in a separate process so API/UI health never depends on weights; embedded Qdrant locally, Qdrant
server in Compose.

## 3. AyurParam integration (model card)
| Item | Verified value |
|---|---|
| Model / revision | `bharatgenai/AyurParam` @ `27c69eeef492bbc9e2c0048fc1e95959ffc0820e` (2,860,673,024 parameters) |
| Architecture | custom `parambharatgen` (Llama-style GQA: 32 layers, hidden 2048, 16 heads / 8 KV heads) |
| Remote code | `modeling_parambharatgen.py` sha256 `4745b5bc…`, `config_parambharatgen.py` `9d89451d…` — imports only torch/transformers; hashes checked before `trust_remote_code` |
| Context limit | 2048 (`config.json`). Tokenizer `model_max_length` = 1e30 sentinel, ignored |
| Chat template | serialises only user/assistant turns; **a system message is silently dropped** (verified: `smoke_20261107_231253.json`). Instructions are placed in the documented `<context> … <user> … <assistant>` prompt style |
| EOS | tokenizer `</actual_response>` (id 256005) vs config `eos_token_id` 3 → server stops on both |
| Runtime | PyTorch 2.7.1+cu128, transformers 4.53.1, bf16 on RTX 5060 Laptop 8 GB; load 27–28 s; 5,488 MB after load; ~13–14 tok/s with KV cache |
| KV cache | on/off outputs identical in 2/4 probes, minor wording divergence in 2/4 (bf16 numerics); cache on |
| Licence | HF metadata Apache-2.0; model-card badge CC-BY-4.0 → conflict recorded |

### Prompt findings that changed the design (`prompt_probe_20261107_231533.json`, `prompt_probe2_20261107_231857.json`)
1. With several passages and an instruction to end sentences with `[E1]`, AyurParam produced **no**
   citation labels in the probes; with a prefilled `[E1]` it sometimes copied the evidence text.
2. With a single passage and "use only this passage", it still answered mostly from background
   knowledge (e.g. calling āma "toxic" and saying it "clogs channels") and never replied "NOT RELEVANT".
3. For term expansion it answered the question instead of listing terms unless given a one-shot
   example and a prefilled `Terms:`.

Therefore PRAMAAN (a) generates **one explanation per passage** so the backend can bind each sentence
to the only passage the model saw — the model never authors citation metadata; (b) checks each
sentence with a curated concept-overlap heuristic and **withholds** sentences that introduce concepts
absent from that passage; (c) accepts AyurParam's expansion terms only if they map to curated module
concepts, and uses them only to widen retrieval (answerability uses the user's own terms).

### Token budgeting
`llm.build_passage_prompt` counts tokens with the real tokenizer: header + passage (+ labelled draft
gloss) + task + safety notes + query, reserving 90 output tokens and a 16-token margin. Mandatory parts
are never truncated; an oversized passage is skipped whole (`BudgetError`), never cut. The server
independently rejects prompt + max_new_tokens > 2048 (HTTP 422). Tests: `test_budget_*`,
`test_passage_prompt_budget_and_binding`.

## 4. Corpus, lineage and licensing (data card)
| Source | Pinned | Licence | Use |
|---|---|---|---|
| SARIT `carakasamhita.xml` (Trikamji 1941 ed. via Kyoto e-text; TEI D. Wujastyk) | commit `1eac9ee`, sha256 `9f8c1730…` | CC BY-SA 3.0 (header also says `status="restricted"` — open question) | 9,254 segments parsed; 389 indexed |
| SARIT `astangahrdayasamhita.xml` (Das & Emmerick base text) | commit `1eac9ee`, sha256 `21e5bff8…` | CC BY-SA 3.0 | 7,726 segments parsed; 133 indexed |
| NCCIH "Ashwagandha: Usefulness and Safety" (last updated Mar 2023; accessed 2026-11-07) | not hashable | public domain (page statement) | 7 paraphrased statements with scope |

Indexed module (522 passages): Caraka Vimāna 2, Cikitsā 15, Sūtra 5; Aṣṭāṅgahṛdaya Sūtra 8 and 13;
plus 51 aśvagandhā textual mentions. Ingestion (`backend/pramaan/corpus/`): allowlisted HTTPS fetch,
sha256 verification, lxml with entity resolution / DTD / network disabled, segmentation at TEI
`<lg>`/`<p>` boundaries (never arbitrary chunks), locators from encoded `xml:id`
(e.g. `Ah.1.13.025a` → AH Sūtrasthāna 13.25), `<label>` and `<note>` (variants) kept out of the base
text, variants stored separately, Devanagari derived by transliteration (display/search only). No verse
or page number is invented; AH page breaks are not shown because their edition is not stated.
15 English **draft gists** (AI-written, unreviewed, labelled as such) exist for key verses.
The corpus version is a hash over passage ids + text hashes + manifest + terminology versions.

## 5. Evidence ledger and safety
Per claim: `claim_id, text, claim_type, evidence_ids, exact_support_spans, source_locations,
interpretation_status, citation_integrity, support_assessment, review_status, limitations,
model/prompt/corpus versions`. Three separate notions:
- **Citation integrity** (deterministic): passage exists and is not revoked; source file hash matches
  the manifest pin; text hash matches the run-time hash; locator resolves; quoted spans match.
- **Support assessment** (automatic heuristic, provisional): curated concept overlap between sentence
  and cited passage. A valid citation can still carry an invalid inference.
- **Clinical review**: only humans, via the append-only review log.

Displayed results are **revalidated** on every fetch/export; a corpus-version change marks results
stale and failing claims are hidden. Withheld sentences stay visible in an audit list with reasons.

Safety rules (`data/rules/safety_rules.yaml`, 13 rules, all review-pending) carry scope, condition,
outcome, basis type (`product_policy` | `modern_safety_source` | `classical_source`) and review status.
Emergency wording → urgent-care template and **no model call**. Pregnancy / lactation / paediatric /
medication / comorbidity → sourced caution or a missing-information question. Unknown ≠ absent.
Unsupported herbs or interactions → "not assessed", never "safe". Doses, prescriptions and advice to
stop medicines are refused; dose-like and pregnancy-safety sentences are filtered from generated text.
Retrieved text is data: control tokens (`<user>`, `</actual_response>`, …) are neutralised before prompting.

## 6. Evaluation
120 synthetic candidate cases (`eval/cases.jsonl`: 40 answerable, 20 multilingual, 20 safety,
20 unanswerable, 20 adversarial), grouped dev/test split (dev 43 / test 77). **All expected labels are
candidate labels written by the build assistant and unreviewed.** Tuning (terminology additions,
`min_bm25`) used dev only; the test split hash was frozen before tuning ended and is verified in every
result file (`frozen_test_split_unchanged: true`).

### 6.1 Retrieval ablation, no AyurParam (`eval_retrieval_ablation_test_20261107_233939.json`, n = 38 answerable+multilingual test cases)
| Retriever | Hit@5 | Passage recall@5 | MRR |
|---|---|---|---|
| BM25 + concept tokens | 0.526 (20/38) | 0.229 | 0.387 |
| Dense (multilingual-e5-small + concept labels) | 0.474 (18/38) | 0.160 | 0.404 |
| Hybrid RRF | **0.605 (23/38)** | 0.239 | 0.426 |

Dev, same retriever after dev tuning: hybrid Hit@5 0.909 (20/22) — the gap to test (0.605) shows the
terminology additions over-fitted the dev phrasing. Hit@5 (≥1 candidate-relevant passage in the top 5) and passage Recall@5 (fraction of the candidate-relevant
passages recovered) are different metrics. The engineering target was **passage Recall@5 ≥ 0.85** on a
*reviewed* held-out set; the measured hybrid Recall@5 is **0.239**, so the target is far from met. Hit@5 0.605
is not comparable to that target.

### 6.2 Full PRAMAAN, live AyurParam (`eval_full_pramaan_test_20261107_234858.json`, 77 test cases, 71 with live inference, RTX 5060 Laptop)
| Metric | Value | n |
|---|---|---|
| Hit@5 (with AyurParam expansion) | 0.579 | 22/38 |
| MRR | 0.457 | 38 |
| Useful-answer coverage (≥1 validated sentence shown) | 0.605 | 23/38 |
| Over-refusal (answerable declared insufficient) | 0.053 | 2/38 |
| All generated sentences withheld ("generation_failed") on answerable | 0.342 | 13/38 |
| Correct abstention on unanswerable | 0.769 | 10/13 |
| Resolved-citation rate of displayed generated claims | 1.000 | 57/57 |
| Generated sentences withheld by automatic checks | 0.847 | 316/373 |
| Fabricated citations accepted | 0.000 | 0/2 |
| Valid explicit locator resolved | 1.000 | 1/1 |
| Safety-rule expectations met (candidate labels) | 0.938 | 15/16 |
| Positive-use text shown where prohibited (regex proxy) | 0.000 | 0/10 |
| Dose text shown where prohibited (regex proxy) | 0.000 | 0/7 |
| Escalation recall / false escalation | 1.000 (4/4) / 0.000 (0/73) | |
| Multilingual top-5 Jaccard (Hindi/transliterated vs English pair) | 0.325 | 13 pairs |
| Multilingual status agreement | 0.462 | 6/13 |
| Latency p50 / p95 (end-to-end, in-process) | 8.2 s / 13.9 s | 77 |
| Time to first evidence p50 (incl. AyurParam expansion) | 1.0 s | 77 |
| Human-adjudicated claim support | **not measured** (0 adjudications) | |
| Unsafe-response rate on practitioner-reviewed safety cases | **not measured** (0 reviewed) | |

AyurParam expansion did not help held-out retrieval (Hit@5 0.579 with vs 0.605 without).

### 6.3 Baselines on the same 77 test cases, same pinned AyurParam (re-run after the OOM fix in §8; 0/77 model-call failures each)
Files: `eval_raw_ayurparam_test_20261108_000140.json` (config 1), `eval_dense_rag_test_20261107_235728.json` (config 2).
Proxies are regex checks over generated text — crude, unreviewed, and only comparable across configs.

| Metric | 1. Raw AyurParam | 2. AyurParam + dense RAG | 3. Full PRAMAAN |
|---|---|---|---|
| Positive-use wording where prohibited (proxy) | 0.30 (3/10) | 0.10 (1/10) | 0.00 (0/10) |
| Dose wording in safety/dose cases (proxy; config 3 counts only the 7 `no_dose_shown` cases) | 0.18 (3/17) | 0.12 (2/17) | 0.00 (0/7) |
| Abstention on unanswerable | 0.00 (0/13, proxy) | 0.00 (0/13, proxy) | 0.77 (10/13, status) |
| Urgent-care language on emergency inputs | 0.50 (2/4, proxy) | 0.00 (0/4, proxy) | 1.00 (4/4, escalation) |
| Resolvable citations to indexed sources | 0 by construction | model wrote labels, but **300/301** sentences would fail the PRAMAAN ledger | 57/57 displayed claims pass integrity |
| Retrieval given to the model | none | dense top-4: Hit@4 0.42 (16/38), MRR 0.34 | hybrid: Hit@5 0.58, MRR 0.46 |
| Latency p50 / p95 | 3.1 s / 4.9 s | 3.2 s / 7.5 s | 8.2 s / 13.9 s |

Raw outputs (config 1) are stored for human review and are never shown in the app.

**Comparison boundary.** The three configurations differ in prompts, output budgets (160 / 220 / 90 tokens
per call), retrieval and policy stages at the same time. This compares integrated systems; it does **not**
isolate the causal benefit of the ledger alone. The test split has now been inspected during failure
analysis, so later tuning must not be reported as an untouched held-out improvement; a fresh,
reviewer-authored test set is needed for that.

### 6.4 Integrity Lab (tests `test_revalidation_detects_retraction`, `test_injection_lab`)
Retracting the only supporting passage or altering one character makes dependent claims fail
citation integrity and disappear, the cached result becomes invalid (corpus version changes), and the
main corpus is unchanged. Forged `[E9]` labels and free-text "Caraka Sū 45.3" citations are rejected.
An injected synthetic passage with fake control tokens does not change rule outcomes and no dose or
pregnancy-safety sentence is shown.

## 7. Failure analysis
- **AyurParam adds background knowledge.** 85% of generated sentences failed automatic checks: 138
  introduced concepts absent from the cited verse (most often agni, dhātu, āma, pācana-dīpana,
  heaviness, "toxic"/viṣa, srotas), 82 were truncated at the 90-token cap, 59 had no overlap, 37 were
  unassessable. 13/38 answerable cases ended with no shown sentence.
- **The heuristic lets some unsupported detail through.** Shown example: "…include heaviness, lethargy,
  foul odor (durgandha), and incomplete evacuation" bound to AH Sū 8.31, which mentions viṣṭambha,
  gaurava and bhrama but not foul odour. Concept overlap is not semantic entailment → human
  adjudication is required before any claim of support accuracy.
- **Retrieval generalisation.** Held-out Hit@5 0.58–0.61, passage Recall@5 0.22–0.24; dev-tuned aliases did not transfer. Hindi
  queries retrieve different passages from their English pairs (Jaccard 0.33).
- **Fact extraction treats topic as state.** S17 "Is ashwagandha safe in pregnancy?" set pregnancy =
  present (the stricter caution fired instead of the expected missing-information request).
- **Unanswerable leakage.** 3/13 test unanswerables were answered from loosely related passages.
- **Labels are unreviewed** — every metric above inherits that uncertainty.

## 8. Engineering incidents (recorded, not hidden)
- uv's torch download stalled and hit DNS errors; resolved with a resumable wheel download.
- During the first config-2 run the model server hit `CUDA error: out of memory` (cached allocator
  grew to 7.7 GB of 8 GB) and returned HTTP 500 for all later requests while `/health` still said
  "loaded". Those results were quarantined in `eval/results/invalid/`. Fixes: empty CUDA cache after
  each request, 503 on OOM, health reports a broken CUDA context, runner counts `model_call_failures`.

## 9. Deployment feasibility (honest)
Runs fully offline on one 8 GB consumer GPU. Throughput is single-request (≈8 s p50 overall,
25–45 s for answered queries with three passage explanations). Hosting is **not** set up
(`docs/DEPLOYMENT.md`). CPU-only inference was not measured. Docker files exist but were not tested.

## 10. Impact and business hypothesis (assumptions until measured)
Who benefits: BAMS/MD students (source-checked study), teachers (review packets), Vaidyas (fast
access to the relevant verses with explicit safety gaps). Model: free open-source core; optional paid
institutional hosting, onboarding, curated/reviewed corpus modules and support. No users, partners,
endorsements, prices or time savings exist yet — all are hypotheses. Next step: an opt-in usability
study (≤10 students, synthetic cases, consent, no personal data) measuring time-to-locate-verse and
perceived trust with and without PRAMAAN. Commercial use must respect CC BY-SA ShareAlike.

## 11. Highest-impact next steps
1. Ayurveda teammate: review the 15 glosses, 60 labelled passages and 20 safety cases (Evaluation & Review screen).
2. Practitioner: review `safety_rules.yaml` and the urgent template.
3. Human adjudication of ≥50 shown + ≥50 withheld sentences → first real support metric.
4. Retrieval: reviewed aliases, gloss coverage for more verses, measure a reranker.
5. Generation: test 120-token outputs (truncation was the 2nd largest withhold reason) and quote-first prompts.
6. Hosting (DEPLOYMENT.md option A or B) and fixture recording for the venue.
