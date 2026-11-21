"""Run the PRAMAAN API for a public tunnel demo (laptop + Cloudflare Tunnel).

    python scripts/run_public_demo.py            # http://127.0.0.1:8600 (expose ONLY this port)

Read-only public demo mode, live AyurParam via the local model server (start model_server/server.py
first). Optional passcode: set PRAMAAN_ACCESS_PASSCODE before running.
"""
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
os.environ.setdefault("PRAMAAN_DEPLOY_MODE", "public_demo")
os.environ.setdefault("PRAMAAN_LLM_MODE", "http")
os.environ.setdefault("PRAMAAN_RATE_LIMIT", "20")
sys.path.insert(0, str(ROOT / "backend"))

import uvicorn  # noqa: E402

if __name__ == "__main__":
    # proxy_headers lets the app see X-Forwarded-Proto=https from the tunnel (Secure session cookie)
    uvicorn.run("pramaan.api:app", host="127.0.0.1", port=8600, proxy_headers=True, forwarded_allow_ips="127.0.0.1")
