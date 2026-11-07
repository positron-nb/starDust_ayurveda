"""SQLite corpus store. The built corpus is read-only at runtime; the Integrity Lab works on
disposable copies (snapshots) of this file."""
from __future__ import annotations

import hashlib
import json
import shutil
import sqlite3
from pathlib import Path

from ..schemas import Gloss, Passage, Source

SCHEMA = """
CREATE TABLE IF NOT EXISTS meta (key TEXT PRIMARY KEY, value TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS sources (source_id TEXT PRIMARY KEY, json TEXT NOT NULL, file_sha256 TEXT);
CREATE TABLE IF NOT EXISTS passages (
    passage_id TEXT PRIMARY KEY, source_id TEXT NOT NULL, position INTEGER NOT NULL,
    indexed INTEGER NOT NULL DEFAULT 0, text_hash TEXT NOT NULL, json TEXT NOT NULL,
    revoked INTEGER NOT NULL DEFAULT 0
);
CREATE INDEX IF NOT EXISTS idx_passages_pos ON passages(source_id, position);
CREATE TABLE IF NOT EXISTS glosses (
    passage_id TEXT NOT NULL, lang TEXT NOT NULL, text TEXT NOT NULL, author TEXT NOT NULL,
    method TEXT NOT NULL, review_status TEXT NOT NULL, PRIMARY KEY (passage_id, lang)
);
"""


def sha256_text(s: str) -> str:
    return hashlib.sha256(s.encode("utf-8")).hexdigest()


def sha256_file(p: Path) -> str:
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


class CorpusStore:
    def __init__(self, path: Path):
        self.path = Path(path)
        self.conn = sqlite3.connect(str(self.path), check_same_thread=False)
        self.conn.executescript(SCHEMA)
        self._cache: dict[str, Passage] | None = None

    # ---- writing (build time / lab snapshots) ----
    def put_meta(self, key: str, value: str) -> None:
        self.conn.execute("INSERT OR REPLACE INTO meta VALUES (?, ?)", (key, value))

    def put_source(self, src: dict, file_sha256: str | None) -> None:
        self.conn.execute("INSERT OR REPLACE INTO sources VALUES (?, ?, ?)",
                          (src["source_id"], json.dumps(src, ensure_ascii=False), file_sha256))

    def put_passage(self, p: Passage, indexed: bool) -> None:
        self.conn.execute(
            "INSERT OR REPLACE INTO passages (passage_id, source_id, position, indexed, text_hash, json) VALUES (?,?,?,?,?,?)",
            (p.passage_id, p.source_id, p.position, int(indexed), p.text_hash,
             p.model_dump_json(exclude={"gloss"})),
        )

    def put_gloss(self, passage_id: str, g: Gloss) -> None:
        self.conn.execute("INSERT OR REPLACE INTO glosses VALUES (?,?,?,?,?,?)",
                          (passage_id, g.lang, g.text, g.author, g.method, g.review_status))

    def commit(self) -> None:
        self.conn.commit()
        self._cache = None

    # ---- reading ----
    def meta(self, key: str, default: str = "") -> str:
        r = self.conn.execute("SELECT value FROM meta WHERE key=?", (key,)).fetchone()
        return r[0] if r else default

    def sources(self) -> list[Source]:
        return [Source(**{k: v for k, v in json.loads(r[0]).items() if k in Source.model_fields})
                for r in self.conn.execute("SELECT json FROM sources")]

    def source_raw(self, source_id: str) -> dict | None:
        r = self.conn.execute("SELECT json, file_sha256 FROM sources WHERE source_id=?", (source_id,)).fetchone()
        if not r:
            return None
        d = json.loads(r[0])
        d["_file_sha256_at_build"] = r[1]
        return d

    def _gloss_map(self) -> dict[str, Gloss]:
        out = {}
        for pid, lang, text, author, method, rs in self.conn.execute("SELECT * FROM glosses"):
            if lang == "en":
                out[pid] = Gloss(lang=lang, text=text, author=author, method=method, review_status=rs)
        return out

    def indexed_passages(self) -> list[Passage]:
        if self._cache is None:
            gl = self._gloss_map()
            self._cache = {}
            for pid, js in self.conn.execute(
                "SELECT passage_id, json FROM passages WHERE indexed=1 AND revoked=0 ORDER BY source_id, position"
            ):
                p = Passage.model_validate_json(js)
                p.gloss = gl.get(pid)
                self._cache[pid] = p
        return list(self._cache.values())

    def get(self, passage_id: str, include_revoked: bool = False) -> Passage | None:
        q = "SELECT json FROM passages WHERE passage_id=?" + ("" if include_revoked else " AND revoked=0")
        r = self.conn.execute(q, (passage_id,)).fetchone()
        if not r:
            return None
        p = Passage.model_validate_json(r[0])
        g = self.conn.execute("SELECT text, author, method, review_status FROM glosses WHERE passage_id=? AND lang='en'",
                              (passage_id,)).fetchone()
        if g:
            p.gloss = Gloss(lang="en", text=g[0], author=g[1], method=g[2], review_status=g[3])
        return p

    def stored_hash(self, passage_id: str) -> str | None:
        r = self.conn.execute("SELECT text_hash FROM passages WHERE passage_id=? AND revoked=0", (passage_id,)).fetchone()
        return r[0] if r else None

    def neighbours(self, passage_id: str, k: int = 2) -> list[Passage]:
        r = self.conn.execute("SELECT source_id, position FROM passages WHERE passage_id=?", (passage_id,)).fetchone()
        if not r:
            return []
        rows = self.conn.execute(
            "SELECT json FROM passages WHERE source_id=? AND position BETWEEN ? AND ? AND revoked=0 ORDER BY position",
            (r[0], r[1] - k, r[1] + k),
        ).fetchall()
        return [Passage.model_validate_json(x[0]) for x in rows]

    def chapter(self, source_id: str, prefix: str, limit: int = 400) -> list[Passage]:
        rows = self.conn.execute(
            "SELECT json FROM passages WHERE source_id=? AND passage_id LIKE ? AND revoked=0 ORDER BY position LIMIT ?",
            (source_id, prefix + "%", limit),
        ).fetchall()
        return [Passage.model_validate_json(x[0]) for x in rows]

    def corpus_version(self) -> str:
        return self.meta("corpus_version")

    def compute_corpus_version(self) -> str:
        h = hashlib.sha256()
        h.update(self.meta("manifest_version").encode())
        h.update(self.meta("terms_version").encode())
        for pid, th in self.conn.execute(
            "SELECT passage_id, text_hash FROM passages WHERE indexed=1 AND revoked=0 ORDER BY passage_id"
        ):
            h.update(f"{pid}:{th};".encode())
        return "corpus-" + h.hexdigest()[:16]

    # ---- lab-only mutation helpers (used on disposable snapshots) ----
    def snapshot_to(self, dest: Path) -> "CorpusStore":
        self.conn.commit()
        dest.parent.mkdir(parents=True, exist_ok=True)
        bk = sqlite3.connect(str(dest))
        self.conn.backup(bk)
        bk.close()
        return CorpusStore(dest)

    def close(self) -> None:
        self.conn.close()


def copy_file(src: Path, dst: Path) -> None:
    dst.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(src, dst)
