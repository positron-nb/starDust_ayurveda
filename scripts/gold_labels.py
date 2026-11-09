"""Gold-label versions for retrieval evaluation.

    python scripts/gold_labels.py freeze-v1          # eval/gold/gold_v1_original.jsonl (+ sha256), never edited again
    python scripts/gold_labels.py export-v2-sheet    # eval/gold/gold_v2_adjudication_sheet.csv for the reviewer
    python scripts/gold_labels.py import-v2 <filled.csv>   # eval/gold/gold_v2_adjudicated.jsonl

v2 sheet rows: every v1 gold passage of each case PLUS the current top-5 passages that are not in v1
(so the reviewer can also add missed relevant verses). Labels: direct / contextual / not_relevant.
Metrics must be reported on v1 and v2 separately; v2 is a different benchmark, not an "improvement".
"""
import csv
import hashlib
import json
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))
G = ROOT / "eval" / "gold"
LABELS = ("direct", "contextual", "not_relevant")


def cases():
    return [json.loads(l) for l in (ROOT / "eval" / "cases.jsonl").read_text(encoding="utf-8").splitlines() if l.strip()]


def freeze_v1():
    G.mkdir(parents=True, exist_ok=True)
    rows = [{"case_id": c["case_id"], "split": c["split"], "query": c["query"], "relevant_passages": c["expected"]["relevant_passages"]}
            for c in cases() if c["expected"].get("relevant_passages")]
    blob = "".join(json.dumps(r, ensure_ascii=False, sort_keys=True) + "\n" for r in rows)
    p = G / "gold_v1_original.jsonl"
    if p.exists() and p.read_text(encoding="utf-8") != blob:
        raise SystemExit("gold_v1_original.jsonl already exists and differs — v1 is frozen; do not overwrite")
    p.write_text(blob, encoding="utf-8")
    (G / "gold_v1_original.sha256").write_text(hashlib.sha256(blob.encode()).hexdigest() + "\n")
    print(len(rows), "cases frozen;", hashlib.sha256(blob.encode()).hexdigest()[:16])


def export_v2_sheet():
    from pramaan.config import settings
    from pramaan.corpus.store import CorpusStore
    from pramaan.llm import LLMAdapter
    from pramaan.pipeline import Engine
    from pramaan.retrieval import Retriever
    from pramaan.safety import load_policy
    from pramaan.schemas import QueryRequest
    from pramaan.terms import load_terminology
    store = CorpusStore(settings.corpus_db)
    terms = load_terminology()
    eng = Engine(store, terms, load_policy(), LLMAdapter(), Retriever(store, terms))
    v1 = [json.loads(l) for l in (G / "gold_v1_original.jsonl").read_text(encoding="utf-8").splitlines()]
    out = []
    for c in v1:
        r = eng.run(QueryRequest(query=c["query"], use_model=False))
        top = [e.passage.passage_id for e in r.evidence if e.role == "primary"][:5]
        for pid, origin in [(p, "v1_gold") for p in c["relevant_passages"]] + [(p, "retrieved_not_in_v1") for p in top if p not in c["relevant_passages"]]:
            p = store.get(pid)
            out.append({"case_id": c["case_id"], "split": c["split"], "query": c["query"], "passage_id": pid, "origin": origin,
                        "locator": f"{p.work}, {p.verse_label}" if p else "", "passage_iast": p.text_iast if p else "",
                        "passage_devanagari": p.text_deva if p else "", "relevance_label": "", "reason": "", "reviewer_name": "",
                        "reviewer_role": "", "review_date": ""})
    path = G / "gold_v2_adjudication_sheet.csv"
    with open(path, "w", encoding="utf-8-sig", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=list(out[0]))
        w.writeheader()
        w.writerows(out)
    print(path, len(out), "rows")


def import_v2(csv_path):
    rows = list(csv.DictReader(open(csv_path, encoding="utf-8-sig")))
    v1 = {json.loads(l)["case_id"]: json.loads(l) for l in (G / "gold_v1_original.jsonl").read_text(encoding="utf-8").splitlines()}
    by = {}
    pending = 0
    for r in rows:
        lab = (r.get("relevance_label") or "").strip().lower()
        if lab not in LABELS or not (r.get("reviewer_name") or "").strip():
            pending += 1
            continue
        by.setdefault(r["case_id"], []).append(r)
    out = []
    for cid, rs in by.items():
        out.append({"case_id": cid, "split": v1[cid]["split"], "query": v1[cid]["query"],
                    "direct": [r["passage_id"] for r in rs if r["relevance_label"] == "direct"],
                    "contextual": [r["passage_id"] for r in rs if r["relevance_label"] == "contextual"],
                    "not_relevant": [r["passage_id"] for r in rs if r["relevance_label"] == "not_relevant"],
                    "reasons": {r["passage_id"]: r.get("reason", "") for r in rs},
                    "reviewers": sorted({f"{r['reviewer_name']} ({r.get('reviewer_role') or 'other'})" for r in rs})})
    p = G / "gold_v2_adjudicated.jsonl"
    p.write_text("".join(json.dumps(x, ensure_ascii=False) + "\n" for x in out), encoding="utf-8")
    print(json.dumps({"cases_adjudicated": len(out), "rows_pending": pending, "written": str(p), "at": time.strftime("%Y-%m-%dT%H:%M:%S")}))


if __name__ == "__main__":
    cmd = sys.argv[1] if len(sys.argv) > 1 else ""
    {"freeze-v1": freeze_v1, "export-v2-sheet": export_v2_sheet}.get(cmd, lambda: import_v2(sys.argv[2]) if cmd == "import-v2" else print(__doc__))()
