# Demo hosting — laptop + Cloudflare Tunnel (fallback independent of ZeroGPU)

**Not production hosting.** A temporary, passcode-protected demo served from the team's GPU laptop.
Status (2026-11-09): application-side controls implemented and tested; **the tunnel itself has not
been run** (`cloudflared` is not installed on the build machine and was not downloaded by the assistant).

Reference: Cloudflare Tunnel docs — https://developers.cloudflare.com/cloudflare-one/connections/connect-networks/
(verify the current install/run commands there before use).

## Architecture
```
visitor ──HTTPS──► Cloudflare ──tunnel──► cloudflared (laptop) ──► 127.0.0.1:8600  PRAMAAN API + UI   (only this is exposed)
                                                                    127.0.0.1:8601  AyurParam server   (NEVER exposed)
```

## Controls (implemented)
| Requirement | Implementation | Tested |
|---|---|---|
| Model server private | binds `127.0.0.1:8601`; tunnel points only at :8600 | by config |
| Authentication | `PRAMAAN_ACCESS_PASSCODE` → passcode form → HttpOnly, SameSite=Strict, Secure, HMAC-signed session cookie (8 h); every `/api/*` except login/status returns 401 without it | `tests/test_auth.py` |
| Brute force | 5 login attempts / 5 min / IP → 429 | `test_auth.py` |
| Rate limiting | 30 POST / min / IP (`PRAMAAN_RATE_LIMIT`), 64 KB body cap, query/case length caps | `test_api.py` |
| Read-only demo | `PRAMAAN_DEPLOY_MODE=public_demo`: review/admin routes 403, runs listed per browser session only | `test_api.py` |
| CORS | only `http://localhost:5173` / `127.0.0.1:5173` (dev); same-origin in production | by config |
| Secrets | env vars only (`.env`, git-ignored); nothing in frontend code | inspection |
| Logs | access log records method/path/status only; request bodies (queries, cases) are not logged | inspection |
| Headers | CSP, nosniff, no-referrer, frame-ancestors none | `test_api.py` |
| Data | synthetic educational cases only; banner on login page says so | — |

## Run (Windows PowerShell)
```powershell
# 1. strong random secrets for this demo session
$env:PRAMAAN_ACCESS_PASSCODE = "<share privately with judges/reviewers>"
$env:PRAMAAN_SESSION_SECRET  = (python -c "import secrets;print(secrets.token_hex(32))")
$env:PRAMAAN_DEPLOY_MODE     = "public_demo"
# 2. services (two terminals)
.venv\Scripts\python model_server\server.py
.venv\Scripts\python -m uvicorn --app-dir backend pramaan.api:app --host 127.0.0.1 --port 8600
# 3. tunnel (install cloudflared from Cloudflare's official download page first)
cloudflared tunnel --url http://127.0.0.1:8600        # quick tunnel: random *.trycloudflare.com URL, changes on restart
```
A named tunnel (Cloudflare account + domain) gives a stable URL; quick tunnels have no uptime guarantee.

## Kill switch
Close the `cloudflared` window (or Ctrl+C) → public access stops immediately. Rotating
`PRAMAAN_SESSION_SECRET` and restarting the API invalidates every existing session.

## Test checklist
| Test | Result |
|---|---|
| Normal access with passcode | PASS (local, `test_auth.py`) |
| Invalid passcode / forged cookie | PASS (401) |
| API health behind auth | PASS |
| Model inference | PASS locally (live runs in eval) — not through a tunnel |
| Source-only fallback | PASS locally (browser check 2026-11-08) |
| Safety fallback (escalation, not-assessed) | PASS (unit tests) |
| Tunnel disconnection | **NOT TESTED** (no cloudflared) |
| Backend restart | sessions survive only if `PRAMAAN_SESSION_SECRET` is fixed; otherwise visitors re-enter the passcode (by design) |
