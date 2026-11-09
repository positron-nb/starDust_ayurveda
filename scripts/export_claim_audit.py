"""Export the claim-support audit sheet (CSV for Excel/Sheets + printable HTML; no app needed).

    python scripts/export_claim_audit.py [--result eval/results/eval_full_pramaan_....json] [--withheld 50]

Includes every DISPLAYED generated sentence and a deterministic sample of WITHHELD ones.
Automatic decisions are in auto_* columns; reviewers fill only the human_* / reviewer_* columns.
See docs/CLAIM_AUDIT_REVIEW_GUIDE.md.
"""
import argparse
import glob
import html
import json
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))

from pramaan.audit import build_rows, write_csv  # noqa: E402
from pramaan.config import settings  # noqa: E402
from pramaan.corpus.store import CorpusStore  # noqa: E402


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--result", default=None)
    ap.add_argument("--withheld", type=int, default=50)
    a = ap.parse_args()
    f = a.result or sorted(glob.glob(str(ROOT / "eval" / "results" / "eval_full_pramaan_*.json")))[-1]
    res = json.loads(Path(f).read_text(encoding="utf-8"))
    cases = {}
    for l in (ROOT / "eval" / "cases.jsonl").read_text(encoding="utf-8").splitlines():
        if l.strip():
            c = json.loads(l)
            cases[c["case_id"]] = c
    rows = build_rows(res, f, cases, CorpusStore(settings.corpus_db), a.withheld)
    d = ROOT / "eval" / "audit"
    d.mkdir(parents=True, exist_ok=True)
    stem = d / f"claim_audit_{time.strftime('%Y%m%d_%H%M%S')}"
    write_csv(rows, Path(f"{stem}.csv"))
    e = html.escape
    nd = sum(r["population"] == "displayed" for r in rows)
    parts = ["<!doctype html><meta charset='utf-8'><title>PRAMAAN claim-support audit</title>",
             "<style>body{font-family:'Noto Sans','Nirmala UI',sans-serif;max-width:1000px;margin:20px auto;padding:0 12px}"
             ".r{border:1px solid #ccc;border-radius:6px;padding:10px;margin:10px 0;page-break-inside:avoid}.m{color:#555;font-size:12px}"
             ".d{font-size:17px}.box{border-bottom:1px dotted #999;min-height:20px;margin:6px 0}.w{background:#fff6ec}</style>",
             f"<h1>PRAMAAN claim-support audit</h1><p class=m>Source run {e(Path(f).name)} · {len(rows)} records "
             f"({nd} displayed, {len(rows) - nd} withheld sample). Labels: supported · partial · unsupported · passage_misread · unresolved. "
             "Read docs/CLAIM_AUDIT_REVIEW_GUIDE.md first. Glosses are unreviewed AI drafts — judge against the Sanskrit.</p>"]
    for r in rows:
        parts.append(f"<div class='r{' w' if r['population'] == 'withheld' else ''}'><b>{e(r['record_id'])}</b> "
                     f"<span class=m>[{e(r['population'])} by automatic check] case {e(r['case_id'])} · Q: {e(r['question'])}</span>"
                     f"<p><b>Sentence:</b> {e(r['sentence'])}</p><p class=m>{e(r['locator'])} ({e(r['passage_id'])})</p>"
                     f"<p class=d>{e(r['passage_devanagari'])}</p><p>{e(r['passage_iast'])}</p>"
                     + (f"<p class=m>Draft gloss (unreviewed): {e(r['draft_gloss_unreviewed'])}</p>" if r["draft_gloss_unreviewed"] else "")
                     + (f"<p class=m>Automatic reason withheld: {e(r['auto_withheld_reason'])}</p>" if r["auto_withheld_reason"] else "")
                     + "<div>☐ supported ☐ partial ☐ unsupported ☐ passage_misread ☐ unresolved</div>"
                       "<div class=box>Exact supporting words:</div><div class=box>Comment:</div></div>")
    Path(f"{stem}.html").write_text("".join(parts), encoding="utf-8")
    print(json.dumps({"csv": f"{stem}.csv", "html": f"{stem}.html", "records": len(rows), "displayed": nd, "withheld": len(rows) - nd}))


if __name__ == "__main__":
    main()
