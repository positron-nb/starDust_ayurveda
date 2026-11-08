"""Import a filled claim-support audit CSV into the append-only review log and compute the
human-adjudicated support metric from the rows that were actually labelled.

    python scripts/import_claim_audit.py eval/audit/claim_audit_<ts>.csv [--dry-run]

Rows without support_label or reviewer_name are skipped (never guessed). Writes
eval/results/eval_claim_audit_<ts>.json, which the Evaluation & Review screen shows.
"""
import argparse
import csv
import json
import sys
import time
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))

from pramaan.appdb import AppDB  # noqa: E402
from pramaan.config import settings  # noqa: E402
from pramaan.schemas import ReviewAction  # noqa: E402

LABELS = {"supported": "accepted", "partial": "needs_revision", "unsupported": "rejected", "passage_misread": "rejected"}
ROLES = {"student_bams", "student_md_phd", "practitioner", "engineer", "other"}


def ratio(n, d, note=""):
    return {"value": round(n / d, 4) if d else None, "numerator": n, "denominator": d, "note": note,
            **({} if d else {"reason": "no labelled rows"})}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("csv")
    ap.add_argument("--dry-run", action="store_true")
    a = ap.parse_args()
    rows = list(csv.DictReader(open(a.csv, encoding="utf-8-sig")))
    done, skipped, errors = [], 0, []
    db = None if a.dry_run else AppDB(settings.app_db)
    for r in rows:
        lab = (r.get("support_label") or "").strip().lower()
        name = (r.get("reviewer_name") or "").strip()
        if not lab or not name:
            skipped += 1
            continue
        if lab not in LABELS:
            errors.append(f"{r['item_id']}: unknown label '{lab}'")
            continue
        role = (r.get("reviewer_role") or "other").strip()
        role = role if role in ROLES else "other"
        note = f"[claim-support audit: {lab}] supporting text: {r.get('exact_supporting_text', '').strip()} | reason: {r.get('reason', '').strip()} | passage {r['passage_id']} | sentence: {r['sentence'][:300]}"
        if db:
            db.add_review(ReviewAction(target_type="claim", target_id=r["item_id"], decision=LABELS[lab], note=note[:2000],
                                       reviewer_name=name[:80], reviewer_role=role),
                          (r.get("review_date") or "").strip() or time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()))
        done.append((r["kind"], lab, name, role))
    shown = [x for x in done if x[0] == "shown"]
    withh = [x for x in done if x[0] == "withheld"]
    c_sh, c_wh = Counter(x[1] for x in shown), Counter(x[1] for x in withh)
    metrics = {
        "human_adjudicated_claim_support": ratio(c_sh["supported"], len(shown), "shown claims fully supported by the cited verse (human label)"),
        "shown_claims_partial": ratio(c_sh["partial"], len(shown)),
        "shown_claims_unsupported_or_misread": ratio(c_sh["unsupported"] + c_sh["passage_misread"], len(shown)),
        "withheld_sentences_actually_supported": ratio(c_wh["supported"], len(withh), "filter false-positives: supported sentences the automatic check removed"),
        "rows_labelled": {"value": len(done), "note": f"{skipped} rows unlabelled/skipped of {len(rows)}"},
        "reviewers": {"value": len({x[2] for x in done}), "note": "; ".join(sorted({f'{x[2]} ({x[3]}, self-declared)' for x in done}))},
    }
    out = {"eval_id": f"eval_claim_audit_{time.strftime('%Y%m%d_%H%M%S')}", "created_at": time.strftime("%Y-%m-%dT%H:%M:%S"),
           "config_name": "human_claim_audit", "description": f"Human claim-support labels imported from {Path(a.csv).name}. Roles self-declared, unverified.",
           "split": "test", "n_cases": len(done), "llm_mode": "n/a", "n_live_inference": 0, "corpus_version": "", "hardware": "human review",
           "metrics": metrics, "failures": [{"case_id": e.split(":")[0], "reason": e} for e in errors], "per_case": []}
    if done and not a.dry_run:
        p = ROOT / "eval" / "results" / f"{out['eval_id']}.json"
        p.write_text(json.dumps(out, ensure_ascii=False, indent=1), encoding="utf-8")
        print("wrote", p)
    print(json.dumps(metrics, ensure_ascii=False, indent=1))
    if errors:
        print("errors:", errors)


if __name__ == "__main__":
    main()
