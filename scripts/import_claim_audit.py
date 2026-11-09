"""Import a filled claim-support audit CSV into the append-only review log (idempotent).

    python scripts/import_claim_audit.py eval/audit/claim_audit_<ts>.csv [--dry-run]

- Rows without human_label or reviewer_name are skipped (never guessed).
- Re-importing the same file does not create duplicates.
- A changed label by the same reviewer is appended (history kept).
- Afterwards writes eval/results/eval_claim_audit_<ts>.json from the review log (see claim_audit_summary.py).
"""
import argparse
import json
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))

from pramaan.appdb import AppDB  # noqa: E402
from pramaan.audit import import_rows, latest_labels, read_csv, summarise  # noqa: E402
from pramaan.config import settings  # noqa: E402


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("csv")
    ap.add_argument("--dry-run", action="store_true")
    a = ap.parse_args()
    rows = read_csv(Path(a.csv))
    db = AppDB(settings.app_db)
    res = import_rows(rows, db, time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()), dry_run=a.dry_run)
    print(json.dumps(res, ensure_ascii=False, indent=1))
    if a.dry_run:
        return
    summ = summarise(rows, latest_labels(db))
    if summ["displayed"]["human_reviewed"] + summ["withheld"]["human_reviewed"] == 0:
        print("no human labels in the log for this sheet; no result file written")
        return

    def m(pop, k, n, d, note=""):
        return {"value": round(n / d, 4) if d else None, "numerator": n, "denominator": d, "note": note,
                **({} if d else {"reason": "no adjudicated rows"})}
    D, W = summ["displayed"], summ["withheld"]
    out = {"eval_id": f"eval_claim_audit_{time.strftime('%Y%m%d_%H%M%S')}", "created_at": time.strftime("%Y-%m-%dT%H:%M:%S"),
           "config_name": "human_claim_audit", "split": "audit_sheet", "n_cases": summ["total_records"], "llm_mode": "n/a",
           "n_live_inference": 0, "corpus_version": "", "hardware": "human review",
           "description": f"Human claim-support labels for {Path(a.csv).name}. Reviewer roles self-declared: {', '.join(summ['reviewers'])}",
           "metrics": {
               "human_adjudicated_claim_support": m("displayed", "supported", D["supported"], D["adjudicated_excluding_unresolved"], "DISPLAYED sentences labelled supported / adjudicated (unresolved excluded)"),
               "displayed_partial": m("displayed", "partial", D["partial"], D["adjudicated_excluding_unresolved"]),
               "displayed_unsupported_or_misread": m("displayed", "u", D["unsupported"] + D["passage_misread"], D["adjudicated_excluding_unresolved"]),
               "displayed_pending_or_unresolved": m("displayed", "p", D["pending"] + D["unresolved"], D["total_records"]),
               "withheld_actually_supported": m("withheld", "supported", W["supported"], W["adjudicated_excluding_unresolved"], "automatic filter false positives"),
               "withheld_pending_or_unresolved": m("withheld", "p", W["pending"] + W["unresolved"], W["total_records"]),
           },
           "summary": summ, "failures": [], "per_case": []}
    p = ROOT / "eval" / "results" / f"{out['eval_id']}.json"
    p.write_text(json.dumps(out, ensure_ascii=False, indent=1), encoding="utf-8")
    print("wrote", p)


if __name__ == "__main__":
    main()
