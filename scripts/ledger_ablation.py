"""Evidence-ledger ablation from the human claim audit (no new generation needed).

    python scripts/ledger_ablation.py [eval/audit/claim_audit_<ts>.csv]

Config A = every sentence AyurParam generated for the audited run (no evidence gating).
Config B = only the sentences PRAMAAN displayed (gating on). Same queries, same passages, same model run.
The audit labels ALL displayed sentences and a random-like systematic sample of withheld ones, so
A-level counts for withheld sentences are estimated with weight = total_withheld / sampled_withheld.
Prints 'not measured' until labels exist. Never fabricates labels.
"""
import glob
import json
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))

from pramaan.appdb import AppDB  # noqa: E402
from pramaan.audit import ADJUDICATED, latest_labels, read_csv  # noqa: E402
from pramaan.config import settings  # noqa: E402

if __name__ == "__main__":
    sheet = Path(sys.argv[1] if len(sys.argv) > 1 else sorted(glob.glob(str(ROOT / "eval" / "audit" / "claim_audit_*.csv")))[-1])
    rows = read_csv(sheet)
    src = ROOT / "eval" / "results" / rows[0]["source_eval_file"]
    run = json.loads(src.read_text(encoding="utf-8"))
    total_shown = sum(len(p["shown"]) for p in run["per_case"])
    total_withheld = sum(len(p["withheld"]) for p in run["per_case"])
    labels = latest_labels(AppDB(settings.app_db))
    lab = {pop: Counter(labels[r["record_id"]]["label"] for r in rows if r["population"] == pop and r["record_id"] in labels)
           for pop in ("displayed", "withheld")}
    n_sampled_w = sum(1 for r in rows if r["population"] == "withheld")
    adj_d = sum(lab["displayed"][k] for k in ADJUDICATED)
    adj_w = sum(lab["withheld"][k] for k in ADJUDICATED)
    out = {"source_run": src.name, "config_A_sentences": total_shown + total_withheld, "config_B_sentences": total_shown,
           "withheld_total": total_withheld, "withheld_sampled": n_sampled_w,
           "labelled": {"displayed": dict(lab["displayed"]), "withheld": dict(lab["withheld"])}}
    if adj_d < total_shown or adj_w == 0:
        out["status"] = (f"NOT MEASURED: {adj_d}/{total_shown} displayed and {adj_w}/{n_sampled_w} sampled withheld sentences "
                         "have adjudicated labels (unresolved excluded). Complete the claim audit first.")
    else:
        w = total_withheld / adj_w
        unsup = lambda c: c["unsupported"] + c["passage_misread"]  # noqa: E731
        out["estimates"] = {
            "B_unsupported_or_misread_displayed": unsup(lab["displayed"]),
            "A_unsupported_or_misread_displayed_est": round(unsup(lab["displayed"]) + unsup(lab["withheld"]) * w, 1),
            "B_supported_displayed": lab["displayed"]["supported"],
            "A_supported_displayed_est": round(lab["displayed"]["supported"] + lab["withheld"]["supported"] * w, 1),
            "false_withholding_est (supported sentences removed by the gate)": round(lab["withheld"]["supported"] * w, 1),
            "partial_displayed_B": lab["displayed"]["partial"],
            "note": f"withheld counts extrapolated with weight {w:.2f} from {adj_w} adjudicated sampled sentences; sampling error not quantified",
        }
    print(json.dumps(out, ensure_ascii=False, indent=1))
