"""Export a claim-support audit sheet for a human reviewer (e.g. the BAMS teammate).

    python scripts/export_claim_audit.py            # latest eval/results/eval_full_pramaan_*.json
    python scripts/export_claim_audit.py --withheld 50

Writes eval/audit/claim_audit_<ts>.csv (open in Excel/Sheets; UTF-8 with BOM so Devanagari shows)
and a printable .html with the same rows. Every SHOWN generated sentence is included, plus a
deterministic sample of WITHHELD ones so the reviewer can also check what the filter removed.

Reviewer fills: support_label (supported / partial / unsupported / passage_misread),
exact_supporting_text, reason, reviewer_name, reviewer_role, review_date.
Then: python scripts/import_claim_audit.py <filled.csv>
"""
import argparse
import csv
import glob
import html
import json
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))

from pramaan.config import settings  # noqa: E402
from pramaan.corpus.store import CorpusStore  # noqa: E402

COLUMNS = ["item_id", "kind", "case_id", "question", "sentence", "passage_id", "locator", "passage_iast",
           "passage_devanagari", "draft_gloss_unreviewed", "withheld_reason_auto",
           "support_label", "exact_supporting_text", "reason", "reviewer_name", "reviewer_role", "review_date"]
REVIEWER_ROLES = "student_bams | student_md_phd | practitioner | engineer | other"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--result", default=None)
    ap.add_argument("--withheld", type=int, default=50)
    a = ap.parse_args()
    f = a.result or sorted(glob.glob(str(ROOT / "eval" / "results" / "eval_full_pramaan_*.json")))[-1]
    res = json.loads(Path(f).read_text(encoding="utf-8"))
    cases = {json.loads(l)["case_id"]: json.loads(l) for l in (ROOT / "eval" / "cases.jsonl").read_text(encoding="utf-8").splitlines() if l.strip()}
    store = CorpusStore(settings.corpus_db)
    rows, withheld = [], []
    for pc in res["per_case"]:
        q = cases.get(pc["case_id"], {}).get("query", "")
        for i, s in enumerate(pc["shown"]):
            rows.append(("S", pc["case_id"], i, q, s["text"], s["evidence"], ""))
        for i, w in enumerate(pc["withheld"]):
            withheld.append(("W", pc["case_id"], i, q, w["text"], w["evidence"], w["reason"] or ""))
    step = max(1, len(withheld) // a.withheld) if a.withheld else 0
    rows += withheld[::step][: a.withheld] if step else []
    out_rows = []
    for kind, cid, i, q, text, ev, reason in rows:
        pid = ev[0] if ev else ""
        p = store.get(pid, include_revoked=True) if pid else None
        out_rows.append({
            "item_id": f"{cid}-{kind}{i + 1}", "kind": "shown" if kind == "S" else "withheld", "case_id": cid, "question": q,
            "sentence": text, "passage_id": pid, "locator": f"{p.work}, {p.verse_label}" if p else "",
            "passage_iast": p.text_iast if p else "", "passage_devanagari": p.text_deva if p else "",
            "draft_gloss_unreviewed": p.gloss.text if p and p.gloss else "", "withheld_reason_auto": reason,
            "support_label": "", "exact_supporting_text": "", "reason": "", "reviewer_name": "", "reviewer_role": "", "review_date": "",
        })
    d = ROOT / "eval" / "audit"
    d.mkdir(parents=True, exist_ok=True)
    stem = d / f"claim_audit_{time.strftime('%Y%m%d_%H%M%S')}"
    with open(f"{stem}.csv", "w", encoding="utf-8-sig", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=COLUMNS)
        w.writeheader()
        w.writerows(out_rows)
    e = html.escape
    parts = [f"<!doctype html><meta charset='utf-8'><title>PRAMAAN claim-support audit</title>"
             "<style>body{font-family:'Noto Sans','Nirmala UI',sans-serif;max-width:1000px;margin:20px auto;padding:0 12px}"
             ".r{border:1px solid #ccc;border-radius:6px;padding:10px;margin:10px 0;page-break-inside:avoid}.m{color:#555;font-size:12px}"
             ".d{font-size:17px}.box{border-bottom:1px dotted #999;min-height:20px;margin:4px 0}</style>",
             f"<h1>Claim-support audit</h1><p class=m>Source run: {e(Path(f).name)} · {len(out_rows)} items "
             f"({sum(r['kind'] == 'shown' for r in out_rows)} shown, {sum(r['kind'] == 'withheld' for r in out_rows)} withheld sample). "
             "For each item: does the cited verse, read in context, support the sentence? Labels: supported / partial / unsupported / passage_misread. "
             f"Record exact supporting words. Roles: {REVIEWER_ROLES}. Glosses are unreviewed AI drafts.</p>"]
    for r in out_rows:
        parts.append(f"<div class=r><b>{e(r['item_id'])}</b> <span class=m>[{e(r['kind'])}] Q: {e(r['question'])}</span>"
                     f"<p><b>Sentence:</b> {e(r['sentence'])}</p><p class=m>{e(r['locator'])} ({e(r['passage_id'])})</p>"
                     f"<p class=d>{e(r['passage_devanagari'])}</p><p>{e(r['passage_iast'])}</p>"
                     + (f"<p class=m>Draft gloss (unreviewed): {e(r['draft_gloss_unreviewed'])}</p>" if r['draft_gloss_unreviewed'] else "")
                     + (f"<p class=m>Auto-withheld because: {e(r['withheld_reason_auto'])}</p>" if r['withheld_reason_auto'] else "")
                     + "<div>Label: ☐ supported ☐ partial ☐ unsupported ☐ passage misread</div><div class=box>Supporting words:</div><div class=box>Reason:</div></div>")
    Path(f"{stem}.html").write_text("".join(parts), encoding="utf-8")
    print(json.dumps({"csv": f"{stem}.csv", "html": f"{stem}.html", "items": len(out_rows)}, ensure_ascii=False))


if __name__ == "__main__":
    main()
