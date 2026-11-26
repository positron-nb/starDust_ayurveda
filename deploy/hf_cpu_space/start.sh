#!/usr/bin/env bash
# Start PRAMAAN on the Space: the web app comes up at once (verses, citations, safety); AyurParam
# weights download in the background and the model server joins when loaded. Until then answers
# fall back to source-only mode, as designed.
set -euo pipefail
cd /home/user/app
echo "PRAMAAN build commit: $(cat BUILD_COMMIT)"

(
  python - <<'PY'
import os, time
from huggingface_hub import snapshot_download
t = time.time()
snapshot_download("bharatgenai/AyurParam", revision="27c69eeef492bbc9e2c0048fc1e95959ffc0820e",
                  local_dir=os.environ["AYURPARAM_LOCAL_DIR"], allow_patterns=["*.json", "*.py", "*.safetensors"])
print(f"AyurParam weights ready in {time.time() - t:.0f}s", flush=True)
PY
  exec python model_server/server.py
) &

exec python -m uvicorn --app-dir backend pramaan.api:app --host 0.0.0.0 --port 7860 \
  --proxy-headers --forwarded-allow-ips "*"
