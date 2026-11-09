"""Demo access control (enabled only when PRAMAAN_ACCESS_PASSCODE is set)."""
import importlib

from fastapi.testclient import TestClient


def test_passcode_gate(monkeypatch, tmp_path):
    monkeypatch.setenv("PRAMAAN_ACCESS_PASSCODE", "synthetic-test-passcode")
    monkeypatch.setenv("PRAMAAN_COOKIE_SECURE", "0")
    from pramaan import api as api_mod
    from pramaan.config import settings
    api = importlib.reload(api_mod)
    monkeypatch.setattr(settings, "runtime_dir", tmp_path)
    monkeypatch.setattr(settings, "llm_mode", "off")
    api._state.clear()
    c = TestClient(api.app)
    assert c.get("/api/health").status_code == 401
    assert c.get("/api/auth/status").json() == {"auth_required": True, "authenticated": False}
    assert c.post("/api/login", json={"passcode": "wrong"}).status_code == 401
    r = c.post("/api/login", json={"passcode": "synthetic-test-passcode"})
    assert r.status_code == 200 and "httponly" in r.headers["set-cookie"].lower()
    assert c.get("/api/health").status_code == 200
    c.cookies.set("pramaan_session", "9999999999.forged")
    assert c.get("/api/health").status_code == 401  # forged cookie rejected
    c2 = TestClient(api.app)
    codes = [c2.post("/api/login", json={"passcode": "x"}).status_code for _ in range(6)]
    assert codes[-1] == 429  # brute-force limit
    monkeypatch.delenv("PRAMAAN_ACCESS_PASSCODE")
    api._state.clear()
    importlib.reload(api_mod)
