"""Expert validation of PRAMAAN answers (Phase 2): generate live answers, then build rating sheets.

    python scripts/expert_validation.py generate     # needs model_server/server.py running (live AyurParam)
    python scripts/expert_validation.py sheets       # builds the rater workbooks from the newest answers file

Each of the 50 questions in eval/expert_validation/questions.jsonl is run through the full pipeline
(live AyurParam, hybrid retrieval, ledger, safety). The answers file records exactly what a user saw:
the shown explanation sentences with their cited verse, and the evidence list in display order.
Two raters (our clinical lead and an external Ayurveda expert) rate the same 50 answers independently.
"""
from __future__ import annotations

import datetime as dt
import json
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))
OUT = ROOT / "eval" / "expert_validation"


def generate() -> Path:
    from pramaan.config import settings
    from pramaan.corpus.store import CorpusStore
    from pramaan.llm import HTTPAdapter
    from pramaan.pipeline import Engine
    from pramaan.retrieval import Retriever
    from pramaan.safety import load_policy
    from pramaan.schemas import QueryRequest
    from pramaan.terms import load_terminology

    llm = HTTPAdapter(record=False)
    if not llm.health().get("available"):
        raise SystemExit("AyurParam model server not available; start model_server/server.py first")
    store = CorpusStore(settings.corpus_db)
    terms, policy = load_terminology(), load_policy()
    eng = Engine(store, terms, policy, llm, Retriever(store, terms))
    qs = [json.loads(line) for line in (OUT / "questions.jsonl").read_text(encoding="utf-8").splitlines() if line.strip()]
    rows = []
    for q in qs:
        t = time.perf_counter()
        r = eng.run(QueryRequest(query=q["query"], lang=q["lang"], use_model=True))
        by_label = {c.label: c for c in r.evidence}
        shown = [{"text": c.text, "cites": c.evidence_labels,
                  "passages": [by_label[lbl].passage.passage_id for lbl in c.evidence_labels if lbl in by_label]}
                 for c in r.claims if c.claim_type == "interpretation"]
        rows.append({**q, "status": r.status, "inference_ran": r.trace.inference_ran,
                     "seconds": round(time.perf_counter() - t, 1), "notice": r.answer_notice,
                     "shown": shown, "withheld": len(r.rejected_claims),
                     "evidence": [{"label": c.label, "passage_id": c.passage.passage_id, "role": c.role,
                                   "locator": f"{c.passage.work}, {c.passage.verse_label}",
                                   "iast": c.passage.text_iast, "deva": c.passage.text_deva,
                                   "note": c.role_note or ""} for c in r.evidence]})
        print(f"{q['qid']} {r.status:<22} shown={len(shown)} withheld={len(r.rejected_claims)} {rows[-1]['seconds']}s", flush=True)
    meta = {"created_at": dt.datetime.now(dt.timezone.utc).isoformat(), "corpus_version": store.corpus_version(),
            "model": llm.health(), "n": len(rows), "n_live_inference": sum(x["inference_ran"] for x in rows)}
    f = OUT / f"answers_{dt.datetime.now():%Y%m%d_%H%M%S}.json"
    f.write_text(json.dumps({"meta": meta, "answers": rows}, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f)
    return f


if __name__ == "__main__":
    cmd = sys.argv[1] if len(sys.argv) > 1 else ""
    if cmd == "generate":
        generate()
    elif cmd == "sheets":
        from expert_sheets import build  # noqa: E402  (scripts/expert_sheets.py)
        build()
    else:
        raise SystemExit(__doc__)
