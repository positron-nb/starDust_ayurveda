# Repository audit — PRAMAAN

Audit date: 2026-11-09. Commit audited: `ce3176d` on `pramaan-prototype` (clean working tree).
Method: source inspection, not documentation. Status legend:
**Implemented+tested** (code exists and an automated test or logged run exercises it) ·
**Implemented, manually checked** · **Partial** · **Untested** · **Not implemented**.

## 1. Actual architecture
```
frontend/ (React 18 + TS + Vite + Tailwind, ~1.1k LOC)  → built to frontend/dist, served by the API
backend/pramaan/ (FastAPI, ~2.9k LOC)
  api.py        HTTP routes, rate limit, security headers, public_demo read-only switch, SPA serving
  pipeline.py   Engine.run(): the whole request path (see §5)
  terms.py      curated terminology (YAML), alias matching, IAST/Devanagari transliteration, BM25 tokeniser
  retrieval.py  BM25Okapi (+concept tokens) ∥ e5-small dense (Qdrant) → RRF; answerability gate
  llm.py        prompt builders, real-tokenizer budget, HTTP / fixture / off adapters
  ledger.py     claim construction, citation integrity, support heuristic, policy filters, revalidation
  safety.py     tri-state fact extraction, YAML rule engine, escalation
  lab.py        Integrity Lab experiments on disposable SQLite snapshots
  appdb.py      runs cache + append-only review log (SQLite)
  export.py     JSON / HTML review packets
  corpus/       secure TEI parsing, build, SQLite corpus store
  eval/run.py   retrieval ablation + 3 model configurations
model_server/server.py   separate AyurParam process (FastAPI, :8601, localhost)
data/                    manifest, pinned raw TEI, curated modules, draft glosses, terminology, rules
eval/                    cases, frozen-test hash, results, fixtures, audit sheets
```

## 2. Features by status
| Feature | Status | Evidence |
|---|---|---|
| TEI ingestion with checksum verification, xml:id locators, variants separated | Implemented+tested | `test_real_passage_ama_definition`, `test_variants_kept_separate`, `test_source_checksums_pinned`, `test_secure_parser_blocks_entities` |
| Hybrid retrieval (BM25 + dense + RRF) | Implemented+tested | eval runs; dense not covered by unit tests (disabled in CI) |
| AyurParam expansion + per-passage explanation (live) | Implemented, logged | `eval_full_pramaan_test_*`, smoke test |
| Token budget ≤ 2048 with real tokenizer | Implemented+tested | `test_budget_*`, `test_passage_prompt_budget_and_binding` |
| Citation integrity, forged-label rejection, revalidation | Implemented+tested | `test_forged_labels_rejected`, `test_revalidation_detects_retraction` |
| Support heuristic + withholding | Implemented+tested (heuristic only) | `test_passage_prompt_budget_and_binding`; semantic accuracy **not measured** |
| Tri-state facts incl. question-vs-assertion | Implemented+tested | `test_tristate_facts`, 8× `test_pregnancy_question_vs_fact` |
| Safety rules, escalation, not-assessed interactions | Implemented+tested | `test_pregnancy_counterfactual`, `test_emergency_escalation_stops_content`, `test_unsupported_herb_interaction_not_assessed` |
| Fabricated locator refusal | Implemented+tested | `test_fabricated_locator_refused` |
| Integrity Lab (retract / alter / swap / forge / inject) | Implemented+tested | `test_revalidation_detects_retraction`, `test_injection_lab`; browser-checked |
| Source-only fallback | Implemented, manually checked (browser) | no automated UI test |
| Public-demo read-only mode, limits, headers | Implemented+tested | `test_public_demo_blocks_writes_and_limits_inputs` |
| Authentication for public exposure | **Not implemented** before this round | added in this round, see DEMO_HOSTING.md |
| Fixture replay (labelled) | Implemented, manually checked | — |
| Claim-audit export/import | Partial | no duplicate protection, no "unresolved" label, no tests (fixed this round) |
| Docker / Compose | **Untested** | Docker not installed on build machine |
| Hosting | **Not implemented** | — |
| Human/clinical review | **Not started** | review log empty |

## 3. Dependency versions (from `.venv`, lockfile `backend/requirements.lock.txt`)
Python 3.12.10 · torch 2.7.1+cu128 · transformers 4.53.1 · tokenizers 0.21.2 · sentence-transformers 4.1.0 ·
qdrant-client 1.14.2 (embedded mode) · rank-bm25 0.2.2 · FastAPI 0.115.12 · lxml 5.4.0 ·
indic-transliteration 2.3.69. Frontend: React 18.3.1, Vite 5.4.11, Tailwind 3.4.17, TS 5.6.3.

## 4. Model loading and inference flow
`model_server/server.py`: background thread loads from `models/AyurParam` (checks sha256 of the two
remote-code files first), `trust_remote_code=True`, bf16 on CUDA (fp16 on pre-Ampere, fp32 on CPU),
`.to(device)`. `/generate`: tokenises without special tokens, rejects prompt+max_new_tokens > 2048
(422), greedy decoding, repetition_penalty 1.15, stops on both EOS ids, `empty_cache()` after each
call, 503 + unhealthy flag on CUDA errors. One request at a time (lock).
Backend `llm.HTTPAdapter` calls it with a timeout; failures become `retrieval_only`, never silent.

## 5. Request path (`Engine.run`)
normalise → `extract_facts(query, case_text)` + user overrides → escalation check (stop) →
`evaluate_rules` → explicit-locator check (unresolved → refuse) → AyurParam expansion (only curated
module concepts accepted) → hybrid retrieval (limit 6) → answerability (domain concepts, min_bm25 6.0)
→ evidence cards (+adjacent half-verse, +herb mentions, +1 context-limiting candidate) → herb queries
with active rules stop here (no generation) → per-passage generation for top 3 primary cards →
`build_claims` (bound citation, integrity, heuristic, dose/pregnancy/positive-use filters, truncation)
→ status `answered | generation_failed | retrieval_only | insufficient_evidence | escalated`.
Results are cached by a key that includes model revision, prompt, corpus, rules and terms versions,
and are revalidated on every read/export.

## 6. Retrieval pipeline (as coded)
Passage tokens: ASCII-folded words + 5-char prefixes of words > 6 chars + concept tokens `c:<id>` ×2.
Query: raw + IAST transliteration + Sanskrit aliases of matched concepts; same tokeniser.
BM25Okapi default (k1 1.5, b 0.75). Dense: `passage: <IAST> | concepts: <English labels>` and
`query: <raw + concept labels>`. Pool = max(4×limit, 30) per retriever, RRF k = 60, dedupe by text hash.

## 7. Evidence validation
Per sentence: citation built only from the passage shown to the model; checks = passage exists and
not revoked, source file hash = manifest pin, text hash = run hash, locator resolves, spans match.
Support heuristic = curated-concept overlap (meta/intent concepts and `ahara` excluded). Shown only if
integrity passes and all concepts overlap; dose / pregnancy-safety / positive-use (when rules active)
always withheld. Known gap: relations, negation and qualifiers are not assessed.

## 8. Safety enforcement
Independent of model output: rules evaluated before generation; emergency stops before any model call;
herb queries with active rules never call the explanation stage; generated text is filtered afterwards.
Retrieved text is sanitised of control tokens before prompting.

## 9. Evaluation methodology (as coded)
`eval/run.py`. Hit@5 = case has ≥1 candidate-relevant passage among the first 5 *primary* evidence
cards; passage Recall@5 = |relevant ∩ top5| / |relevant| averaged over cases; MRR over the full list.
Labels are AI-written candidates. The 77-case test split has been inspected → now **development data**.

## 10. Technical debt
- `build_explain_prompt` (multi-passage) is only used by eval config 2 and tests.
- Corpus rebuild requires stopping the API on Windows (file lock).
- `eval_retrieval_ablation_dev_*` files from superseded corpus versions remain (flagged in UI).
- Support heuristic is lexical; no negation/relation handling.
- No automated frontend tests.
- Concept patterns are hand-written regexes; some over-match (documented in terminology notes).

## 11. Unresolved risks
Weak retrieval (passage Recall@5 0.24); zero human review; licence questions (CC BY-SA corpus vs
permissive-licence rule; AyurParam metadata conflict); single-GPU, single-request model server;
hosting absent; Docker untested; Hindi parity unproven (6/13 status agreement).

## 12. Priorities (matches EXECUTION_ROADMAP.md)
P1 human claim audit → P2 retrieval → P3 Phase 1 proposal (22 Nov) → P4 PyTorch 2.8 / ZeroGPU →
P5 hosting fallback + Docker → P6 usability study → P7 finale.
