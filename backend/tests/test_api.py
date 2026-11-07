"""API-level checks (no model needed): public-demo read-only mode, input limits, headers."""
from fastapi.testclient import TestClient

from pramaan import api
from pramaan.config import settings


def test_public_demo_blocks_writes_and_limits_inputs(monkeypatch, tmp_path):
    monkeypatch.setattr(settings, "deploy_mode", "public_demo")
    monkeypatch.setattr(settings, "runtime_dir", tmp_path)
    monkeypatch.setattr(settings, "llm_mode", "off")
    api._state.clear()
    c = TestClient(api.app)
    r = c.post("/api/reviews", json={"target_type": "claim", "target_id": "x", "decision": "accepted",
                                     "reviewer_name": "a", "reviewer_role": "engineer"})
    assert r.status_code == 403
    assert c.post("/api/admin/reset").status_code == 403
    assert c.get("/api/runs").json() == []  # no cross-session listing on the public demo
    assert c.post("/api/query", json={"query": "a" * 2500}).status_code == 413
    h = c.get("/api/health")
    assert h.status_code == 200 and h.headers["x-content-type-options"] == "nosniff"
    assert h.json()["llm"]["available"] is False  # retrieval-only is reported, not hidden
    r = c.post("/api/query", json={"query": "What is ama and how is it formed?", "use_model": True})
    assert r.status_code == 200 and r.json()["status"] in ("retrieval_only", "answered", "insufficient_evidence")
    assert r.json()["trace"]["inference_ran"] is False
    api._state.clear()
