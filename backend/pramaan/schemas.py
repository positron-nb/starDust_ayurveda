"""Typed records for the evidence ledger and API contract."""
from __future__ import annotations

from typing import Literal, Optional

from pydantic import BaseModel, Field

TriState = Literal["present", "absent", "unknown"]


class Source(BaseModel):
    source_id: str
    kind: str
    title: str
    work: str
    edition: str
    url: str
    pinned_revision: Optional[str] = None
    sha256: Optional[str] = None
    acquisition_date: str
    license: str
    reviewer_status: str
    known_limitations: list[str] = []


class Variant(BaseModel):
    locator: str
    text: str


class Passage(BaseModel):
    passage_id: str  # e.g. "Ca.3.2.7" / "Ah.1.13.25"
    source_id: str
    work: str
    sthana: str
    sthana_no: int
    chapter_no: int
    chapter_name: str
    verse_label: str  # human locator, e.g. "Vimānasthāna 2.7"
    xml_ids: list[str]
    segment_type: Literal["verse", "prose"]
    text_iast: str  # original base text, unchanged except whitespace collapsing
    text_deva: str  # derived transliteration (display/search only)
    text_hash: str  # sha256 of text_iast
    variants: list[Variant] = []
    modules: list[str] = []
    concepts: list[str] = []
    position: int  # order within the source
    review_status: str = "pending"
    gloss: Optional["Gloss"] = None


class Gloss(BaseModel):
    lang: Literal["en", "hi"]
    text: str
    author: str
    method: str
    review_status: str = "pending"


class CaseFact(BaseModel):
    key: str  # pregnancy, lactation, pediatric, medications, serious_comorbidity, emergency_signs, ...
    state: TriState
    values: list[str] = []
    origin: Literal["extracted", "user_confirmed", "user_edited", "default_unknown"] = "default_unknown"
    evidence_text: Optional[str] = None


class SupportSpan(BaseModel):
    passage_id: str
    start: int
    end: int
    text: str
    concept: str


class CitationIntegrity(BaseModel):
    status: Literal["pass", "fail"]
    checks: dict[str, bool]
    detail: list[str] = []


class Claim(BaseModel):
    claim_id: str
    text: str
    claim_type: Literal["source_explanation", "interpretation", "safety_statement", "boundary_statement"]
    evidence_ids: list[str]
    evidence_labels: list[str] = []
    exact_support_spans: list[SupportSpan] = []
    source_locations: list[str] = []
    interpretation_status: Literal["draft_generated", "deterministic_template", "human_reviewed"] = "draft_generated"
    citation_integrity: CitationIntegrity
    support_assessment: Literal[
        "concept_overlap_auto", "partial_overlap_auto", "no_overlap_auto", "not_assessable_auto", "source_statement"
    ]
    support_detail: str = ""
    review_status: Literal["pending", "accepted", "rejected", "needs_revision"] = "pending"
    limitations: list[str] = []
    shown_in_answer: bool = True
    withheld_reason: Optional[str] = None
    run_id: str = ""
    model_id: Optional[str] = None
    model_revision: Optional[str] = None
    prompt_version: Optional[str] = None
    corpus_version: Optional[str] = None


class SafetyAlert(BaseModel):
    rule_id: str
    title: str
    action: str
    severity: str
    message: str
    question: Optional[str] = None
    basis_type: str
    basis_text: Optional[str] = None
    source_id: Optional[str] = None
    statement_id: Optional[str] = None
    statement_paraphrase: Optional[str] = None
    statement_scope: Optional[str] = None
    source_url: Optional[str] = None
    review_status: str = "pending"


class EvidenceCard(BaseModel):
    label: str  # E1, E2...
    passage: Passage
    retrieval: dict
    role: Literal["primary", "context_limiting_candidate", "adjacent_context"] = "primary"
    role_note: Optional[str] = None
    matched_concepts: list[str] = []


class StageTrace(BaseModel):
    name: str
    ran: bool
    mode: str  # live | fixture_replay | skipped | unavailable | error
    ms: float = 0.0
    detail: dict = {}


class RunTrace(BaseModel):
    run_id: str
    created_at: str
    cache_key: str
    llm_mode: str
    model_id: str
    model_revision: str
    inference_ran: bool
    prompt_version: str
    corpus_version: str
    rules_version: str
    terms_version: str
    embed_model: str
    stages: list[StageTrace] = []
    timings_ms: dict[str, float] = {}
    hardware: Optional[str] = None


class RunResult(BaseModel):
    run_id: str
    status: Literal["answered", "insufficient_evidence", "escalated", "generation_failed", "retrieval_only"]
    query: str
    lang: Literal["en", "hi"]
    normalized_query: dict
    facts: list[CaseFact]
    safety_alerts: list[SafetyAlert]
    missing_information: list[str]
    evidence: list[EvidenceCard]
    claims: list[Claim]
    rejected_claims: list[Claim]
    answer_notice: str
    escalation_message: Optional[str] = None
    unresolved_questions: list[str] = []
    trace: RunTrace
    revalidated_at: Optional[str] = None
    stale: bool = False
    stale_reasons: list[str] = []


class QueryRequest(BaseModel):
    query: str = Field(..., min_length=1)
    lang: Literal["en", "hi"] = "en"
    case_text: str = ""
    facts: Optional[list[CaseFact]] = None  # user-confirmed facts override extraction
    source_filter: Optional[list[str]] = None
    use_model: bool = True
    retrieval_mode: Literal["hybrid", "dense", "bm25"] = "hybrid"
    session_id: Optional[str] = None


class ReviewAction(BaseModel):
    target_type: Literal["claim", "passage", "rule", "gloss", "eval_case"]
    target_id: str
    run_id: Optional[str] = None
    decision: Literal["accepted", "rejected", "needs_revision", "comment"]
    note: str = ""
    reviewer_name: str = Field(..., min_length=1, max_length=80)
    reviewer_role: Literal["student_bams", "student_md_phd", "practitioner", "engineer", "other"]


Passage.model_rebuild()
