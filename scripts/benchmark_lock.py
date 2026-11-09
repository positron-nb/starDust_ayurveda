"""Validate and lock the reviewer-authored retrieval benchmark.

    python scripts/benchmark_lock.py eval/fresh_benchmark/questions.csv [--force-relock]

Checks every gold/acceptable id exists in the corpus, writes questions.jsonl and LOCK (sha256 of the
test rows). Re-locking a changed test split requires --force-relock and is recorded in LOCK history.
"""
import argparse
import csv
import hashlib
import json
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))

from pramaan.config import settings  # noqa: E402
from pramaan.corpus.store import CorpusStore  # noqa: E402


def test_hash(rows):
    blob = "".join(json.dumps(r, ensure_ascii=False, sort_keys=True) for r in rows if r["split"] == "test")
    return hashlib.sha256(blob.encode("utf-8")).hexdigest()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("csv")
    ap.add_argument("--force-relock", action="store_true")
    a = ap.parse_args()
    store = CorpusStore(settings.corpus_db)
    indexed = {p.passage_id for p in store.indexed_passages()}
    rows, errs = [], []
    for r in csv.DictReader(open(a.csv, encoding="utf-8-sig")):
        if not (r.get("question") or "").strip():
            continue
        split = r["split"].strip()
        gold = [x.strip() for x in (r.get("gold_passages") or "").split(";") if x.strip()]
        acc = [x.strip() for x in (r.get("acceptable_passages") or "").split(";") if x.strip()]
        cov = (r.get("coverage") or "indexed").strip()
        if split not in ("dev", "test"):
            errs.append(f"{r['question_id']}: split must be dev or test")
        if cov == "indexed" and not gold:
            errs.append(f"{r['question_id']}: indexed question without gold passages")
        for g in gold + acc:
            if store.get(g) is None:
                errs.append(f"{r['question_id']}: passage {g} does not exist")
            elif g not in indexed:
                errs.append(f"{r['question_id']}: passage {g} exists but is not in the indexed module")
        rows.append({"question_id": r["question_id"].strip(), "question": r["question"].strip(), "language": r["language"].strip(),
                     "split": split, "gold": gold, "acceptable": acc, "source_constraint": (r.get("source_constraint") or "").strip(),
                     "coverage": cov, "author": (r.get("author") or "").strip(), "notes": (r.get("notes") or "").strip()})
    if errs:
        print("\n".join(errs))
        raise SystemExit("not locked: fix the errors above")
    d = Path(a.csv).parent
    lock = d / "LOCK"
    h = test_hash(rows)
    hist = json.loads(lock.read_text()) if lock.exists() else {"history": []}
    if hist.get("test_sha256") and hist["test_sha256"] != h and not a.force_relock:
        raise SystemExit("test split differs from the locked version; use --force-relock only if the reviewer changed it before any evaluation")
    (d / "questions.jsonl").write_text("".join(json.dumps(r, ensure_ascii=False) + "\n" for r in rows), encoding="utf-8")
    hist["history"].append({"at": time.strftime("%Y-%m-%dT%H:%M:%S"), "test_sha256": h, "n_dev": sum(r["split"] == "dev" for r in rows),
                            "n_test": sum(r["split"] == "test" for r in rows)})
    hist["test_sha256"] = h
    lock.write_text(json.dumps(hist, indent=1))
    print(json.dumps(hist["history"][-1]))


if __name__ == "__main__":
    main()
