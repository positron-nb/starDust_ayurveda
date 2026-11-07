"""Central configuration. Values come from environment variables with safe local defaults."""
from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]


def _env(name: str, default: str) -> str:
    return os.environ.get(name, default)


def _path(name: str, default: Path) -> Path:
    v = os.environ.get(name)
    return Path(v) if v else default


# Pinned AyurParam revision, verified 2026-11-07 against the Hugging Face API.
AYURPARAM_MODEL_ID = "bharatgenai/AyurParam"
AYURPARAM_REVISION = "27c69eeef492bbc9e2c0048fc1e95959ffc0820e"
# config.json max_position_embeddings at the pinned revision. The tokenizer's model_max_length
# (1e30 sentinel) is NOT a supported window and is ignored.
AYURPARAM_CONTEXT_LIMIT = 2048

EMBED_MODEL_ID = "intfloat/multilingual-e5-small"
EMBED_MODEL_REVISION = "614241f622f53c4eeff9890bdc4f31cfecc418b3"
EMBED_MAX_TOKENS = 512

PROMPT_VERSION = "prompts-2026.11.07.4-perpassage"


@dataclass
class Settings:
    data_dir: Path = field(default_factory=lambda: _path("PRAMAAN_DATA_DIR", REPO_ROOT / "data"))
    build_dir: Path = field(default_factory=lambda: _path("PRAMAAN_BUILD_DIR", REPO_ROOT / "data" / "build"))
    runtime_dir: Path = field(default_factory=lambda: _path("PRAMAAN_RUNTIME_DIR", REPO_ROOT / "data" / "runtime"))
    model_dir: Path = field(default_factory=lambda: _path("AYURPARAM_LOCAL_DIR", REPO_ROOT / "models" / "AyurParam"))
    # "http" -> call the separate model server; "fixture" -> replay recorded live outputs;
    # "off" -> retrieval-only mode.
    llm_mode: str = field(default_factory=lambda: _env("PRAMAAN_LLM_MODE", "http"))
    model_server_url: str = field(default_factory=lambda: _env("AYURPARAM_SERVER_URL", "http://127.0.0.1:8601"))
    model_timeout_s: float = field(default_factory=lambda: float(_env("AYURPARAM_TIMEOUT_S", "180")))
    qdrant_url: str = field(default_factory=lambda: _env("QDRANT_URL", ""))  # empty -> embedded local mode
    # "local" (full features, admin routes on) or "public_demo" (read-only, disposable sessions).
    deploy_mode: str = field(default_factory=lambda: _env("PRAMAAN_DEPLOY_MODE", "local"))
    max_query_chars: int = 2000
    max_case_chars: int = 4000
    rate_limit_per_min: int = field(default_factory=lambda: int(_env("PRAMAAN_RATE_LIMIT", "30")))
    enable_dense: bool = field(default_factory=lambda: _env("PRAMAAN_ENABLE_DENSE", "1") == "1")

    @property
    def corpus_db(self) -> Path:
        return self.build_dir / "corpus.sqlite"

    @property
    def app_db(self) -> Path:
        return self.runtime_dir / "app.sqlite"

    @property
    def qdrant_path(self) -> Path:
        return self.build_dir / "qdrant"

    @property
    def fixture_file(self) -> Path:
        return REPO_ROOT / "eval" / "fixtures" / "ayurparam_replay.jsonl"

    @property
    def is_public_demo(self) -> bool:
        return self.deploy_mode == "public_demo"


settings = Settings()
