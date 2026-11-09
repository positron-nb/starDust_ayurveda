"""Controlled retrieval experiments (no AyurParam; retrieval path of the production Engine).

    python -m pramaan.eval.retrieval_lab experiments      # grid → eval/results/retrieval_exp_<ts>.json
    python -m pramaan.eval.retrieval_lab failures         # miss diagnostics for the default config

Populations (all INSPECTED, therefore development data):
  devA = original dev split (22 answerable+multilingual cases) — used to SELECT configurations
  devB = former held-out test split (38 cases) — inspected on 2026-11-07, reported only as a check
A fresh, reviewer-authored locked set is required for any held-out claim (eval/fresh_benchmark/).
Metric definitions: Hit@5 = ≥1 gold passage among the first 5 primary evidence cards;
passage Recall@5 = |gold ∩ top5| / |gold|, averaged over cases (max < 1 when |gold| > 5);
MRR over the full ranked list.
"""
from __future__ import annotations

import hashlib
import json
import platform
import statistics
import subprocess
import sys
import time

from ..config import REPO_ROOT, settings
from ..corpus.store import CorpusStore
from ..llm import LLMAdapter
from ..pipeline import Engine
from ..retrieval import DEFAULT_CONFIG, RetrievalConfig, Retriever
from ..safety import load_policy
from ..schemas import QueryRequest
from ..terms import load_terminology

CASES = REPO_ROOT / "eval" / "cases.jsonl"

GRID: list[tuple[str, dict, str]] = [
    ("B0 default hybrid", {}, "hybrid"),
    ("B1 BM25 only", {}, "bm25"),
    ("B2 dense only", {}, "dense"),
    ("R1 RRF k=20", {"rrf_k": 20}, "hybrid"),
    ("R2 RRF k=100", {"rrf_k": 100}, "hybrid"),
    ("K1 BM25 k1=1.2", {"bm25_k1": 1.2}, "hybrid"),
    ("K2 BM25 k1=2.0", {"bm25_k1": 2.0}, "hybrid"),
    ("K3 BM25 b=0.5", {"bm25_b": 0.5}, "hybrid"),
    ("K4 BM25 b=0.9", {"bm25_b": 0.9}, "hybrid"),
    ("C1 concept weight 1", {"concept_weight": 1}, "hybrid"),
    ("C4 concept weight 4", {"concept_weight": 4}, "hybrid"),
    ("W1 weighted RRF bm25×2", {"w_bm25": 2.0}, "hybrid"),
    ("W2 weighted RRF dense×2", {"w_dense": 2.0}, "hybrid"),
    ("P1 candidate pool 60", {"pool_min": 60}, "hybrid"),
    ("N1 next-verse expansion (top 2)", {"neighbour_expand": 1, "neighbour_top": 2}, "hybrid"),
    ("N2 next-verse expansion (top 1)", {"neighbour_expand": 1, "neighbour_top": 1}, "hybrid"),
    ("D1 dense text without concept labels", {"embed_concept_labels": False}, "hybrid"),
    ("I1 inherit previous-verse concepts ×1", {"inherit_prev_concepts": 1}, "hybrid"),
    ("I2 inherit previous-verse concepts ×2", {"inherit_prev_concepts": 2}, "hybrid"),
    ("I1N2 inherit ×1 + next-verse expansion (top 1)", {"inherit_prev_concepts": 1, "neighbour_expand": 1, "neighbour_top": 1}, "hybrid"),
]


def load_sets():
    cs = [json.loads(l) for l in CASES.read_text(encoding="utf-8").splitlines() if l.strip()]
    cs = [c for c in cs if c["expected"].get("relevant_passages")]
    blob = json.dumps(cs, ensure_ascii=False, sort_keys=True).encode()
    return ({"devA": [c for c in cs if c["split"] == "dev"], "devB": [c for c in cs if c["split"] == "test"]},
            hashlib.sha256(blob).hexdigest()[:16])


def evaluate(eng: Engine, cases: list[dict], mode: str) -> dict:
    hits, recs, rrs, lat, per = 0, [], [], [], []
    for c in cases:
        t = time.perf_counter()
        r = eng.run(QueryRequest(query=c["query"], lang=c["lang"], use_model=False, retrieval_mode=mode))
        lat.append((time.perf_counter() - t) * 1000)
        ranked = [e.passage.passage_id for e in r.evidence if e.role == "primary"]
        rel = c["expected"]["relevant_passages"]
        top = ranked[:5]
        h = any(p in rel for p in top)
        hits += h
        recs.append(len(set(top) & set(rel)) / len(rel))
        rrs.append(next((1 / (i + 1) for i, p in enumerate(ranked) if p in rel), 0.0))
        per.append({"case_id": c["case_id"], "hit": h, "ranked": ranked[:6], "gold": rel})
    n = len(cases)
    return {"n": n, "hit_at_5": round(hits / n, 4), "hits": hits, "passage_recall_at_5": round(statistics.mean(recs), 4),
            "mrr": round(statistics.mean(rrs), 4), "p50_ms": round(statistics.median(lat), 1),
            "max_possible_recall_at_5": round(statistics.mean(min(5, len(c["expected"]["relevant_passages"])) / len(c["expected"]["relevant_passages"]) for c in cases), 4),
            "per_case": per}


def git_commit() -> str:
    try:
        return subprocess.check_output(["git", "rev-parse", "--short", "HEAD"], cwd=REPO_ROOT, text=True).strip()
    except Exception:
        return "unknown"


def run_experiments(only: list[str] | None = None) -> dict:
    store = CorpusStore(settings.corpus_db)
    terms, policy = load_terminology(), load_policy()
    sets, dhash = load_sets()
    rows = []
    for name, overrides, mode in GRID:
        if only and not any(name.startswith(o) for o in only):
            continue
        cfg = RetrievalConfig(**{**DEFAULT_CONFIG.as_dict(), **overrides})
        retr = Retriever(store, terms, config=cfg)
        if mode != "bm25" and retr.dense is None:
            raise SystemExit(f"{name}: dense index unavailable ({retr.dense_error}); refusing to report a silently degraded run")
        eng = Engine(store, terms, policy, LLMAdapter(), retr)
        res = {k: evaluate(eng, v, mode) for k, v in sets.items()}
        rows.append({"experiment": name, "mode": mode, "config": cfg.as_dict(), **res})
        print(f"{name:40s} devA hit {res['devA']['hit_at_5']:.3f} R@5 {res['devA']['passage_recall_at_5']:.3f} | "
              f"devB hit {res['devB']['hit_at_5']:.3f} R@5 {res['devB']['passage_recall_at_5']:.3f} | p50 {res['devB']['p50_ms']} ms", flush=True)
    out = {"kind": "retrieval_experiments", "created_at": time.strftime("%Y-%m-%dT%H:%M:%S"), "git_commit": git_commit(),
           "corpus_version": store.corpus_version(), "terms_version": terms.version, "dataset": "eval/cases.jsonl (answerable+multilingual with gold)",
           "dataset_hash": dhash, "populations": {k: len(v) for k, v in sets.items()},
           "note": "devA used for selection; devB was inspected on 2026-11-07 and is NOT a held-out set. Gold labels are unreviewed AI candidates.",
           "hardware": f"{platform.processor()} | python {sys.version.split()[0]} | retrieval on CPU", "rows": rows}
    p = REPO_ROOT / "eval" / "results" / f"retrieval_exp_{time.strftime('%Y%m%d_%H%M%S')}.json"
    p.write_text(json.dumps(out, ensure_ascii=False, indent=1), encoding="utf-8")
    print("WROTE", p)
    return out


def failures() -> dict:
    """Diagnostics for each miss under the default config: gold ranks in each retriever's full list,
    concept overlap, corpus presence. Classification of causes is done by a human from this dump."""
    store = CorpusStore(settings.corpus_db)
    terms, policy = load_terminology(), load_policy()
    retr = Retriever(store, terms)
    eng = Engine(store, terms, policy, LLMAdapter(), retr)
    sets, _ = load_sets()
    out = []
    for split, cases in sets.items():
        for c in cases:
            r = eng.run(QueryRequest(query=c["query"], lang=c["lang"], use_model=False))
            ranked = [e.passage.passage_id for e in r.evidence if e.role == "primary"]
            rel = c["expected"]["relevant_passages"]
            direct = list(r.normalized_query["concepts_direct"])
            q = c["query"] + " " + (r.normalized_query.get("iast_transliteration") or "") + " " + " ".join(terms.expansion_terms(direct))
            bm = [pid for pid, _ in retr.bm25_search(q, direct, 600)]
            dn = [pid for pid, _ in retr.dense.search(c["query"], 600)] if retr.dense else []
            gold = []
            for g in rel:
                p = store.get(g)
                gold.append({"id": g, "indexed": g in retr.by_id, "bm25_rank": bm.index(g) + 1 if g in bm else None,
                             "dense_rank": dn.index(g) + 1 if g in dn else None,
                             "gold_concepts": p.concepts if p else [], "overlap": sorted(set(direct) & set(p.concepts if p else []))})
            out.append({"split": split, "case_id": c["case_id"], "lang": c["lang"], "query": c["query"], "query_concepts": direct,
                        "hit_at_5": any(p in rel for p in ranked[:5]), "recall_at_5": len(set(ranked[:5]) & set(rel)) / len(rel),
                        "top5": ranked[:5], "gold": gold, "status": r.status})
    p = REPO_ROOT / "eval" / "results" / f"retrieval_failures_{time.strftime('%Y%m%d_%H%M%S')}.json"
    p.write_text(json.dumps({"git_commit": git_commit(), "cases": out}, ensure_ascii=False, indent=1), encoding="utf-8")
    print("WROTE", p)
    return {"cases": out}


if __name__ == "__main__":
    cmd = sys.argv[1] if len(sys.argv) > 1 else "experiments"
    if cmd == "failures":
        failures()
    else:
        run_experiments(sys.argv[2:] or None)
