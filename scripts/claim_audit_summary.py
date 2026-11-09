"""Report claim-audit progress from the review log (no changes made).

    python scripts/claim_audit_summary.py [eval/audit/claim_audit_<ts>.csv]

Defaults to the newest sheet. Displayed and withheld populations are always reported separately.
"""
import glob
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))

from pramaan.appdb import AppDB  # noqa: E402
from pramaan.audit import latest_labels, read_csv, summarise  # noqa: E402
from pramaan.config import settings  # noqa: E402

if __name__ == "__main__":
    sheet = sys.argv[1] if len(sys.argv) > 1 else sorted(glob.glob(str(ROOT / "eval" / "audit" / "claim_audit_*.csv")))[-1]
    s = summarise(read_csv(Path(sheet)), latest_labels(AppDB(settings.app_db)))
    s["sheet"] = Path(sheet).name
    print(json.dumps(s, ensure_ascii=False, indent=1))
