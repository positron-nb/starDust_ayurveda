"""Human claim-support audit: export rows, import labels idempotently, summarise.

Automatic labels (what PRAMAAN's checks decided) and human labels (what a reviewer decided) are kept
in separate columns and are never mixed. Missing labels are never guessed.
"""
from __future__ import annotations

import csv
import hashlib
import json
from collections import Counter
from pathlib import Path

HUMAN_LABELS = ("supported", "partial", "unsupported", "passage_misread", "unresolved")
ADJUDICATED = ("supported", "partial", "unsupported", "passage_misread")  # 'unresolved' is NOT adjudicated
DECISION = {"supported": "accepted", "partial": "needs_revision", "unsupported": "rejected",
            "passage_misread": "rejected", "unresolved": "comment"}
ROLES = {"student_bams", "student_md_phd", "practitioner", "engineer", "other"}

COLUMNS = [
    "record_id", "population", "auto_decision", "auto_support_assessment", "auto_withheld_reason",
    "case_id", "question", "sentence", "passage_id", "locator", "passage_iast", "passage_devanagari",
    "draft_gloss_unreviewed", "source_eval_file",
    # ---- human columns (filled by the reviewer) ----
    "human_label", "exact_supporting_text", "reviewer_comment", "reviewer_name", "reviewer_role", "review_date",
]


def record_id(source_file: str, case_id: str, population: str, sentence: str, passage_id: str) -> str:
    """Stable id: depends only on content, not on row order."""
    h = hashlib.sha256("\x1f".join([Path(source_file).name, case_id, population, sentence.strip(), passage_id]).encode("utf-8"))
    return "CA-" + h.hexdigest()[:12]


def build_rows(result: dict, source_file: str, cases: dict, store, n_withheld: int = 50) -> list[dict]:
    shown, withheld = [], []
    for pc in result["per_case"]:
        q = cases.get(pc["case_id"], {}).get("query", "")
        for s in pc.get("shown", []):
            shown.append((pc["case_id"], q, "displayed", s["text"], s["evidence"], "shown", s.get("support", ""), ""))
        for w in pc.get("withheld", []):
            withheld.append((pc["case_id"], q, "withheld", w["text"], w["evidence"], "withheld", "", w.get("reason") or ""))
    step = max(1, len(withheld) // n_withheld) if n_withheld and withheld else 0
    picked = shown + (withheld[::step][:n_withheld] if step else [])
    rows, seen = [], set()
    for cid, q, pop, text, ev, dec, sup, reason in picked:
        pid = ev[0] if ev else ""
        rid = record_id(source_file, cid, pop, text, pid)
        if rid in seen:
            continue
        seen.add(rid)
        p = store.get(pid, include_revoked=True) if pid else None
        rows.append({
            "record_id": rid, "population": pop, "auto_decision": dec, "auto_support_assessment": sup,
            "auto_withheld_reason": reason, "case_id": cid, "question": q, "sentence": text, "passage_id": pid,
            "locator": f"{p.work}, {p.verse_label}" if p else "", "passage_iast": p.text_iast if p else "",
            "passage_devanagari": p.text_deva if p else "", "draft_gloss_unreviewed": p.gloss.text if p and p.gloss else "",
            "source_eval_file": Path(source_file).name,
            "human_label": "", "exact_supporting_text": "", "reviewer_comment": "", "reviewer_name": "", "reviewer_role": "", "review_date": "",
        })
    return rows


def write_csv(rows: list[dict], path: Path) -> None:
    with open(path, "w", encoding="utf-8-sig", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=COLUMNS)
        w.writeheader()
        w.writerows(rows)


def read_csv(path: Path) -> list[dict]:
    rows = list(csv.DictReader(open(path, encoding="utf-8-sig")))
    # backwards compatibility with the first sheet format (item_id/kind/support_label)
    for r in rows:
        if "record_id" not in r and "item_id" in r:
            r["record_id"] = r["item_id"]
            r["population"] = "displayed" if r.get("kind") == "shown" else "withheld"
            r["human_label"] = r.get("support_label", "")
            r["reviewer_comment"] = r.get("reason", "")
    return rows


def _note(r: dict, label: str) -> str:
    return json.dumps({"audit": "claim_support", "label": label, "population": r.get("population"),
                       "passage_id": r.get("passage_id"), "exact_supporting_text": (r.get("exact_supporting_text") or "").strip(),
                       "comment": (r.get("reviewer_comment") or "").strip(), "sentence": (r.get("sentence") or "")[:300]},
                      ensure_ascii=False)


def import_rows(rows: list[dict], db, now: str, dry_run: bool = False) -> dict:
    """Idempotent: an identical (record, reviewer, label, supporting text, comment) entry is skipped.
    A changed label by the same reviewer is appended as a new review (history kept)."""
    stats = Counter()
    errors = []
    existing = {}
    if db is not None:
        for rv in db.reviews("claim"):
            existing.setdefault((rv["target_id"], rv["reviewer_name"]), []).append(rv.get("note") or "")
    for r in rows:
        label = (r.get("human_label") or "").strip().lower()
        name = (r.get("reviewer_name") or "").strip()
        if not label or not name:
            stats["unlabelled_skipped"] += 1
            continue
        if label not in HUMAN_LABELS:
            errors.append(f"{r.get('record_id')}: unknown label '{label}'")
            continue
        note = _note(r, label)
        key = (r["record_id"], name[:80])
        if note in existing.get(key, []):
            stats["duplicate_skipped"] += 1
            continue
        role = (r.get("reviewer_role") or "other").strip()
        if role not in ROLES:
            role = "other"
        if not dry_run and db is not None:
            from .schemas import ReviewAction
            db.add_review(ReviewAction(target_type="claim", target_id=r["record_id"], decision=DECISION[label], note=note[:2000],
                                       reviewer_name=name[:80], reviewer_role=role), (r.get("review_date") or "").strip() or now)
        existing.setdefault(key, []).append(note)
        stats["imported"] += 1
    return {"stats": dict(stats), "errors": errors}


def latest_labels(db) -> dict[str, dict]:
    """record_id -> latest human label entry (per record; latest across reviewers)."""
    out = {}
    for rv in reversed(db.reviews("claim")):  # oldest first
        try:
            n = json.loads(rv.get("note") or "")
        except Exception:
            continue
        if n.get("audit") != "claim_support":
            continue
        out[rv["target_id"]] = {**n, "reviewer_name": rv["reviewer_name"], "reviewer_role": rv["reviewer_role"], "created_at": rv["created_at"]}
    return out


def summarise(sheet_rows: list[dict], labels: dict[str, dict]) -> dict:
    out = {}
    for pop in ("displayed", "withheld"):
        rs = [r for r in sheet_rows if r.get("population") == pop]
        c = Counter(labels[r["record_id"]]["label"] for r in rs if r["record_id"] in labels)
        adjudicated = sum(c[k] for k in ADJUDICATED)
        out[pop] = {
            "total_records": len(rs), "human_reviewed": sum(c.values()), "pending": len(rs) - sum(c.values()),
            **{k: c[k] for k in HUMAN_LABELS}, "adjudicated_excluding_unresolved": adjudicated,
            "supported_rate_of_adjudicated": round(c["supported"] / adjudicated, 4) if adjudicated else None,
            "supported_or_partial_rate_of_adjudicated": round((c["supported"] + c["partial"]) / adjudicated, 4) if adjudicated else None,
        }
    out["total_records"] = len(sheet_rows)
    out["reviewers"] = sorted({f"{v['reviewer_name']} ({v['reviewer_role']}, self-declared)" for v in labels.values()})
    out["note"] = ("Displayed and withheld populations are reported separately. A withheld sentence labelled 'supported' "
                   "is a false positive of the automatic filter, not an error of the reviewer. 'unresolved' is not adjudicated.")
    return out
