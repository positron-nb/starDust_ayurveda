# PRAMAAN: Verse-Grounded Ayurveda Intelligence Powered by AyurParam

**AyushTech Innovate: National Open Ayurveda AI Challenge · Techfest, IIT Bombay 2026–27 · Phase 1 Proposal**

| Team | Team ID | Team Leader | Members |
| --- | --- | --- | --- |
| **StarDust** | **TM-FAD5308E454** | Abhishek Kumar Singh | Abhinav Rai, Naman Singh, Kirti Gaikwad (Clinical Lead · PhD Scholar, Ayurveda) |

**Live demo:** [stardustayurveda-kappa.vercel.app](https://stardustayurveda-kappa.vercel.app/) · **Code:** Apache-2.0, [github.com/positron-nb/starDust_ayurveda](https://github.com/positron-nb/starDust_ayurveda) · **Corpus:** third-party SARIT data under its original CC BY-SA 3.0 licence · Full AyurParam demo: served from our GPU through a secure tunnel (link on request).

## 1. PRAMAAN at a glance

PRAMAAN turns AyurParam into a study and practice companion that can be trusted: **every sentence it shows is tied to an original verse** from the Caraka (Charaka) Saṃhitā or the Aṣṭāṅga Hṛdaya, sentences the verse does not support are blocked before anyone sees them, and a model-independent safety layer handles emergencies, pregnancy, children, medicines and dosing. It is not a chatbot that "knows" Ayurveda; it is a workbench that **shows its evidence**. The name reflects *pramāṇa* (means of valid knowledge): like *āptopadeśa*, the authoritative classical word, every answer stands on the verse it shows.

<!-- FIGURE:cards -->

## 2. The problem

- AI answers about Ayurveda are fluent but unverifiable: a student cannot tell which sentence comes from Caraka or Vāgbhaṭa and which is the model's own background.
- We measured it. When AyurParam is given one verse to explain, **{{WITHHELD_PCT}} of its sentences ({{WITHHELD}}) contain content our support check cannot find in that verse.** Traceability therefore has to be enforced by the system, not assumed from the model.
- Students lose time locating the right verse in large texts; teachers cannot audit AI answers; Vaidyas need pregnancy, paediatric and medication checks before any advice.

## 3. Users and use cases

The primary users are **BAMS / MD students**; teachers, Vaidyas and wellness learners are secondary users.

| User | Typical question | What PRAMAAN gives |
| --- | --- | --- |
| **BAMS / MD students (primary)** | "What is Srotas?" · "त्रिदोष क्या है?" | The defining verse first, an explanation tied to it, the chapter around it |
| Teachers and examiners | "Is this AI answer correct?" | Evidence ledger and a printable review packet for every answer |
| Vaidyas (educational case review) | Synthetic case: "28-year-old, pregnant, wants Aśvagandhā" | Safety alerts, missing-information questions, classical evidence |
| Wellness learners | Dinacaryā, Ṛtucaryā, Nidrā, Vyāyāma | Classical regimen verses with clear educational disclaimers |

## 4. Solution architecture

<!-- FIGURE:arch -->

1. **Ask** in English or Hindi; optionally add a synthetic case (no real patient data).
2. **Safety gate:** rule-based extraction of pregnancy, lactation, age, medicines, comorbidity, dose and emergency facts as *present / absent / unknown*; 13 YAML rules run **before** the model. Emergencies go straight to an urgent-care message.
3. **Retrieve:** curated English / Hindi / Sanskrit terminology maps the question to Ayurveda concepts; hybrid search finds verse-level passages; the curated definition verse comes first for "what is" questions.
4. **Explain:** AyurParam explains **one retrieved verse at a time**, in English or Hindi.
5. **Verify:** the server attaches each citation; every sentence must pass citation-integrity and support checks; failures are withheld with a visible reason.
6. **Present:** verses (IAST + Devanagari) with [E1], [E2] tags linking each sentence to its verse; JSON and printable review export.

## 5. AyurParam at the core

- `bharatgenai/AyurParam` (2.9 B parameters, revision `27c69ee`) is the **only language model at runtime**, served by our own FastAPI model server in bf16 on an 8 GB laptop GPU (RTX 5060).
- **Two roles:** (a) Ayurveda term expansion, which turns user wording into curated Sanskrit concepts (accepted only if the concept exists in our terminology); (b) per-verse explanation in English or Hindi.
- **Engineering for trust:** remote model code is sha256-checked before `trust_remote_code`; the 2048-token window is enforced with the real tokenizer; the chat template was verified (it drops system messages, so instructions travel in a documented `<context>` block); every answer's trace records model id, revision, timings, and corpus and rule versions.

## 6. RAG over authenticated classical texts

- **Corpus:** SARIT TEI editions of the Caraka Saṃhitā and Aṣṭāṅga Hṛdaya, pinned and sha256-verified (third-party data under its original CC BY-SA 3.0 licence, attributed). 16,980 segments are parsed with their encoded verse locators; **{{INDEXED}} verse-level passages are indexed** in five curated modules: Agni–Āma–Ajīrṇa, Prakṛti, Svasthavṛtta, foundational concepts (Mūla-siddhānta) and classical herb mentions.
- **20 core topics (24 curated concepts):** Agni (Manda, Viṣama, Tīkṣṇa, Sama), Āma, Ajīrṇa, Grahaṇī, Prakṛti, Tridoṣa, Pañcamahābhūta, Saptadhātu, Āhāra, Āhāravidhividhāna, the eight Āhāravidhiviśeṣāyatanas, Āhāra-mala, Dhātumala, Srotas, Koṣṭha, Dinacaryā, Ṛtucaryā, Nidrā, Divāsvapna and Vyāyāma.
- **Hybrid retrieval:** BM25 over IAST plus curated concept tokens, and multilingual-e5 dense vectors in Qdrant, fused with reciprocal rank fusion; curated chapter-topic tags boost the chapters a topic actually lives in; an answerability gate refuses to answer without lexical evidence.
- **Definition-first pedagogy:** 1–3 curated definition verses per concept are shown first for "what is" questions, for example Tridoṣa → Aṣṭāṅga Hṛdaya Sū 1.6 (*vāyuḥ pittaṃ kaphaś ceti trayo doṣāḥ*), Srotas → Caraka Sū 30.12 (*sravaṇāt srotāṃsi*), Grahaṇī → Caraka Ci 15.56.
- **Honest scope:** a question outside the indexed topics gets "insufficient evidence" plus the list of covered topics, never an invented answer.
- **Reader tools:** relevance or textual order toggle; open any verse inside its chapter in the Source Explorer.

## 7. Grounding and hallucination control

- **Server-bound citations:** the model never writes citation metadata; the backend attaches the verse it was given.
- **Citation integrity:** the cited passage exists and is not revoked, the source file hash equals the pinned hash, the text hash is unchanged since answer time, the locator resolves, and quoted spans match. Invented references such as "Caraka Sūtrasthāna 45.12" are rejected.
- **Support check and withhold-and-explain:** every curated concept in a sentence must appear in its cited verse; dose wording and pregnancy-safety assertions are always withheld; withheld sentences are listed with the reason.
- **Source-only fallback:** if generation fails or every sentence is withheld, the user still receives the original verses.
- **Evidence ledger:** each claim stores evidence ids, spans, source locations and producing model, prompt and corpus versions; results are revalidated on every display and marked stale if the corpus changes.
- **Integrity Lab:** reviewers can retract or tamper with a verse, forge a citation or inject instructions on a sandbox copy, and watch dependent claims fail the production validator.

## 8. Safety and contraindication guardrails

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

Herb rules fire only when a herb is proposed, so ordinary study questions are never blocked. All 13 rules live in one YAML file, each labelled as product policy, modern safety source or classical source, so an Ayurveda expert can review and edit them without code. Facts are tri-state, and *unknown is never treated as absent*. Retrieved text is sanitised against prompt injection, and every answer carries a clear educational disclaimer.

## 9. Measured results

Measured on our 120-case evaluation suite (40 answerable, 20 multilingual, 20 safety, 20 unanswerable, 20 adversarial), live AyurParam on an RTX 5060 laptop GPU, {{EVAL_DATE}}.

| What we measured | Result |
| --- | --- |
| Displayed claims whose citation resolves to a real, unchanged verse | **{{CIT}}** |
| Fabricated citations accepted | **{{FAB}}** |
| Emergency cases escalated · false alarms on non-emergency cases | **{{ESC}} · {{FALSE}}** |
| Dose wording shown · positive-use wording shown under an active safety rule | **{{DOSE}} · {{POS}}** |
| Safety-rule expectations met (23 cases: 20 safety + 3 adversarial) | **{{SAFE}}** |
| Correct abstention on unanswerable questions | **{{ABST}}** |
| Retrieval Hit@5 (relevant verse in top 5; 60 answerable questions incl. 20 multilingual) | **{{HIT5}}** |
| Median time to first evidence · median full answer | **{{FIRST}} · {{P50}}** |
| Automated test suite | **{{TESTS}} tests passing** |

The single rule miss (a request to stop a medicine) has since been fixed and is covered by automated tests.

## 10. Ayurveda × engineering workflow

- **Clinical knowledge is data, not code:** topics, definition verses, terminology and safety rules live in three human-editable YAML files that our clinical lead can review and change directly.
- **A live feedback loop that already works:** our clinical lead tested the hosted app. Her report that "What is Prakriti?" returned off-target verses, her list of foundational topics, and her rule that "the definition must come first" became the Prakṛti, Svasthavṛtta and foundational modules and the definition-first ordering.
- **Review tooling:** claim-audit sheets, an Evaluation & Review screen and printable review packets make expert review fast and traceable.

## 11. Usability and multilingual access

- Questions in **English or Hindi**; explanations in English or Hindi; Sanskrit always shown as the original IAST with Devanagari.
- Concepts are recognised across scripts and spellings: "What is tridosha?" and "त्रिदोष क्या है?" both open with the same defining verse (covered by automated tests).
- Explanation on the left, verses on the right, an [E] tag on every sentence, and one-click examples for first-time users (Figure 2, last page).

## 12. Openness and deployment

- **Open source:** Apache-2.0 code on GitHub; the classical corpus is third-party SARIT data under its original CC BY-SA 3.0 licence, with attribution; reproducible corpus build from pinned sources; {{TESTS}} automated tests.
- **Runs on modest hardware:** the full stack runs offline on one 8 GB consumer GPU, which suits colleges and clinics without cloud budgets or with data-privacy needs.
- **Live demos:** the full AyurParam app is served from our GPU through a secure tunnel for demos, and an always-on public demo (verses and safety layer) runs on Vercel.
- **Ready to scale:** Docker Compose files and a Hugging Face ZeroGPU adapter with automatic local fallback are prepared for permanent hosting in Phase 2.

## 13. Impact and business model

- **Students** find the defining verse in seconds and always see text and interpretation separately.
- **Teachers** get auditable AI they can safely bring into the classroom, with review packets instead of black-box answers.
- **Vaidyas** see classical evidence together with safety checks before advising.

**Model: free core, paid trust.** The open-source core stays free for every student and Vaidya. Revenue pays for expert review, the costly part of trustworthy Ayurveda AI:

- **College edition (annual licence):** runs on-premise on one 8 GB GPU, with faculty dashboards and modules mapped to the NCISM BAMS syllabus. NCISM permitted 31 new Ayurveda colleges with 2,620 BAMS seats for 2025–26 alone ([NCISM LOP list, 19 Nov 2025](https://ncismindia.org/assets/pdf/List%20of%20Colleges%20Granted%20LOP%20to%20establish%20new%20Ayurveda%20Colleges%20for%20the%20A.Y.%202025-26%20as%20on%2019.11.2025.pdf)).
- **Clinic edition:** offline evidence and safety checks for Vaidyas; patient data stays on-premise, which eases obligations under India's DPDP Act, 2023.
- **Verified-content API** for Ayurveda ed-tech and publishers.
- **Faculty-reviewed modules:** experts are paid per verified module, and each module returns to the free core.

**Go-to-market:** validation through our clinical lead's academic network, a pilot with one BAMS batch, then colleges nationwide.

## 14. Roadmap

**Where we stand today:** the support check is lexical; Suśruta and the classical commentaries are not yet indexed; retrieval Hit@5 is {{HIT5_V}}. The milestones below close these gaps.

| By | Milestone |
| --- | --- |
| 1 Dec 2026 (Phase 2) | Suśruta Saṃhitā ingestion · Anupāna and Ṛtu (seasonal) contraindication rules · Marathi questions · clinical-lead sign-off on every definition verse and safety rule · expert validation: 50 answers rated independently by our clinical lead and an external Ayurveda expert, with agreement reported · retrieval tuned on a locked benchmark · permanent hosted link |
| 15–18 Dec 2026 (Finale) | Classical commentaries · semantic support check validated against clinical-lead labels · Saṃprāpti view linking nidāna → doṣa → dhātu → srotas · Dravya (herb) module · pilot with one BAMS batch |

<!-- FIGURE:screenshot -->
