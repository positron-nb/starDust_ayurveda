"""Review-packet export (JSON + printable HTML). All dynamic text is HTML-escaped."""
from __future__ import annotations

from html import escape

from .schemas import RunResult

CSS = """
body{font-family:'Noto Sans','Noto Sans Devanagari',system-ui,sans-serif;color:#1f2a1f;max-width:900px;margin:24px auto;padding:0 16px;line-height:1.5}
h1{color:#1e4d2b;font-size:22px} h2{color:#1e4d2b;font-size:17px;border-bottom:1px solid #d9d2c3;padding-bottom:4px;margin-top:28px}
.box{border:1px solid #d9d2c3;border-radius:6px;padding:10px 12px;margin:8px 0;background:#fbf8f2}
.tag{display:inline-block;font-size:11px;padding:1px 6px;border-radius:10px;margin-right:4px;border:1px solid #999}
.warn{border-color:#c2410c;background:#fff4ec} .muted{color:#5b6b5b;font-size:12px}
.deva{font-family:'Noto Serif Devanagari','Noto Sans Devanagari',serif;font-size:17px}
table{border-collapse:collapse;width:100%;font-size:13px} td,th{border:1px solid #ddd;padding:4px 6px;text-align:left;vertical-align:top}
@media print{.noprint{display:none}}
"""


def packet_json(r: RunResult) -> dict:
    d = r.model_dump()
    d["_packet"] = {
        "format": "pramaan-review-packet/1",
        "disclaimer": "Educational/clinician-support draft. Not a diagnosis, prescription or safety clearance. Generated explanations are drafts pending human review; automatic support checks are heuristics.",
    }
    return d


def packet_html(r: RunResult, reviews: list[dict]) -> str:
    e = escape
    t = r.trace
    parts = [f"<!doctype html><html lang='{e(r.lang)}'><head><meta charset='utf-8'><title>PRAMAAN review packet {e(r.run_id)}</title><style>{CSS}</style></head><body>"]
    parts.append("<h1>PRAMAAN review packet</h1>")
    parts.append(f"<p class='muted'>Run {e(r.run_id)} · {e(t.created_at)} · status <b>{e(r.status)}</b> · LLM mode <b>{e(t.llm_mode)}</b> · inference ran: <b>{e(str(t.inference_ran))}</b><br>"
                 f"Model {e(t.model_id)} @ {e(t.model_revision[:12])} · prompt {e(t.prompt_version)} · corpus {e(t.corpus_version)} · rules {e(t.rules_version)} · terms {e(t.terms_version)}"
                 + (f"<br><b>Revalidated {e(r.revalidated_at or '')}; stale: {e(str(r.stale))}</b> {e('; '.join(r.stale_reasons))}" if r.revalidated_at else "") + "</p>")
    parts.append("<div class='box warn'>Educational / clinician-support draft. Not a diagnosis, prescription, dose or safety clearance. "
                 "Generated text is pending human review. Citation checks confirm structural integrity only, not medical truth.</div>")
    parts.append(f"<h2>Question</h2><div class='box'>{e(r.query)}</div>")
    if r.escalation_message:
        parts.append(f"<h2>Urgent-care message</h2><div class='box warn'>{e(r.escalation_message)}</div>")
    parts.append("<h2>Case facts (tri-state)</h2><table><tr><th>Fact</th><th>State</th><th>Values</th><th>Origin</th></tr>")
    for f in r.facts:
        parts.append(f"<tr><td>{e(f.key)}</td><td>{e(f.state)}</td><td>{e(', '.join(f.values))}</td><td>{e(f.origin)}</td></tr>")
    parts.append("</table>")
    if r.safety_alerts:
        parts.append("<h2>Safety alerts and missing information</h2>")
        for a in r.safety_alerts:
            parts.append(f"<div class='box warn'><b>{e(a.rule_id)}</b> ({e(a.basis_type)}; review {e(a.review_status)}): {e(a.message)}"
                         + (f"<br><span class='muted'>Source statement: {e(a.statement_paraphrase or '')} Scope: {e(a.statement_scope or '')} {e(a.source_url or '')}</span>" if a.statement_id else "")
                         + "</div>")
    parts.append(f"<h2>Answer status</h2><div class='box'>{e(r.answer_notice)}</div>")
    parts.append("<h2>Claims (evidence ledger)</h2><table><tr><th>Claim</th><th>Evidence</th><th>Citation integrity</th><th>Support (auto)</th><th>Review</th></tr>")
    for c in r.claims:
        parts.append(f"<tr><td>{e(c.text)}<div class='muted'>{e(c.claim_type)} · {e(c.interpretation_status)}</div></td>"
                     f"<td>{e('; '.join(c.source_locations))}</td><td>{e(c.citation_integrity.status)}</td>"
                     f"<td>{e(c.support_assessment)}<div class='muted'>{e(c.support_detail)}</div></td><td>{e(c.review_status)}</td></tr>")
    parts.append("</table>")
    if r.rejected_claims:
        parts.append("<h2>Withheld generated sentences (audit)</h2><table><tr><th>Text</th><th>Reason</th></tr>")
        for c in r.rejected_claims:
            parts.append(f"<tr><td>{e(c.text)}</td><td>{e(c.withheld_reason or '')}</td></tr>")
        parts.append("</table>")
    parts.append("<h2>Source passages</h2>")
    for c in r.evidence:
        p = c.passage
        parts.append(f"<div class='box'><b>[{e(c.label)}] {e(p.work)}, {e(p.verse_label)}</b> <span class='tag'>{e(c.role)}</span>"
                     f"<div class='muted'>xml:id {e(', '.join(p.xml_ids))} · {e(p.source_id)} · hash {e(p.text_hash[:12])}</div>"
                     f"<div class='deva'>{e(p.text_deva)}</div><div>{e(p.text_iast)}</div>"
                     + (f"<div class='muted'>Unreviewed draft gloss ({e(p.gloss.author)}): {e(p.gloss.text)}</div>" if p.gloss else "")
                     + (f"<div class='muted'>{e(c.role_note)}</div>" if c.role_note else "") + "</div>")
    if r.unresolved_questions or r.missing_information:
        parts.append("<h2>Unresolved questions</h2><ul>" + "".join(f"<li>{e(q)}</li>" for q in dict.fromkeys(r.missing_information + r.unresolved_questions)) + "</ul>")
    parts.append("<h2>Human review history</h2>")
    if reviews:
        parts.append("<table><tr><th>When</th><th>Target</th><th>Decision</th><th>Reviewer (self-declared role)</th><th>Note</th></tr>")
        for rv in reviews:
            parts.append(f"<tr><td>{e(rv['created_at'])}</td><td>{e(rv['target_type'])} {e(rv['target_id'])}</td><td>{e(rv['decision'])}</td>"
                         f"<td>{e(rv['reviewer_name'])} ({e(rv['reviewer_role'])})</td><td>{e(rv.get('note') or '')}</td></tr>")
        parts.append("</table><p class='muted'>Reviewer roles are self-declared and unverified. A student review is not professional clinical approval.</p>")
    else:
        parts.append("<p>No human review recorded. All generated content remains pending.</p>")
    parts.append("<p class='muted'>Sources: SARIT TEI editions (CC BY-SA 3.0, see manifest); NCCIH (public domain). Application code Apache-2.0.</p>")
    parts.append("</body></html>")
    return "".join(parts)
