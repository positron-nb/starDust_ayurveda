import os
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
os.environ.setdefault("PRAMAAN_ENABLE_DENSE", "0")

from pramaan.config import settings  # noqa: E402
from pramaan.corpus.store import CorpusStore  # noqa: E402
from pramaan.llm import GenResult, LLMAdapter  # noqa: E402
from pramaan.retrieval import Retriever  # noqa: E402
from pramaan.safety import load_policy  # noqa: E402
from pramaan.terms import load_terminology  # noqa: E402


class ScriptedLLM(LLMAdapter):
    """TEST-ONLY stub. Never used by the app; outputs are scripted strings, not AyurParam."""
    mode = "test_stub"

    def __init__(self, explain: str, expand: str = "agni, ama"):
        self.explain, self.expand = explain, expand
        self.prompts: list[str] = []

    def health(self):
        return {"mode": self.mode, "available": True}

    def generate(self, prompt, stage, max_new_tokens=256, **kw):
        self.prompts.append(prompt)
        return GenResult(ok=True, text=self.expand if stage == "expand" else self.explain, mode="test_stub")


@pytest.fixture(scope="session")
def store():
    if not settings.corpus_db.exists():
        pytest.skip("corpus not built; run python -m pramaan.corpus.build")
    return CorpusStore(settings.corpus_db)


@pytest.fixture(scope="session")
def terms():
    return load_terminology()


@pytest.fixture(scope="session")
def policy():
    return load_policy()


@pytest.fixture(scope="session")
def retriever(store, terms):
    return Retriever(store, terms, enable_dense=False)
