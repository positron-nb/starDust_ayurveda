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


def fresh() -> dict:
    """Evaluate the default configuration on the reviewer-authored locked benchmark."""
    d = REPO_ROOT / "eval" / "fresh_benchmark"
    qf, lock = d / "questions.jsonl", d / "LOCK"
    if not qf.exists() or not lock.exists():
        raise SystemExit("no locked benchmark yet: the reviewer must write questions.csv, then run scripts/benchmark_lock.py")
    rows = [json.loads(l) for l in qf.read_text(encoding="utf-8").splitlines() if l.strip()]
    blob = "".join(json.dumps(r, ensure_ascii=False, sort_keys=True) for r in rows if r["split"] == "test")
    if hashlib.sha256(blob.encode("utf-8")).hexdigest() != json.loads(lock.read_text())["test_sha256"]:
        raise SystemExit("locked test split was modified after locking — refusing to report")
    store = CorpusStore(settings.corpus_db)
    terms, policy = load_terminology(), load_policy()
    retr = Retriever(store, terms)
    if retr.dense is None:
        raise SystemExit("dense index unavailable; refusing to report a degraded run")
    eng = Engine(store, terms, policy, LLMAdapter(), retr)
    out = {}
    for split in ("dev", "test"):
        cases = [{"case_id": r["question_id"], "query": r["question"], "lang": "hi" if r["language"] == "hi" else "en",
                  "expected": {"relevant_passages": r["gold"] + r["acceptable"]}} for r in rows
                 if r["split"] == split and r["coverage"] == "indexed" and r["gold"]]
        if cases:
            res = evaluate(eng, cases, "hybrid")
            # Hit@5 counts gold OR acceptable; Recall@5 is reported against the strict gold list too
            strict = [len(set(pc["ranked"][:5]) & set(r["gold"])) / len(r["gold"])
                      for pc, r in zip(res["per_case"], [x for x in rows if x["split"] == split and x["coverage"] == "indexed" and x["gold"]])]
            res["strict_gold_recall_at_5"] = round(statistics.mean(strict), 4)
            out[split] = res
    p = REPO_ROOT / "eval" / "results" / f"retrieval_fresh_{time.strftime('%Y%m%d_%H%M%S')}.json"
    p.write_text(json.dumps({"git_commit": git_commit(), "lock": json.loads(lock.read_text()), "results": out}, ensure_ascii=False, indent=1), encoding="utf-8")
    print("WROTE", p, {k: (v["hit_at_5"], v["strict_gold_recall_at_5"], v["n"]) for k, v in out.items()})
    return out


MATRIX = [
    # name, query views, rerank
    ("E1-A baseline", (), False),
    ("E1-B transliteration only", ("translit",), False),
    ("E1-C roman lexicon only", ("roman_lexicon",), False),
    ("E1-D translit + roman lexicon", ("translit", "roman_lexicon"), False),
    ("E2-C rerank only", (), True),
    ("E2-D normalization + rerank", ("translit", "roman_lexicon"), True),
]


def _lang_of(c: dict) -> str:
    if c.get("variant"):
        return {"en": "en", "hi": "hi", "hinglish": "hinglish"}[c["variant"]]
    if c["case_id"].endswith("tr"):
        return "hinglish"
    return "hi" if c["lang"] == "hi" else "en"


def _metrics(rows: list[dict]) -> dict:
    import math
    if not rows:
        return {"n": 0}
    hit = sum(r["hit"] for r in rows)
    ndcg = []
    for r in rows:
        dcg = sum(1 / math.log2(i + 2) for i, p in enumerate(r["top5"]) if p in r["gold"])
        ideal = sum(1 / math.log2(i + 2) for i in range(min(5, len(r["gold"]))))
        ndcg.append(dcg / ideal)
    return {"n": len(rows), "hit_at_5": f"{hit}/{len(rows)}", "hit_rate": round(hit / len(rows), 4),
            "recall_at_5": round(statistics.mean(r["recall"] for r in rows), 4),
            "mrr_at_5": round(statistics.mean(r["rr5"] for r in rows), 4), "ndcg_at_5": round(statistics.mean(ndcg), 4)}


def matrix(only: list[str] | None = None) -> dict:
    from ..terms import with_views
    store = CorpusStore(settings.corpus_db)
    base_terms, policy = load_terminology(), load_policy()
    sets, dhash = load_sets()
    indic_rows = [json.loads(l) for l in (REPO_ROOT / "eval" / "indic_cases.jsonl").read_text(encoding="utf-8").splitlines() if l.strip()]
    unans = [json.loads(l) for l in CASES.read_text(encoding="utf-8").splitlines() if l.strip()]
    unans = [c for c in unans if c["category"] == "unanswerable"]
    pops = {"devA": sets["devA"], "devB": sets["devB"],
            "indic": [{"case_id": r["case_id"], "query": r["query"], "lang": r["lang"], "variant": r["variant"],
                       "expected": {"relevant_passages": r["gold"]}} for r in indic_rows if r["gold"]]}
    ooc = [{"case_id": c["case_id"], "query": c["query"], "lang": c["lang"]} for c in unans] + \
          [{"case_id": r["case_id"], "query": r["query"], "lang": r["lang"], "variant": r["variant"]} for r in indic_rows if not r["gold"]]
    results = []
    for name, views, rerank in MATRIX:
        if only and not any(name.startswith(o) for o in only):
            continue
        terms = with_views(base_terms, views)
        cfg = RetrievalConfig(**{**DEFAULT_CONFIG.as_dict(), "rerank": rerank})
        retr = Retriever(store, terms, config=cfg)
        if retr.dense is None:
            raise SystemExit(f"{name}: dense index unavailable ({retr.dense_error})")
        eng = Engine(store, terms, policy, LLMAdapter(), retr)
        per, lat = {}, []
        for pop, cases in pops.items():
            rows = []
            for c in cases:
                t = time.perf_counter()
                r = eng.run(QueryRequest(query=c["query"], lang=c["lang"], use_model=False))
                lat.append((time.perf_counter() - t) * 1000)
                ranked = [e.passage.passage_id for e in r.evidence if e.role == "primary"]
                gold = c["expected"]["relevant_passages"]
                rows.append({"case_id": c["case_id"], "lang": _lang_of(c), "gold": gold, "top5": ranked[:5],
                             "hit": any(p in gold for p in ranked[:5]), "recall": len(set(ranked[:5]) & set(gold)) / len(gold),
                             "rr5": next((1 / (i + 1) for i, p in enumerate(ranked[:5]) if p in gold), 0.0), "status": r.status})
            per[pop] = {"all": _metrics(rows), **{f"lang_{l}": _metrics([x for x in rows if x["lang"] == l]) for l in ("en", "hi", "hinglish")},
                        "cases": rows}
        fa = []
        for c in ooc:
            r = eng.run(QueryRequest(query=c["query"], lang=c["lang"], use_model=False))
            fa.append({"case_id": c["case_id"], "status": r.status, "concepts": list(r.normalized_query["concepts_direct"])})
        n_fa = sum(x["status"] != "insufficient_evidence" for x in fa)
        lat.sort()
        res = {"experiment": name, "views": list(views), "rerank": rerank, "populations": per,
               "out_of_corpus_false_answerable": f"{n_fa}/{len(fa)}", "out_of_corpus": fa,
               "latency_p50_ms": round(lat[len(lat) // 2], 1), "latency_p95_ms": round(lat[int(0.95 * (len(lat) - 1))], 1)}
        results.append(res)
        a, b, ind = per["devA"]["all"], per["devB"]["all"], per["indic"]
        print(f"{name:32s} devA {a['hit_at_5']} R@5 {a['recall_at_5']} | devB {b['hit_at_5']} R@5 {b['recall_at_5']} nDCG {b['ndcg_at_5']} | "
              f"indic en {ind['lang_en']['hit_at_5']} hi {ind['lang_hi']['hit_at_5']} hinglish {ind['lang_hinglish']['hit_at_5']} | "
              f"OOC false-ans {res['out_of_corpus_false_answerable']} | p50 {res['latency_p50_ms']} p95 {res['latency_p95_ms']} ms", flush=True)
    import torch
    out = {"kind": "retrieval_matrix", "created_at": time.strftime("%Y-%m-%dT%H:%M:%S"), "git_commit": git_commit(),
           "corpus_version": store.corpus_version(), "terms_version": base_terms.version, "dataset_hash": dhash,
           "reranker": "BAAI/bge-reranker-v2-m3 @ 953dc6f, fp16 on " + ("cuda" if torch.cuda.is_available() else "cpu"),
           "note": "All populations inspected/development data; roman lexicon is unreviewed (pending). Not held-out results.",
           "results": results}
    p = REPO_ROOT / "eval" / "results" / f"retrieval_matrix_{time.strftime('%Y%m%d_%H%M%S')}.json"
    p.write_text(json.dumps(out, ensure_ascii=False, indent=1), encoding="utf-8")
    print("WROTE", p)
    return out


def candidate_pool_recall(depths=(30, 60)) -> dict:
    """Is the gold passage even in the candidate pool? (upper bound for any reranker)
    Pool@k = union of BM25 top-k and dense top-k (deduplicated), using the production query views."""
    store = CorpusStore(settings.corpus_db)
    terms, policy = load_terminology(), load_policy()
    retr = Retriever(store, terms)
    if retr.dense is None:
        raise SystemExit("dense index unavailable")
    eng = Engine(store, terms, policy, LLMAdapter(), retr)
    sets, dhash = load_sets()
    out = {"git_commit": git_commit(), "dataset_hash": dhash, "corpus_version": store.corpus_version()}
    for split, cases in sets.items():
        rec = {k: [] for k in depths}
        rec5 = []
        sizes = {k: [] for k in depths}
        for c in cases:
            r = eng.run(QueryRequest(query=c["query"], lang=c["lang"], use_model=False))
            direct = list(r.normalized_query["concepts_direct"])
            q = c["query"] + " " + (r.normalized_query.get("iast_transliteration") or "") + " " + " ".join(terms.expansion_terms(direct))
            dq = c["query"] + " " + " ".join(terms.by_id(x).label.get("en", "") for x in direct if terms.by_id(x))
            gold = c["expected"]["relevant_passages"]
            top5 = [e.passage.passage_id for e in r.evidence if e.role == "primary"][:5]
            rec5.append(len(set(top5) & set(gold)) / len(gold))
            for k in depths:
                pool = {p for p, _ in retr.bm25_search(q, direct, k)} | {p for p, _ in retr.dense.search(dq, k)}
                sizes[k].append(len(pool))
                rec[k].append(len(pool & set(gold)) / len(gold))
        out[split] = {"n": len(cases), "recall_at_5_final": round(statistics.mean(rec5), 4),
                      **{f"candidate_recall_pool{k}": round(statistics.mean(rec[k]), 4) for k in depths},
                      **{f"mean_pool_size{k}": round(statistics.mean(sizes[k]), 1) for k in depths}}
    p = REPO_ROOT / "eval" / "results" / f"retrieval_pool_{time.strftime('%Y%m%d_%H%M%S')}.json"
    p.write_text(json.dumps(out, indent=1), encoding="utf-8")
    print("WROTE", p)
    print(json.dumps(out, indent=1))
    return out


def indic(use_model: bool = False) -> dict:
    """EN / Hindi (Devanagari) / Roman-Hinglish triplets of the same intent (eval/indic_cases.jsonl).
    Reports retrieval per variant and agreement ACROSS variants of one intent (status, top-5 overlap)."""
    rows = [json.loads(l) for l in (REPO_ROOT / "eval" / "indic_cases.jsonl").read_text(encoding="utf-8").splitlines() if l.strip()]
    store = CorpusStore(settings.corpus_db)
    terms, policy = load_terminology(), load_policy()
    retr = Retriever(store, terms)
    if retr.dense is None:
        raise SystemExit("dense index unavailable; refusing to report a degraded run")
    from ..llm import make_adapter
    eng = Engine(store, terms, policy, make_adapter() if use_model else LLMAdapter(), retr)
    res = {}
    for r in rows:
        x = eng.run(QueryRequest(query=r["query"], lang=r["lang"], use_model=use_model))
        ranked = [e.passage.passage_id for e in x.evidence if e.role == "primary"]
        res[r["case_id"]] = {**r, "status": x.status, "top5": ranked[:5], "concepts": list(x.normalized_query["concepts_direct"]),
                             "hit_at_5": (any(p in r["gold"] for p in ranked[:5]) if r["gold"] else None),
                             "recall_at_5": (len(set(ranked[:5]) & set(r["gold"])) / len(r["gold"]) if r["gold"] else None),
                             "shown_claims": sum(1 for c in x.claims if c.claim_type == "interpretation"),
                             "inference_ran": x.trace.inference_ran}
    by_v = {}
    for v in ("en", "hi", "hinglish"):
        xs = [c for c in res.values() if c["variant"] == v and c["gold"]]
        un = [c for c in res.values() if c["variant"] == v and not c["gold"]]
        by_v[v] = {"n_answerable": len(xs), "hit_at_5": f"{sum(c['hit_at_5'] for c in xs)}/{len(xs)}",
                   "mean_recall_at_5": round(statistics.mean(c["recall_at_5"] for c in xs), 3) if xs else None,
                   "out_of_corpus_abstained": f"{sum(c['status'] == 'insufficient_evidence' for c in un)}/{len(un)}"}
    intents = sorted({c["intent"] for c in res.values()})
    agree, jac_hi, jac_hl = 0, [], []
    for i in intents:
        e, h, l = (res[f"{i}-{v}"] for v in ("en", "hi", "hinglish"))
        agree += (e["status"] == h["status"] == l["status"])
        for other, acc in ((h, jac_hi), (l, jac_hl)):
            a, b = set(e["top5"]), set(other["top5"])
            acc.append(len(a & b) / len(a | b) if a | b else 1.0)
    out = {"git_commit": git_commit(), "created_at": time.strftime("%Y-%m-%dT%H:%M:%S"), "use_model": use_model,
           "n_cases": len(rows), "n_intents": len(intents), "by_variant": by_v,
           "status_agreement_all_three": f"{agree}/{len(intents)}",
           "top5_jaccard_en_vs_hi": round(statistics.mean(jac_hi), 3), "top5_jaccard_en_vs_hinglish": round(statistics.mean(jac_hl), 3),
           "note": "Candidate cases written by the build assistant, not by native speakers; labels unreviewed.", "cases": list(res.values())}
    p = REPO_ROOT / "eval" / "results" / f"indic_eval_{'model' if use_model else 'retrieval'}_{time.strftime('%Y%m%d_%H%M%S')}.json"
    p.write_text(json.dumps(out, ensure_ascii=False, indent=1), encoding="utf-8")
    print("WROTE", p)
    print(json.dumps({k: v for k, v in out.items() if k != "cases"}, ensure_ascii=False, indent=1))
    return out


if __name__ == "__main__":
    cmd = sys.argv[1] if len(sys.argv) > 1 else "experiments"
    if cmd == "matrix":
        matrix(sys.argv[2:] or None)
    elif cmd == "pool":
        candidate_pool_recall()
    elif cmd == "indic":
        indic(use_model="--model" in sys.argv)
    elif cmd == "fresh":
        fresh()
    elif cmd == "failures":
        failures()
    else:
        run_experiments(sys.argv[2:] or None)
