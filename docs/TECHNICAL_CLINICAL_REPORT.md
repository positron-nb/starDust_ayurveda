# PRAMAAN: Technical-Clinical Report

**AyushTech Innovate: National Open Ayurveda AI Challenge · Techfest, IIT Bombay 2026–27 · Phase 2**

| Team | Team ID | Team Leader | Members |
| --- | --- | --- | --- |
| **StarDust** | **TM-FAD5308E454** | Abhishek Kumar Singh | Abhinav Rai, Naman Singh, Kirti Gaikwad (Clinical Lead · PhD Scholar, Ayurveda) |

**Live app:** [stardustayurveda-kappa.vercel.app](https://stardustayurveda-kappa.vercel.app/) (always on; shows a "Live AyurParam demo" button whenever the GPU demo is running) · **Code:** Apache-2.0, [github.com/positron-nb/starDust_ayurveda](https://github.com/positron-nb/starDust_ayurveda) · **Corpus:** third-party SARIT data under its original CC BY-SA 3.0 licence.

## 1. Summary

PRAMAAN answers Ayurveda questions **only from original verses** of the Caraka (Charaka) Saṃhitā and the Aṣṭāṅga Hṛdaya. AyurParam explains one retrieved verse at a time; the server attaches every citation; sentences the verse does not support are withheld before the user sees them; and a model-independent safety layer handles emergencies, pregnancy, children, medicines and dosing. This report covers the three things Phase 2 asks for: **retrieval accuracy (§3), classical text citations (§4) and safety boundaries (§5)**, followed by the comparison against plain AyurParam and plain RAG (§6) and the clinical validation underway (§7).

<!-- FIGURE:cards -->

## 2. System overview

<!-- FIGURE:arch -->

The pipeline runs as a FastAPI backend with a separate AyurParam model server, so the app keeps working (verses, citations, safety) even when the model is unavailable. Every answer carries a trace with the model id and revision, timings, and the corpus, rule and terminology versions it used. The figure shows the order of the stages; §3–§5 describe each one with its measurements.

## 3. Retrieval accuracy

**Method.** Questions in English or Hindi are mapped to curated Ayurveda concepts (English / Hindi / Sanskrit aliases and Sanskrit text patterns). Hybrid search fuses BM25 over IAST plus concept tokens with multilingual-e5 dense vectors (Qdrant) by reciprocal rank fusion. Chapter-level topic tags, curated from the texts, boost the chapters where a topic is actually taught, and for "what is X" questions the curated definition verse of that concept is shown first. An answerability gate declines questions without lexical evidence and lists the covered topics instead.

**Coverage.** **{{INDEXED}} verse-level passages** in five curated modules: Agni–Āma–Ajīrṇa, Prakṛti, Svasthavṛtta, foundational concepts (Mūla-siddhānta) and classical herb mentions. Together they cover 20 core topics and 24 curated concepts.

**Measured on the 60 answerable questions** of our 120-case suite (40 answerable + 20 multilingual; relevance labels written by the team, now under clinical-lead review):

| Retriever (no AyurParam) | Hit@5 | Passage Recall@5 | MRR |
| --- | --- | --- | --- |
| BM25 + concept tokens | {{ret.bm25_hit_at_5|v2}} ({{ret.bm25_hit_at_5|frac}}) | {{ret.bm25_passage_recall_at_5|v2}} | {{ret.bm25_mrr|v2}} |
| Dense (multilingual-e5-small) | {{ret.dense_hit_at_5|v2}} ({{ret.dense_hit_at_5|frac}}) | {{ret.dense_passage_recall_at_5|v2}} | {{ret.dense_mrr|v2}} |
| **Hybrid (PRAMAAN)** | **{{ret.hybrid_hit_at_5|v2}} ({{ret.hybrid_hit_at_5|frac}})** | **{{ret.hybrid_passage_recall_at_5|v2}}** | **{{ret.hybrid_mrr|v2}}** |

Retrieval-only run of {{ret.@date}}. In the full pipeline with live AyurParam ({{full.@date}}), Hit@5 is **{{full.hit_at_5|v2}} ({{full.hit_at_5|frac}})**, MRR **{{full.mrr|v2}}**, and the first evidence appears in a median of **{{full.time_to_first_evidence_p50_ms|s}}**. Hybrid fusion beats either retriever alone on every metric.

**Definition-first ordering** is covered by automated tests: for "What is Tridoṣa?", "What is Srotas?", "Āma?", "Grahaṇī?", the Hindi "त्रिदोष क्या है?" and five other questions, the defining verse (for example Aṣṭāṅga Hṛdaya Sū 1.6, Caraka Sū 30.12, Caraka Ci 15.56) is always shown first, while questions about causes, signs or treatment keep relevance order.

**Abstention.** On 20 questions outside the corpus, PRAMAAN correctly declines **{{full.correct_abstention|frac}}**; it never invents an answer, and lists the covered topics instead.

## 4. Classical text citations

**Lineage.** The SARIT TEI editions of the Caraka Saṃhitā (Trikamji 1941 e-text) and the Aṣṭāṅga Hṛdaya (Das & Emmerick base text) are pinned to a commit and verified by sha256 at every build. 16,980 segments are parsed at verse and prose boundaries, never as arbitrary chunks; each keeps its encoded locator (for example `Ah.1.13.025a` → Aṣṭāṅga Hṛdaya Sūtrasthāna 13.25). Variant readings are stored separately, and Devanagari is derived from the IAST for display only.

**How a citation is made.** The model never writes citation metadata. AyurParam sees one verse; the server binds every sentence it produces to that verse's id and shows both together ([E1], [E2] tags on screen).

**How a citation is checked.** Before display, and again on every reload or export:

1. The cited passage exists and is not revoked.
2. The source file hash equals the pinned hash.
3. The passage text hash is unchanged since answer time.
4. The locator resolves.
5. Every quoted span matches the text.

If the corpus changes, dependent answers are marked stale. References typed by the user or the model, such as "Caraka Sūtrasthāna 45.12", are checked against the edition and rejected when they do not exist.

| Citation measurement ({{full.@date}}, live AyurParam) | Result |
| --- | --- |
| Displayed sentences whose citation resolves to a real, unchanged verse | **{{full.resolved_citation_rate_displayed|frac}} ({{full.resolved_citation_rate_displayed|pct}})** |
| Fabricated references accepted | **{{full.fabricated_citation_accepted|frac}}** |
| Valid explicit locators resolved to the right verse | **{{full.valid_locator_resolved|frac}}** |
| AyurParam sentences withheld because the cited verse did not support them | {{full.generated_sentences_withheld_rate|frac}} ({{full.generated_sentences_withheld_rate|pct}}) |

The last row is the reason PRAMAAN exists. Given a single verse, AyurParam often adds background knowledge the verse does not contain; PRAMAAN keeps those sentences out of the answer and lists them, with the reason, in an audit panel. When every sentence is withheld, the user still receives the original verses (source-only fallback).

**Integrity Lab.** Reviewers can retract or alter a verse, forge a citation, or inject instructions into a passage on a disposable copy of the corpus. Dependent claims then fail the production validator, while the main corpus stays untouched; automated tests cover each experiment.

## 5. Safety boundaries

**What PRAMAAN will not do:** diagnose, prescribe, give doses, clear a herb as "safe", or advise stopping a medicine. Every answer carries an educational disclaimer.

**How safety is enforced.** Thirteen rules live in one YAML file that the clinical lead can edit; each is labelled as product policy, modern safety source (NCCIH) or classical source. They run **before and outside the model**. Case facts are tri-state (present / absent / unknown), and *unknown is never treated as absent*.

| Situation | PRAMAAN's behaviour |
| --- | --- |
| Emergency wording (chest pain, difficulty breathing, fainting, …) | Urgent-care message; the model is never called |
| Pregnancy or lactation present **or unknown** + herb | Sourced caution, or a missing-information question |
| Child + herb | No herb-use interpretation; paediatric review required |
| Age unknown + herb | Asks the age first; herb-use interpretation waits for the answer |
| Current medicines; thyroid, autoimmune or liver disease; planned surgery | Interaction caution |
| Dose or prescription request | Refused |
| Request to stop or replace a medicine | Refused; consult the treating physician |
| Herb without a curated modern safety source | "Not assessed", never "safe" |
| Classical restriction (*niṣedha*) near the queried concept | Surfaced as context-limiting evidence for review |

Herb rules fire only when a herb is proposed, so ordinary study questions are never blocked. Retrieved text is treated as data: control tokens are neutralised before prompting, so a passage cannot instruct the model.

| Safety measurement ({{full.@date}}, live AyurParam) | Result |
| --- | --- |
| Emergency cases escalated | **{{full.escalation_recall|frac}}** |
| False alarms on non-emergency cases | **{{full.false_escalation|frac}}** |
| Safety-rule expectations met (20 safety + 3 adversarial cases) | **{{full.safety_rule_expectation_met|frac}}** |
| Dose wording shown where prohibited | **{{full.dose_shown_auto_proxy|frac}}** |
| Positive-use wording shown under an active safety rule | **{{full.positive_use_shown_auto_proxy|frac}}** |

## 6. Why the architecture matters: AyurParam alone vs plain RAG vs PRAMAAN

The same pinned AyurParam was run three ways on the same 77 test questions (runs of {{raw.@date}} and {{fulltest.@date}}). The configurations differ in more than one stage, so this compares whole systems, not the ledger alone.

| Measurement | AyurParam alone | AyurParam + plain RAG | **PRAMAAN** |
| --- | --- | --- | --- |
| Positive-use wording where prohibited | {{raw.positive_use_text_auto_proxy|frac}} | {{rag.positive_use_text_auto_proxy|frac}} | **{{fulltest.positive_use_shown_auto_proxy|frac}}** |
| Abstains on unanswerable questions | {{raw.abstention_on_unanswerable_auto_proxy|frac}} | {{rag.abstention_on_unanswerable_auto_proxy|frac}} | **{{fulltest.correct_abstention|frac}}** |
| Emergency inputs routed to urgent care | {{raw.urgent_language_on_emergency_auto_proxy|frac}} | {{rag.urgent_language_on_emergency_auto_proxy|frac}} | **{{fulltest.escalation_recall|frac}}** |
| Sentences with a resolvable citation | none (no sources) | {{rag.sentences_failing_ledger_if_validated|n}} of {{rag.sentences_failing_ledger_if_validated|d}} sentences would fail our citation and support checks | **{{fulltest.resolved_citation_rate_displayed|frac}} pass** |
| Median latency | {{raw.latency_p50_ms|s}} | {{rag.latency_p50_ms|s}} | {{fulltest.latency_p50_ms|s}} |

PRAMAAN is slower because it explains each verse separately and checks every sentence. In exchange it never shows prohibited wording, always routes emergencies, declines what the texts do not cover, and every sentence it shows cites a real verse.

## 7. Clinical validation

- **Expert rating of 50 answers.** We generated 50 live answers covering all 20 topics (40 English, 10 Hindi; questions and outputs in `eval/expert_validation/`). Our clinical lead and an external Ayurveda expert rate each answer independently on four questions: relevance of the verses, faithfulness of each sentence to its cited verse, clinical correctness, and overall quality. We report each rater's scores and their agreement (percent agreement and Cohen's κ). Ratings are due on 30 Nov 2026 and will be added to this section.
- **Curated knowledge review.** The clinical lead is reviewing the 24 definition-verse choices, the 13 safety rules, and new Anupāna and Ṛtu (seasonal) restrictions, using the same workbook.
- **Feedback already built in.** Her testing of the hosted app produced the Prakṛti, Svasthavṛtta and foundational modules, the definition-first ordering, and the corrected age-rule behaviour.

## 8. AyurParam integration

- `bharatgenai/AyurParam` (2.9 B parameters, revision `27c69ee`) is the only language model at runtime. It runs in bf16 on an 8 GB laptop GPU (RTX 5060), loads in about 30 s, and generates about 13–14 tokens/s.
- **Roles:** Ayurveda term expansion, where only terms that map to curated concepts are accepted, and per-verse explanation in English or Hindi.
- **Verified behaviour that shaped the design:** the chat template silently drops system messages, so instructions travel in the documented `<context>` block. Asked to cite several passages at once, AyurParam produced no citation labels, which is why each verse is explained separately and the server binds the citation. The 2048-token window is enforced with the real tokenizer, and an oversized passage is skipped whole, never cut.
- **Safe loading:** the remote model code is sha256-checked against the reviewed version before `trust_remote_code`.

## 9. Deployment and reproducibility

- **Live:** the always-on app on Vercel shows verses, citations, the safety layer and the Integrity Lab. When the team GPU runs the full demo (one command: `scripts/start_live_demo.ps1`), the app shows a "Live AyurParam demo" button linking to it; the button appears only after the server confirms the demo is up.
- **Reproducible:** the corpus is built from pinned sources with checksum verification; {{TESTS}} automated tests pass; every number in this report is read from result files in `eval/results/` by `scripts/build_proposal.py`.
- **Portable:** Docker Compose files and a CPU Hugging Face Space recipe (`deploy/hf_cpu_space/`) are included; the full stack runs offline on one 8 GB consumer GPU.

## 10. Roadmap

**Where we stand today:** the support check is lexical, so it can miss a negation or a relation; the Suśruta Saṃhitā and the classical commentaries are not yet indexed; and retrieval Hit@5 is {{full.hit_at_5|v2}}. The milestones below close these gaps.

| By | Milestone |
| --- | --- |
| 15–18 Dec 2026 (Finale) | Expert-rating results and agreement · Anupāna and Ṛtu rules from the clinical lead · retrieval tuned on her locked benchmark · Suśruta Saṃhitā ingestion · Marathi questions |
| After the Finale | Classical commentaries · semantic support check validated against expert labels · Saṃprāpti view (nidāna → doṣa → dhātu → srotas) · pilot with one BAMS batch |

<!-- FIGURE:screenshot -->
