"""Hybrid retrieval: BM25 (exact terminology + concept tokens) and dense (multilingual-e5-small,
stored in Qdrant), fused with reciprocal rank fusion.

Scores are ranking signals, not clinical confidence probabilities.
"""
from __future__ import annotations

import logging
import math
import time
from dataclasses import dataclass, field
from pathlib import Path

from rank_bm25 import BM25Okapi

from .config import EMBED_MODEL_ID, EMBED_MODEL_REVISION, settings
from .corpus.store import CorpusStore
from .schemas import Passage
from .terms import Terminology, tokenize_for_bm25

log = logging.getLogger(__name__)

RRF_K = 60


def passage_doc_tokens(p: Passage) -> list[str]:
    toks = tokenize_for_bm25(p.text_iast)
    toks += [f"c:{c}" for c in p.concepts for _ in range(2)]  # concept tags (curated patterns)
    return toks


def passage_embed_text(p: Passage, terms: Terminology) -> str:
    """Derived text for dense indexing: original IAST + English labels of tagged concepts.
    Labels come from the curated terminology table, not from a model."""
    labels = []
    for cid in p.concepts:
        c = terms.by_id(cid)
        if c:
            labels.append(c.label.get("en", cid))
    return "passage: " + p.text_iast + (" | concepts: " + "; ".join(labels) if labels else "")


@dataclass
class Hit:
    passage: Passage
    bm25_rank: int | None = None
    bm25_score: float = 0.0
    dense_rank: int | None = None
    dense_score: float = 0.0
    fused: float = 0.0
    matched_concepts: list[str] = field(default_factory=list)

    def as_dict(self) -> dict:
        return {
            "bm25_rank": self.bm25_rank, "bm25_score": round(self.bm25_score, 3),
            "dense_rank": self.dense_rank, "dense_score": round(self.dense_score, 4),
            "rrf": round(self.fused, 5), "note": "ranking signals, not confidence",
        }


class Embedder:
    _instance = None

    def __init__(self):
        from sentence_transformers import SentenceTransformer

        self.model = SentenceTransformer(EMBED_MODEL_ID, revision=EMBED_MODEL_REVISION, device="cpu")
        self.model.max_seq_length = 512

    @classmethod
    def get(cls) -> "Embedder":
        if cls._instance is None:
            cls._instance = Embedder()
        return cls._instance

    def encode(self, texts: list[str]):
        return self.model.encode(texts, normalize_embeddings=True, batch_size=32, show_progress_bar=False)


class DenseIndex:
    def __init__(self, store: CorpusStore, terms: Terminology, path: Path | None = None):
        from qdrant_client import QdrantClient
        from qdrant_client.models import Distance, PointStruct, VectorParams

        self.collection = "passages_" + store.corpus_version().replace("corpus-", "")
        if settings.qdrant_url:
            self.client = QdrantClient(url=settings.qdrant_url, timeout=30)
        else:
            path = path or settings.qdrant_path
            path.mkdir(parents=True, exist_ok=True)
            self.client = QdrantClient(path=str(path))
        self.ids: list[str] = []
        passages = store.indexed_passages()
        self.ids = [p.passage_id for p in passages]
        existing = {c.name for c in self.client.get_collections().collections}
        if self.collection not in existing:
            emb = Embedder.get().encode([passage_embed_text(p, terms) for p in passages])
            self.client.create_collection(self.collection, vectors_config=VectorParams(size=emb.shape[1], distance=Distance.COSINE))
            self.client.upsert(self.collection, points=[
                PointStruct(id=i, vector=emb[i].tolist(), payload={"passage_id": passages[i].passage_id})
                for i in range(len(passages))
            ])

    def search(self, query: str, limit: int) -> list[tuple[str, float]]:
        vec = Embedder.get().encode(["query: " + query])[0].tolist()
        res = self.client.query_points(self.collection, query=vec, limit=limit).points
        return [(r.payload["passage_id"], float(r.score)) for r in res]


class Retriever:
    def __init__(self, store: CorpusStore, terms: Terminology, enable_dense: bool | None = None,
                 qdrant_path: Path | None = None):
        self.store = store
        self.terms = terms
        self.passages = store.indexed_passages()
        self.by_id = {p.passage_id: p for p in self.passages}
        self.bm25 = BM25Okapi([passage_doc_tokens(p) for p in self.passages]) if self.passages else None
        self.dense: DenseIndex | None = None
        self.dense_error: str | None = None
        want_dense = settings.enable_dense if enable_dense is None else enable_dense
        if want_dense and self.passages:
            try:
                self.dense = DenseIndex(store, terms, qdrant_path)
            except Exception as e:  # dense is optional; BM25 still works
                log.exception("dense index unavailable")
                self.dense_error = f"{type(e).__name__}: {e}"

    def bm25_search(self, query_text: str, concept_ids: list[str], limit: int) -> list[tuple[str, float]]:
        if not self.bm25:
            return []
        toks = tokenize_for_bm25(query_text) + [f"c:{c}" for c in concept_ids for _ in range(2)]
        if not toks:
            return []
        scores = self.bm25.get_scores(toks)
        order = sorted(range(len(scores)), key=lambda i: -scores[i])
        return [(self.passages[i].passage_id, float(scores[i])) for i in order[:limit] if scores[i] > 0]

    def search(self, query_text: str, concept_ids: list[str], dense_query: str, limit: int = 8,
               mode: str = "hybrid", source_filter: list[str] | None = None) -> tuple[list[Hit], dict]:
        t0 = time.perf_counter()
        pool = max(limit * 4, 30)
        bm = self.bm25_search(query_text, concept_ids, pool) if mode in ("hybrid", "bm25") else []
        t1 = time.perf_counter()
        dn: list[tuple[str, float]] = []
        if mode in ("hybrid", "dense") and self.dense is not None:
            dn = self.dense.search(dense_query, pool)
        t2 = time.perf_counter()
        hits: dict[str, Hit] = {}
        for r, (pid, s) in enumerate(bm):
            h = hits.setdefault(pid, Hit(self.by_id[pid]))
            h.bm25_rank, h.bm25_score = r + 1, s
            h.fused += 1.0 / (RRF_K + r + 1)
        for r, (pid, s) in enumerate(dn):
            if pid not in self.by_id:
                continue
            h = hits.setdefault(pid, Hit(self.by_id[pid]))
            h.dense_rank, h.dense_score = r + 1, s
            h.fused += 1.0 / (RRF_K + r + 1)
        out = [h for h in hits.values() if not source_filter or h.passage.source_id in source_filter]
        for h in out:
            h.matched_concepts = [c for c in concept_ids if c in h.passage.concepts]
        out.sort(key=lambda h: -h.fused)
        # de-duplicate identical texts (same verse repeated in a source)
        seen, dedup = set(), []
        for h in out:
            if h.passage.text_hash in seen:
                continue
            seen.add(h.passage.text_hash)
            dedup.append(h)
        info = {
            "mode": mode if (mode != "hybrid" or self.dense) else "bm25 (dense unavailable)",
            "bm25_candidates": len(bm), "dense_candidates": len(dn),
            "bm25_ms": round((t1 - t0) * 1000, 1), "dense_ms": round((t2 - t1) * 1000, 1),
            "dense_error": self.dense_error,
        }
        return dedup[:limit], info


def answerability(hits: list[Hit], concept_ids: list[str], min_concept_hits: int = 1,
                  min_bm25: float = 6.0) -> tuple[bool, str]:
    """Heuristic gate; min_bm25=6.0 chosen on the DEV split (eval_retrieval_ablation_dev_20261107_233535:
    lowest threshold that abstained on 7/7 dev unanswerables while keeping 20/22 dev answerables). Requires that at
    least one top passage carries a queried domain concept AND has a non-trivial BM25 score.
    Pure-dense similarity alone never makes a question 'answerable'."""
    if not hits:
        return False, "no passages retrieved"
    if not concept_ids:
        return False, "query did not map to any curated domain concept in the indexed module"
    top = hits[:5]
    good = [h for h in top if set(h.matched_concepts) & set(concept_ids) and h.bm25_score >= min_bm25]
    if len(good) < min_concept_hits:
        return False, "no top passage contains the queried concepts with sufficient lexical support"
    return True, f"{len(good)} of top {len(top)} passages contain queried concepts"


def entropy_like(xs: list[float]) -> float:
    s = sum(xs) or 1.0
    return -sum((x / s) * math.log(x / s) for x in xs if x > 0)
