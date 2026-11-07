"""Application database: cached runs and the append-only human review log.

No patient identifiers are stored: case text is kept only inside the run record of the local
instance (deletable via /api/admin/reset or per-run delete), and logs never contain it.
"""
from __future__ import annotations

import json
import sqlite3
import threading
from pathlib import Path

from .schemas import ReviewAction, RunResult

SCHEMA = """
CREATE TABLE IF NOT EXISTS runs (
    run_id TEXT PRIMARY KEY, cache_key TEXT NOT NULL, created_at TEXT NOT NULL, session_id TEXT,
    corpus_version TEXT NOT NULL, json TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_runs_cache ON runs(cache_key);
CREATE TABLE IF NOT EXISTS reviews (
    review_id INTEGER PRIMARY KEY AUTOINCREMENT, created_at TEXT NOT NULL, target_type TEXT NOT NULL,
    target_id TEXT NOT NULL, run_id TEXT, decision TEXT NOT NULL, note TEXT, reviewer_name TEXT NOT NULL,
    reviewer_role TEXT NOT NULL, previous_decision TEXT
);
CREATE TABLE IF NOT EXISTS eval_runs (
    eval_id TEXT PRIMARY KEY, created_at TEXT NOT NULL, config TEXT NOT NULL, json TEXT NOT NULL
);
"""


class AppDB:
    def __init__(self, path: Path):
        path.parent.mkdir(parents=True, exist_ok=True)
        self.path = path
        self.conn = sqlite3.connect(str(path), check_same_thread=False)
        self.conn.executescript(SCHEMA)
        self.lock = threading.Lock()

    def save_run(self, r: RunResult, session_id: str | None = None) -> None:
        with self.lock:
            self.conn.execute("INSERT OR REPLACE INTO runs VALUES (?,?,?,?,?,?)",
                              (r.run_id, r.trace.cache_key, r.trace.created_at, session_id, r.trace.corpus_version,
                               r.model_dump_json()))
            self.conn.commit()

    def get_run(self, run_id: str) -> RunResult | None:
        row = self.conn.execute("SELECT json FROM runs WHERE run_id=?", (run_id,)).fetchone()
        return RunResult.model_validate_json(row[0]) if row else None

    def cached(self, cache_key: str) -> RunResult | None:
        row = self.conn.execute("SELECT json FROM runs WHERE cache_key=? ORDER BY created_at DESC LIMIT 1", (cache_key,)).fetchone()
        return RunResult.model_validate_json(row[0]) if row else None

    def invalidate_corpus(self, keep_version: str) -> int:
        with self.lock:
            n = self.conn.execute("DELETE FROM runs WHERE corpus_version != ?", (keep_version,)).rowcount
            self.conn.commit()
            return n

    def list_runs(self, limit: int = 50, session_id: str | None = None) -> list[dict]:
        q = "SELECT json FROM runs" + (" WHERE session_id=?" if session_id else "") + " ORDER BY created_at DESC LIMIT ?"
        args = (session_id, limit) if session_id else (limit,)
        out = []
        for (js,) in self.conn.execute(q, args):
            d = json.loads(js)
            out.append({"run_id": d["run_id"], "query": d["query"][:120], "status": d["status"], "lang": d["lang"],
                        "created_at": d["trace"]["created_at"], "inference_ran": d["trace"]["inference_ran"],
                        "llm_mode": d["trace"]["llm_mode"], "n_claims": len(d["claims"]),
                        "n_interpretation_claims": sum(1 for c in d["claims"] if c["claim_type"] == "interpretation")})
        return out

    def delete_run(self, run_id: str) -> None:
        with self.lock:
            self.conn.execute("DELETE FROM runs WHERE run_id=?", (run_id,))
            self.conn.commit()

    def add_review(self, a: ReviewAction, created_at: str) -> int:
        with self.lock:
            prev = self.conn.execute(
                "SELECT decision FROM reviews WHERE target_type=? AND target_id=? AND decision!='comment' ORDER BY review_id DESC LIMIT 1",
                (a.target_type, a.target_id)).fetchone()
            cur = self.conn.execute(
                "INSERT INTO reviews (created_at,target_type,target_id,run_id,decision,note,reviewer_name,reviewer_role,previous_decision) VALUES (?,?,?,?,?,?,?,?,?)",
                (created_at, a.target_type, a.target_id, a.run_id, a.decision, a.note[:2000], a.reviewer_name, a.reviewer_role,
                 prev[0] if prev else None))
            self.conn.commit()
            return int(cur.lastrowid)

    def reviews(self, target_type: str | None = None, target_id: str | None = None) -> list[dict]:
        q, args = "SELECT * FROM reviews", []
        cond = []
        if target_type:
            cond.append("target_type=?")
            args.append(target_type)
        if target_id:
            cond.append("target_id=?")
            args.append(target_id)
        if cond:
            q += " WHERE " + " AND ".join(cond)
        q += " ORDER BY review_id DESC"
        cols = [c[0] for c in self.conn.execute("SELECT * FROM reviews LIMIT 0").description]
        return [dict(zip(cols, r)) for r in self.conn.execute(q, args)]

    def latest_decisions(self, target_type: str) -> dict[str, dict]:
        out = {}
        for r in reversed(self.reviews(target_type)):
            if r["decision"] != "comment":
                out[r["target_id"]] = r
        return out

    def save_eval(self, eval_id: str, created_at: str, config: str, payload: dict) -> None:
        with self.lock:
            self.conn.execute("INSERT OR REPLACE INTO eval_runs VALUES (?,?,?,?)", (eval_id, created_at, config, json.dumps(payload, ensure_ascii=False)))
            self.conn.commit()

    def reset(self, keep_reviews: bool = True) -> None:
        with self.lock:
            self.conn.execute("DELETE FROM runs")
            if not keep_reviews:
                self.conn.execute("DELETE FROM reviews")
            self.conn.commit()
