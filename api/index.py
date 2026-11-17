"""Vercel entrypoint: PRAMAAN API in HOSTED RETRIEVAL-ONLY mode.

AyurParam (2.9B, GPU) cannot run on Vercel serverless functions, so this deployment runs with the model
OFF and is labelled as such in the UI. Retrieval (BM25), source passages, citation checks, safety rules,
source-only fallback and the Integrity Lab are live. Read-only public demo: review/admin routes disabled.
"""
import os
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))

os.environ.setdefault("PRAMAAN_LLM_MODE", "off")
os.environ.setdefault("PRAMAAN_ENABLE_DENSE", "0")         # no torch / e5 on serverless
os.environ.setdefault("PRAMAAN_DEPLOY_MODE", "public_demo")
os.environ.setdefault("PRAMAAN_BUILD_DIR", "/tmp/pramaan_build")
os.environ.setdefault("PRAMAAN_RUNTIME_DIR", "/tmp/pramaan_runtime")

build = Path(os.environ["PRAMAAN_BUILD_DIR"])
build.mkdir(parents=True, exist_ok=True)
if not (build / "corpus.sqlite").exists():  # bundle is read-only; SQLite needs a writable copy
    shutil.copyfile(ROOT / "deploy" / "vercel" / "corpus.sqlite", build / "corpus.sqlite")

from pramaan.api import app  # noqa: E402,F401
