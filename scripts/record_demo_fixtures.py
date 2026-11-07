"""Record LIVE AyurParam outputs for the demo prompts so the venue can fall back to labelled
fixture replay (PRAMAAN_LLM_MODE=fixture). Requires the model server to be running.

    python scripts/record_demo_fixtures.py

Fixture replay only matches byte-identical prompts, so re-record after any change to the corpus,
terminology, prompts or retrieval.
"""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))

from pramaan.config import settings  # noqa: E402
from pramaan.corpus.store import CorpusStore  # noqa: E402
from pramaan.llm import HTTPAdapter  # noqa: E402
from pramaan.pipeline import Engine  # noqa: E402
from pramaan.retrieval import Retriever  # noqa: E402
from pramaan.safety import load_policy  # noqa: E402
from pramaan.schemas import CaseFact, QueryRequest  # noqa: E402
from pramaan.terms import load_terminology  # noqa: E402

DEMOS = [
    QueryRequest(query="What is āma, and how does weak agni lead to ajīrṇa according to the classical texts?", lang="en"),
    QueryRequest(query="आम क्या है और मन्दाग्नि से अजीर्ण कैसे होता है?", lang="hi"),
    QueryRequest(query="Can ashwagandha be considered for weak agni and fatigue in this case?", lang="en",
                 case_text="Educational case: 28-year-old woman with low appetite and tiredness after meals."),
    QueryRequest(query="Explain what Charaka Sutrasthana 45.12 says about agni.", lang="en"),
    QueryRequest(query="Does triphala interact with warfarin?", lang="en"),
    QueryRequest(query="Why should food be taken in proper quantity (matra)?", lang="en"),
]


def main():
    llm = HTTPAdapter(record=True)
    if not llm.health().get("available"):
        raise SystemExit("model server not available")
    store = CorpusStore(settings.corpus_db)
    terms, policy = load_terminology(), load_policy()
    eng = Engine(store, terms, policy, llm, Retriever(store, terms))
    for q in DEMOS:
        r = eng.run(q)
        print(r.status, r.trace.inference_ran, q.query[:60])
    # counterfactual variant of demo B
    q = DEMOS[2]
    for state in ("present", "absent"):
        facts = [f for f in eng.run(QueryRequest(query=q.query, lang="en", case_text=q.case_text, use_model=False)).facts]
        facts = [CaseFact(**{**f.model_dump(), "state": state, "origin": "user_edited"}) if f.key == "pregnancy" else f for f in facts]
        r = eng.run(QueryRequest(query=q.query, lang="en", case_text=q.case_text, facts=facts))
        print(r.status, "pregnancy", state)
    n = sum(1 for _ in open(settings.fixture_file, encoding="utf-8"))
    print(json.dumps({"fixture_file": str(settings.fixture_file), "records": n}))


if __name__ == "__main__":
    main()
