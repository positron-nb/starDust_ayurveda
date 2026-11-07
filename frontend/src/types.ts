export type TriState = "present" | "absent" | "unknown";

export interface CaseFact { key: string; state: TriState; values: string[]; origin: string; evidence_text?: string | null }
export interface Variant { locator: string; text: string }
export interface Gloss { lang: string; text: string; author: string; method: string; review_status: string }
export interface Passage {
  passage_id: string; source_id: string; work: string; sthana: string; sthana_no: number; chapter_no: number;
  chapter_name: string; verse_label: string; xml_ids: string[]; segment_type: string; text_iast: string; text_deva: string;
  text_hash: string; variants: Variant[]; modules: string[]; concepts: string[]; position: number; review_status: string;
  gloss?: Gloss | null;
}
export interface SupportSpan { passage_id: string; start: number; end: number; text: string; concept: string }
export interface CitationIntegrity { status: "pass" | "fail"; checks: Record<string, boolean>; detail: string[] }
export interface Claim {
  claim_id: string; text: string; claim_type: string; evidence_ids: string[]; evidence_labels: string[];
  exact_support_spans: SupportSpan[]; source_locations: string[]; interpretation_status: string;
  citation_integrity: CitationIntegrity; support_assessment: string; support_detail: string; review_status: string;
  limitations: string[]; shown_in_answer: boolean; withheld_reason?: string | null; run_id: string;
  model_id?: string; model_revision?: string; prompt_version?: string; corpus_version?: string;
}
export interface SafetyAlert {
  rule_id: string; title: string; action: string; severity: string; message: string; question?: string | null;
  basis_type: string; basis_text?: string | null; source_id?: string | null; statement_id?: string | null;
  statement_paraphrase?: string | null; statement_scope?: string | null; source_url?: string | null; review_status: string;
}
export interface EvidenceCard { label: string; passage: Passage; retrieval: Record<string, any>; role: string; role_note?: string | null; matched_concepts: string[] }
export interface StageTrace { name: string; ran: boolean; mode: string; ms: number; detail: Record<string, any> }
export interface RunTrace {
  run_id: string; created_at: string; cache_key: string; llm_mode: string; model_id: string; model_revision: string;
  inference_ran: boolean; prompt_version: string; corpus_version: string; rules_version: string; terms_version: string;
  embed_model: string; stages: StageTrace[]; timings_ms: Record<string, number>; hardware?: string | null;
}
export interface RunResult {
  run_id: string; status: string; query: string; lang: "en" | "hi"; normalized_query: Record<string, any>;
  facts: CaseFact[]; safety_alerts: SafetyAlert[]; missing_information: string[]; evidence: EvidenceCard[];
  claims: Claim[]; rejected_claims: Claim[]; answer_notice: string; escalation_message?: string | null;
  unresolved_questions: string[]; trace: RunTrace; revalidated_at?: string | null; stale: boolean; stale_reasons: string[];
  cached?: boolean;
}
export interface Health {
  api: string; version: string; deploy_mode: string; llm: Record<string, any>; llm_mode_configured: string;
  model: { id: string; revision: string; context_limit: number }; prompt_version: string; corpus_version: string;
  rules_version: string; terms_version: string; indexed_passages: number; dense: { enabled: boolean; model: string; error?: string | null };
}
