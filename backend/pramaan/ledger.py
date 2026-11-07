"""Evidence ledger: claim construction and validation.

Three things are kept separate:
  * citation integrity  - deterministic: source exists, file/text hash matches, locator resolves,
                          quoted span matches the stored text.
  * support assessment  - automatic HEURISTIC (curated concept overlap). Fallible, provisional.
  * clinical review     - only a real human, recorded in the review log.
A valid citation can still carry an invalid inference.
"""
from __future__ import annotations

import re

from .corpus.store import CorpusStore, sha256_text
from .schemas import CitationIntegrity, Claim, EvidenceCard, SupportSpan
from .terms import Terminology

LABEL_RE = re.compile(r"\[\s*(E\d{1,2})\s*\]")
ANY_BRACKET_RE = re.compile(r"\[([^\]]{1,40})\]")
# claims that look like prescriptions/doses are never shown
DOSE_RE = re.compile(r"\b\d+(?:\.\d+)?\s*(?:mg|g|gm|grams?|ml|tablets?|capsules?|times a day|times daily)\b|खुराक|ग्राम|मिलीग्राम", re.I)
POSITIVE_USE_RE = re.compile(
    r"\b(?:safe to (?:use|take)|can (?:safely )?(?:take|use)|should take|recommended (?:for|during)|is safe|beneficial (?:in|during) pregnancy|take ashwagandha)\b"
    r"|सुरक्षित है|ले सकती|लेना चाहिए", re.I)


ALWAYS_BLOCK_RE = re.compile(
    r"safe (?:to (?:use|take) )?(?:in|during|for) (?:pregnancy|pregnant|breast-?feeding|lactation)|(?:pregnancy|pregnant women)[^.]{0,40}safe"
    r"|गर्भावस्था में सुरक्षित|स्तनपान में सुरक्षित", re.I)


def check_citation(store: CorpusStore, passage_id: str, expected_hash: str | None,
                   spans: list[SupportSpan] | None = None) -> CitationIntegrity:
    checks: dict[str, bool] = {}
    detail: list[str] = []
    p = store.get(passage_id)
    checks["passage_exists"] = p is not None
    if p is None:
        detail.append(f"{passage_id}: not present (or revoked) in corpus snapshot")
        return CitationIntegrity(status="fail", checks=checks, detail=detail)
    src = store.source_raw(p.source_id)
    checks["source_exists"] = src is not None
    if src is None:
        detail.append(f"source {p.source_id} missing")
    else:
        checks["source_file_hash_pinned"] = (src.get("_file_sha256_at_build") == src.get("sha256"))
        if not checks["source_file_hash_pinned"]:
            detail.append("source file hash differs from manifest pin")
    actual_hash = sha256_text(p.text_iast)
    checks["text_hash_matches_store"] = actual_hash == store.stored_hash(passage_id)
    if expected_hash is not None:
        checks["text_hash_matches_run"] = actual_hash == expected_hash
        if not checks["text_hash_matches_run"]:
            detail.append(f"{passage_id}: text changed since the run (hash mismatch)")
    checks["locator_resolves"] = bool(p.xml_ids) and p.passage_id.split(".")[0] in ("Ca", "Ah")
    if spans:
        ok = all(p.text_iast[s.start:s.end] == s.text for s in spans if s.passage_id == passage_id)
        checks["quoted_spans_match"] = ok
        if not ok:
            detail.append(f"{passage_id}: quoted span no longer matches text")
    status = "pass" if all(checks.values()) else "fail"
    return CitationIntegrity(status=status, checks=checks, detail=detail)


def support_spans(terms: Terminology, card: EvidenceCard, concept_ids: list[str]) -> list[SupportSpan]:
    tags = terms.tag_passage(card.passage.text_iast)
    out = []
    for cid in concept_ids:
        for (s, e, txt) in tags.get(cid, [])[:3]:
            out.append(SupportSpan(passage_id=card.passage.passage_id, start=s, end=e, text=txt, concept=cid))
    return out


GENERIC_CONCEPTS = {"ahara"}


def assess_support(claim_concepts: list[str], passage_concepts: set[str]) -> tuple[str, str]:
    specific = [c for c in claim_concepts if c not in GENERIC_CONCEPTS] or claim_concepts
    if not specific:
        return "not_assessable_auto", "Claim names no curated domain concept; automatic support check not possible."
    inter = [c for c in specific if c in passage_concepts]
    if len(inter) == len(specific):
        return "concept_overlap_auto", f"All claim concepts ({', '.join(specific)}) are tagged in the cited passage(s). Overlap is not proof of support."
    if inter:
        return "partial_overlap_auto", f"Only {', '.join(inter)} of ({', '.join(specific)}) tagged in cited passage(s)."
    return "no_overlap_auto", f"None of the claim's concepts ({', '.join(specific)}) are tagged in the cited passage(s)."


def split_claims(text: str) -> list[str]:
    text = text.replace("\r", "")
    parts: list[str] = []
    for line in text.split("\n"):
        line = line.strip(" -*•\t")
        if not line:
            continue
        # split sentences but keep trailing citation labels with their sentence
        for s in re.split(r"(?<=[.!?।])\s+(?=[A-Zऀ-ॿ])", line):
            s = s.strip()
            if len(s) > 3:
                parts.append(s)
    return parts


def build_claims(raw_output: str, cards: list[EvidenceCard], terms: Terminology, store: CorpusStore,
                 run_meta: dict, withhold_positive: bool, bound_card: EvidenceCard | None = None,
                 start_index: int = 0) -> tuple[list[Claim], list[Claim]]:
    """Parse model output into claims; citation metadata is constructed server-side from the
    retrieved evidence ids only. Returns (shown, rejected)."""
    label_map = {c.label: c for c in cards}
    shown: list[Claim] = []
    rejected: list[Claim] = []
    for i, sent in enumerate(split_claims(raw_output), start=start_index):
        labels = list(dict.fromkeys(LABEL_RE.findall(sent)))
        if bound_card is not None:
            # per-passage mode: the citation is constructed server-side from the only passage shown
            # to the model; any label the model writes is ignored except foreign labels, which fail.
            labels = [bound_card.label]
            sent = LABEL_RE.sub("", sent)
        other_brackets = [b for b in ANY_BRACKET_RE.findall(sent) if not re.fullmatch(r"\s*E\d{1,2}\s*", b)]
        clean = LABEL_RE.sub("", sent).strip()
        clean = re.sub(r"\s+([.,;:।])", r"\1", clean)
        known = [l for l in labels if l in label_map]
        unknown = [l for l in labels if l not in label_map]
        cited_cards = [label_map[l] for l in known]
        concepts = [k for k in terms.concepts_in_query(clean, use_patterns=False) if k not in terms.meta_ids]
        spans: list[SupportSpan] = []
        for c in cited_cards:
            spans += support_spans(terms, c, concepts)
        integ_checks: dict[str, bool] = {"has_citation": bool(known), "no_unknown_labels": not unknown,
                                         "no_free_text_citations": not other_brackets}
        detail = []
        if unknown:
            detail.append(f"label(s) {unknown} do not correspond to retrieved evidence")
        if other_brackets:
            detail.append(f"free-text citation(s) {other_brackets} ignored; citations are built server-side")
        per_passage = [check_citation(store, c.passage.passage_id, c.passage.text_hash, spans) for c in cited_cards]
        for pc in per_passage:
            integ_checks.update({f"{k}": integ_checks.get(k, True) and v for k, v in pc.checks.items()})
            detail += pc.detail
        integrity = CitationIntegrity(status="pass" if all(integ_checks.values()) else "fail", checks=integ_checks, detail=detail)
        pconcepts = set().union(*[set(c.passage.concepts) for c in cited_cards]) if cited_cards else set()
        support, sdetail = assess_support(concepts, pconcepts) if cited_cards else ("no_overlap_auto", "No valid citation.")
        claim = Claim(
            claim_id=f"{run_meta['run_id']}-c{i + 1}", text=clean, claim_type="interpretation",
            evidence_ids=[c.passage.passage_id for c in cited_cards], evidence_labels=known,
            exact_support_spans=spans,
            source_locations=[f"{c.passage.work}, {c.passage.verse_label} (xml:id {c.passage.xml_ids[0]})" for c in cited_cards],
            interpretation_status="draft_generated", citation_integrity=integrity,
            support_assessment=support, support_detail=sdetail,
            limitations=["Generated by AyurParam from retrieved passages; draft until human review."
                         + (" Citation bound server-side: the model was shown only this passage." if bound_card is not None else ""),
                         "Support check is an automatic concept-overlap heuristic, not a judgment of correctness."],
            run_id=run_meta["run_id"], model_id=run_meta.get("model_id"), model_revision=run_meta.get("model_revision"),
            prompt_version=run_meta.get("prompt_version"), corpus_version=run_meta.get("corpus_version"),
        )
        reasons: list[str] = []
        if DOSE_RE.search(clean):
            reasons.append("contains a dose/quantity instruction (product policy: no dosing)")
        if ALWAYS_BLOCK_RE.search(clean):
            reasons.append("pregnancy/lactation safety assertion (product policy: never generated)")
        if withhold_positive and POSITIVE_USE_RE.search(clean):
            reasons.append("positive-use statement withheld by active safety rule")
        if integrity.status != "pass":
            reasons.append("citation integrity failed: " + ("; ".join(detail) or "no valid evidence label"))
        elif support == "no_overlap_auto":
            reasons.append("automatic support check: none of the sentence's concepts appear in the cited passage")
        elif support == "partial_overlap_auto":
            reasons.append("automatic support check: sentence introduces concepts not found in the cited passage (" + sdetail + ")")
        elif support == "not_assessable_auto":
            reasons.append("automatic support check not possible (no curated concept in sentence); withheld conservatively")
        reason = "; ".join(reasons) or None
        if reason:
            claim.shown_in_answer = False
            claim.withheld_reason = reason
            rejected.append(claim)
        else:
            shown.append(claim)
    return shown, rejected


def revalidate_claims(claims: list[Claim], store: CorpusStore, run_hashes: dict[str, str]) -> list[str]:
    """Re-run citation integrity on stored claims against the CURRENT corpus snapshot.
    Mutates claims in place (suppressing those that fail). Returns stale reasons."""
    reasons: list[str] = []
    for cl in claims:
        if cl.claim_type in ("safety_statement", "boundary_statement") and not cl.evidence_ids:
            continue
        all_checks: dict[str, bool] = {}
        detail: list[str] = []
        for pid in cl.evidence_ids:
            r = check_citation(store, pid, run_hashes.get(pid), cl.exact_support_spans)
            for k, v in r.checks.items():
                all_checks[k] = all_checks.get(k, True) and v
            detail += r.detail
        if not cl.evidence_ids:
            all_checks["has_citation"] = False
        status = "pass" if all(all_checks.values()) else "fail"
        if status == "fail" and cl.citation_integrity.status == "pass":
            reasons.append(f"{cl.claim_id}: " + ("; ".join(detail) or "evidence missing"))
        cl.citation_integrity = CitationIntegrity(status=status, checks=all_checks, detail=detail)
        if status == "fail":
            cl.shown_in_answer = False
            cl.withheld_reason = "evidence no longer valid: " + ("; ".join(detail) or "missing")
    return reasons
