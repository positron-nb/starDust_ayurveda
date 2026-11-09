"""PRAMAAN HTTP API (FastAPI).

    uvicorn pramaan.api:app --host 127.0.0.1 --port 8600
"""
from __future__ import annotations

import json
import logging
import platform
import threading
import time
from collections import defaultdict, deque
from pathlib import Path

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from . import __version__
from .appdb import AppDB
from .config import (AYURPARAM_CONTEXT_LIMIT, AYURPARAM_MODEL_ID, AYURPARAM_REVISION, EMBED_MODEL_ID, PROMPT_VERSION,
                     REPO_ROOT, settings)
from .corpus.store import CorpusStore
from .export import packet_html, packet_json
from .lab import EXPERIMENTS, Lab
from .ledger import revalidate_claims
from .llm import make_adapter
from .pipeline import Engine, now_iso
from .retrieval import Retriever
from .safety import extract_facts, load_policy, load_safety_statements
from .schemas import QueryRequest, ReviewAction, RunResult
from .terms import load_terminology

log = logging.getLogger("pramaan")
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s %(message)s")

app = FastAPI(title="PRAMAAN API", version=__version__)
app.add_middleware(CORSMiddleware, allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
                   allow_methods=["GET", "POST", "DELETE"], allow_headers=["*"])

_state: dict = {}
_init_lock = threading.Lock()


def S() -> dict:
    with _init_lock:
        if not _state:
            if not settings.corpus_db.exists():
                raise HTTPException(503, "Corpus not built. Run: python -m pramaan.corpus.build")
            store = CorpusStore(settings.corpus_db)
            terms = load_terminology()
            policy = load_policy()
            llm = make_adapter()
            retr = Retriever(store, terms)
            _state.update(store=store, terms=terms, policy=policy, llm=llm, retriever=retr,
                          engine=Engine(store, terms, policy, llm, retr), db=AppDB(settings.app_db),
                          lab=Lab(store, terms, policy, llm))
            n = _state["db"].invalidate_corpus(store.corpus_version())
            if n:
                log.info("invalidated %d cached runs from older corpus versions", n)
    return _state


# ------------------------------------------------------------------ middleware
_hits: dict[str, deque] = defaultdict(deque)


import hashlib as _hashlib  # noqa: E402
import hmac as _hmac  # noqa: E402
import os as _os  # noqa: E402
import secrets as _secrets  # noqa: E402

# Optional demo access control. Enabled only when PRAMAAN_ACCESS_PASSCODE is set (e.g. when exposed
# through a tunnel). The passcode is typed by the visitor; the server sets an HttpOnly signed session
# cookie. No token ever lives in frontend code.
_PASSCODE = _os.environ.get("PRAMAAN_ACCESS_PASSCODE", "")
_SECRET = (_os.environ.get("PRAMAAN_SESSION_SECRET") or _secrets.token_hex(32)).encode()
_SESSION_TTL = int(_os.environ.get("PRAMAAN_SESSION_TTL_S", "28800"))
_OPEN_PATHS = {"/api/login", "/api/auth/status"}
_login_hits: dict[str, deque] = defaultdict(deque)


def _sign(exp: int) -> str:
    return f"{exp}.{_hmac.new(_SECRET, str(exp).encode(), _hashlib.sha256).hexdigest()}"


def _valid_session(cookie: str | None) -> bool:
    if not cookie or "." not in cookie:
        return False
    exp_s, _sig = cookie.split(".", 1)
    try:
        exp = int(exp_s)
    except ValueError:
        return False
    return exp > time.time() and _hmac.compare_digest(cookie, _sign(exp))


def auth_enabled() -> bool:
    return bool(_PASSCODE)


@app.middleware("http")
async def guard(request: Request, call_next):
    if auth_enabled() and request.url.path.startswith("/api/") and request.url.path not in _OPEN_PATHS:
        if not _valid_session(request.cookies.get("pramaan_session")):
            return JSONResponse({"detail": "authentication required"}, status_code=401)
    if request.url.path.startswith("/api/") and request.method == "POST":
        ip = request.client.host if request.client else "?"
        q = _hits[ip]
        now = time.time()
        while q and now - q[0] > 60:
            q.popleft()
        if len(q) >= settings.rate_limit_per_min:
            return JSONResponse({"detail": "rate limit exceeded"}, status_code=429)
        q.append(now)
        cl = request.headers.get("content-length")
        if cl and int(cl) > 64_000:
            return JSONResponse({"detail": "request too large"}, status_code=413)
    resp = await call_next(request)
    resp.headers["X-Content-Type-Options"] = "nosniff"
    resp.headers["Referrer-Policy"] = "no-referrer"
    resp.headers["Content-Security-Policy"] = ("default-src 'self'; img-src 'self' data:; style-src 'self' 'unsafe-inline' https://fonts.googleapis.com; "
                                               "font-src 'self' https://fonts.gstatic.com; script-src 'self'; connect-src 'self'; frame-ancestors 'none'")
    return resp


class LoginReq(BaseModel):
    passcode: str


def _cookie_secure(request: Request) -> bool:
    """Secure cookies are never sent over plain http, so a fixed Secure flag locks out a local
    http://127.0.0.1 demo. Default: Secure when the request arrived over HTTPS (directly or via a tunnel
    setting X-Forwarded-Proto). PRAMAAN_COOKIE_SECURE=1/0 forces it."""
    forced = _os.environ.get("PRAMAAN_COOKIE_SECURE", "")
    if forced in ("0", "1"):
        return forced == "1"
    return request.url.scheme == "https" or request.headers.get("x-forwarded-proto", "").lower() == "https"


@app.get("/api/auth/status")
def auth_status(request: Request):
    return {"auth_required": auth_enabled(), "authenticated": (not auth_enabled()) or _valid_session(request.cookies.get("pramaan_session"))}


@app.post("/api/login")
def login(req: LoginReq, request: Request):
    if not auth_enabled():
        return {"ok": True, "auth_required": False}
    ip = request.client.host if request.client else "?"
    q = _login_hits[ip]
    now = time.time()
    while q and now - q[0] > 300:
        q.popleft()
    if len(q) >= 5:
        raise HTTPException(429, "too many attempts; wait 5 minutes")
    q.append(now)
    if not _hmac.compare_digest(req.passcode.encode(), _PASSCODE.encode()):
        raise HTTPException(401, "wrong passcode")
    resp = JSONResponse({"ok": True})
    resp.set_cookie("pramaan_session", _sign(int(now) + _SESSION_TTL), max_age=_SESSION_TTL, httponly=True,
                    samesite="strict", secure=_cookie_secure(request))
    return resp


@app.post("/api/logout")
def logout():
    resp = JSONResponse({"ok": True})
    resp.delete_cookie("pramaan_session")
    return resp


def require_local():
    if settings.is_public_demo:
        raise HTTPException(403, "Disabled on the read-only public demo. Run PRAMAAN locally to use this action.")


# ------------------------------------------------------------------ routes
@app.get("/api/health")
def health():
    s = S()
    st: CorpusStore = s["store"]
    return {
        "api": "ok", "version": __version__, "deploy_mode": settings.deploy_mode,
        "llm": s["llm"].health(), "llm_mode_configured": settings.llm_mode,
        "model": {"id": AYURPARAM_MODEL_ID, "revision": AYURPARAM_REVISION, "context_limit": AYURPARAM_CONTEXT_LIMIT},
        "prompt_version": PROMPT_VERSION, "corpus_version": st.corpus_version(), "rules_version": s["policy"].version,
        "terms_version": s["terms"].version, "indexed_passages": len(s["retriever"].passages),
        "dense": {"enabled": s["retriever"].dense is not None, "model": EMBED_MODEL_ID, "error": s["retriever"].dense_error},
        "platform": platform.platform(),
    }


def _validated(run: RunResult) -> RunResult:
    s = S()
    st: CorpusStore = s["store"]
    run_hashes = {c.passage.passage_id: c.passage.text_hash for c in run.evidence}
    reasons = revalidate_claims(run.claims, st, run_hashes)
    if run.trace.corpus_version != st.corpus_version():
        reasons.insert(0, f"corpus version changed: {run.trace.corpus_version} -> {st.corpus_version()}")
    newly_hidden = [c for c in run.claims if not c.shown_in_answer]
    run.claims = [c for c in run.claims if c.shown_in_answer]
    run.rejected_claims = run.rejected_claims + newly_hidden
    run.revalidated_at = now_iso()
    run.stale = bool(reasons)
    run.stale_reasons = reasons
    return run


@app.post("/api/query")
def query(req: QueryRequest):
    if len(req.query) > settings.max_query_chars or len(req.case_text) > settings.max_case_chars:
        raise HTTPException(413, "query or case text too long")
    s = S()
    eng: Engine = s["engine"]
    db: AppDB = s["db"]
    from .safety import merge_facts
    facts = merge_facts(extract_facts(req.query, s["terms"], s["policy"], req.case_text), req.facts)
    key = eng.cache_key(req, facts)
    hit = db.cached(key)
    if hit is not None:
        r = _validated(hit)
        d = r.model_dump()
        d["cached"] = True
        return d
    r = eng.run(req)
    db.save_run(r, req.session_id)
    d = r.model_dump()
    d["cached"] = False
    return d


class FactReq(BaseModel):
    query: str = ""
    case_text: str = ""


@app.post("/api/facts/extract")
def facts_extract(req: FactReq):
    s = S()
    return [f.model_dump() for f in extract_facts(req.query, s["terms"], s["policy"], req.case_text)]


@app.get("/api/runs")
def runs(session_id: str | None = None, limit: int = 50):
    if settings.is_public_demo and not session_id:
        return []
    return S()["db"].list_runs(min(limit, 200), session_id)


@app.get("/api/runs/{run_id}")
def get_run(run_id: str):
    r = S()["db"].get_run(run_id)
    if not r:
        raise HTTPException(404, "run not found")
    return _validated(r).model_dump()


@app.delete("/api/runs/{run_id}")
def delete_run(run_id: str):
    S()["db"].delete_run(run_id)
    return {"deleted": run_id}


@app.get("/api/runs/{run_id}/export.json")
def export_json(run_id: str):
    r = S()["db"].get_run(run_id)
    if not r:
        raise HTTPException(404)
    return JSONResponse(packet_json(_validated(r)), headers={"Content-Disposition": f"attachment; filename=pramaan-{run_id}.json"})


@app.get("/api/runs/{run_id}/export.html", response_class=HTMLResponse)
def export_html(run_id: str):
    s = S()
    r = s["db"].get_run(run_id)
    if not r:
        raise HTTPException(404)
    revs = [x for x in s["db"].reviews() if x.get("run_id") == run_id]
    return HTMLResponse(packet_html(_validated(r), revs))


@app.get("/api/sources")
def sources():
    s = S()
    st: CorpusStore = s["store"]
    manifest = json.loads((settings.data_dir / "sources" / "manifest.json").read_text(encoding="utf-8"))
    counts = {}
    for p in s["retriever"].passages:
        counts.setdefault(p.source_id, {"indexed": 0, "chapters": {}})
        counts[p.source_id]["indexed"] += 1
        ch = p.chapter_name
        counts[p.source_id]["chapters"][ch] = counts[p.source_id]["chapters"].get(ch, 0) + 1
    reviewed = s["db"].latest_decisions("passage")
    return {"manifest": manifest, "counts": counts, "corpus_version": st.corpus_version(),
            "passage_reviews": {"reviewed": len(reviewed), "indexed": len(s["retriever"].passages)}}


@app.get("/api/passages/{passage_id}")
def passage(passage_id: str, context: int = 2):
    s = S()
    st: CorpusStore = s["store"]
    p = st.get(passage_id)
    if not p:
        raise HTTPException(404, "passage not found in corpus (it may not exist in this edition)")
    src = st.source_raw(p.source_id) or {}
    src.pop("_file_sha256_at_build", None)
    return {"passage": p.model_dump(), "neighbours": [n.model_dump() for n in st.neighbours(passage_id, min(context, 5))],
            "source": src, "tags": {k: [list(x) for x in v] for k, v in s["terms"].tag_passage(p.text_iast).items()},
            "reviews": s["db"].reviews("passage", passage_id),
            "gloss_reviews": s["db"].reviews("gloss", passage_id)}


@app.get("/api/chapters")
def chapters():
    s = S()
    out: dict = {}
    for p in s["retriever"].passages:
        k = f"{p.passage_id.rsplit('.', 1)[0]}"
        if k not in out:
            out[k] = {"key": k, "source_id": p.source_id, "work": p.work, "name": p.chapter_name, "count": 0, "first": p.passage_id}
        out[k]["count"] += 1
    return list(out.values())


@app.get("/api/chapters/{key}")
def chapter(key: str):
    s = S()
    work = "sarit-caraka" if key.startswith("Ca") else "sarit-ah"
    ps = s["store"].chapter(work, key + ".")
    return [{"passage_id": p.passage_id, "verse_label": p.verse_label, "text_iast": p.text_iast, "concepts": p.concepts,
             "modules": p.modules} for p in ps]


@app.get("/api/search")
def search(q: str, limit: int = 10):
    s = S()
    terms = s["terms"]
    cids = list(terms.concepts_in_query(q))
    hits, info = s["retriever"].search(q + " " + " ".join(terms.expansion_terms(cids)), cids, q, limit=min(limit, 30))
    return {"concepts": cids, "info": info, "hits": [{"passage_id": h.passage.passage_id, "label": f"{h.passage.work}, {h.passage.verse_label}",
                                                      "text_iast": h.passage.text_iast, "scores": h.as_dict()} for h in hits]}


@app.get("/api/rules")
def rules():
    s = S()
    p = s["policy"]
    return {"version": p.version, "rules": p.rules, "templates": p.templates, "lexicons": p.lexicons,
            "statements": load_safety_statements(), "reviews": s["db"].latest_decisions("rule")}


@app.get("/api/terms")
def terms():
    t = S()["terms"]
    return {"version": t.version, "concepts": [{"id": c.id, "label": c.label, "aliases": c.aliases, "note": c.note} for c in t.concepts]}


@app.post("/api/reviews")
def add_review(a: ReviewAction):
    require_local()
    rid = S()["db"].add_review(a, now_iso())
    return {"review_id": rid}


@app.get("/api/reviews")
def list_reviews(target_type: str | None = None, target_id: str | None = None):
    return S()["db"].reviews(target_type, target_id)


class LabReq(BaseModel):
    experiment: str
    run_id: str | None = None
    passage_id: str | None = None


@app.get("/api/lab/experiments")
def lab_experiments():
    return EXPERIMENTS


@app.post("/api/lab/run")
def lab_run(req: LabReq):
    s = S()
    base = s["db"].get_run(req.run_id) if req.run_id else None
    if req.run_id and base is None:
        raise HTTPException(404, "base run not found")
    try:
        return s["lab"].run(req.experiment, base, req.passage_id)
    except ValueError as e:
        raise HTTPException(400, str(e))


@app.get("/api/eval/results")
def eval_results():
    d = REPO_ROOT / "eval" / "results"
    out = []
    if d.exists():
        for f in d.glob("eval_*.json"):
            try:
                out.append(json.loads(f.read_text(encoding="utf-8")))
            except Exception:
                continue
    out.sort(key=lambda r: r.get("created_at", ""), reverse=True)
    for r in out:
        r["current_corpus"] = r.get("corpus_version") == S()["store"].corpus_version()
    return out


@app.get("/api/eval/smoke")
def eval_smoke():
    d = REPO_ROOT / "eval" / "results"
    fs = sorted(d.glob("smoke_*.json"), reverse=True) if d.exists() else []
    if not fs:
        return None
    s = json.loads(fs[0].read_text(encoding="utf-8"))
    return {k: s.get(k) for k in ("started", "result", "revision", "gpu", "torch", "transformers", "dtype", "load_seconds",
                                  "gpu_mem_after_load_mb", "config_max_position_embeddings", "system_message_reaches_model_via_template",
                                  "chat_template_serialized")} | {"file": fs[0].name}


@app.get("/api/eval/cases")
def eval_cases():
    p = REPO_ROOT / "eval" / "cases.jsonl"
    if not p.exists():
        return []
    cases = [json.loads(l) for l in p.read_text(encoding="utf-8").splitlines() if l.strip()]
    rv = S()["db"].latest_decisions("eval_case")
    for c in cases:
        c["latest_review"] = rv.get(c["case_id"])
    return cases


@app.post("/api/admin/reset")
def admin_reset():
    require_local()
    S()["db"].reset(keep_reviews=True)
    import shutil
    shutil.rmtree(settings.runtime_dir / "lab", ignore_errors=True)
    return {"reset": True, "note": "cached runs and lab snapshots deleted; review log kept"}


@app.post("/api/session/reset")
def session_reset(session_id: str):
    db = S()["db"]
    for r in db.list_runs(500, session_id):
        db.delete_run(r["run_id"])
    return {"reset": session_id}


# ------------------------------------------------------------------ static frontend
DIST = REPO_ROOT / "frontend" / "dist"
if DIST.exists():
    app.mount("/assets", StaticFiles(directory=DIST / "assets"), name="assets")

    @app.get("/{path:path}", include_in_schema=False)
    def spa(path: str):
        f = DIST / path
        if path and f.is_file() and DIST in f.resolve().parents:
            return FileResponse(f)
        return FileResponse(DIST / "index.html", headers={"Cache-Control": "no-cache"})
