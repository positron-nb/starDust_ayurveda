"""Probe prompt formats against REAL retrieved evidence to choose the explanation prompt.
Writes eval/results/prompt_probe_<ts>.json. Development-split queries only."""
from __future__ import annotations

import json
import sys
import time
from pathlib import Path

import torch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))

from pramaan.config import settings  # noqa: E402
from pramaan.corpus.store import CorpusStore  # noqa: E402
from pramaan.llm import format_evidence, sanitize  # noqa: E402
from pramaan.pipeline import Engine  # noqa: E402
from pramaan.llm import LLMAdapter  # noqa: E402
from pramaan.retrieval import Retriever  # noqa: E402
from pramaan.safety import load_policy  # noqa: E402
from pramaan.schemas import QueryRequest  # noqa: E402
from pramaan.terms import load_terminology  # noqa: E402

QUERIES = ["What is āma and how is it formed?", "Why should food be taken in proper quantity (mātrā)?",
           "आम क्या है और यह कैसे बनता है?"]


def variants(q: str, cards, lang: str):
    ev = " ".join(format_evidence(c.label, c.passage, True) for c in cards)
    lang_word = "Hindi" if lang == "hi" else "English"
    return {
        "V1_instr_end_labels": f"<context> Instructions (mandatory): Use ONLY the evidence passages. Write 2 to 4 short sentences in {lang_word}. End every sentence with the label of the supporting passage, e.g. [E1]. Evidence: {ev} <user> {sanitize(q)} (Cite evidence labels like [E1].) <assistant>",
        "V2_per_passage_prefill": f"<context> Explain what each evidence passage says that is relevant to the question, one sentence per passage, in {lang_word}. Start each sentence with the passage label. Use only the passages. Evidence: {ev} <user> {sanitize(q)} <assistant><actual_response>[E1]",
        "V3_fewshot_prefill": f"<context> Answer only from the evidence passages, in {lang_word}. Format: each sentence begins with the label of the passage it comes from. Example: [E1] The passage says food should be taken in proper quantity. [E2] It adds that heavy food should fill only half. Evidence: {ev} <user> {sanitize(q)} <assistant><actual_response>[E1]",
    }


def main():
    from transformers import AutoModelForCausalLM, AutoTokenizer

    store = CorpusStore(settings.corpus_db)
    terms, policy = load_terminology(), load_policy()
    eng = Engine(store, terms, policy, LLMAdapter(), Retriever(store, terms, enable_dense=False))
    tok = AutoTokenizer.from_pretrained(str(settings.model_dir))
    model = AutoModelForCausalLM.from_pretrained(str(settings.model_dir), trust_remote_code=True, torch_dtype=torch.bfloat16).to("cuda").eval()
    eos = [tok.eos_token_id, 3]
    out = []
    for q in QUERIES:
        lang = "hi" if any("ऀ" <= ch <= "ॿ" for ch in q) else "en"
        r = eng.run(QueryRequest(query=q, lang=lang, use_model=False))
        cards = [c for c in r.evidence if c.role != "adjacent_context"][:4]
        for name, p in variants(q, cards, lang).items():
            ids = tok(p, return_tensors="pt", add_special_tokens=False).to("cuda")
            t = time.perf_counter()
            with torch.inference_mode():
                o = model.generate(**ids, max_new_tokens=160, do_sample=False, repetition_penalty=1.15, eos_token_id=eos, pad_token_id=tok.pad_token_id)
            txt = tok.decode(o[0][ids["input_ids"].shape[1]:], skip_special_tokens=False)
            rec = {"query": q, "variant": name, "evidence": [c.passage.passage_id for c in cards], "prompt_tokens": int(ids["input_ids"].shape[1]),
                   "ms": round((time.perf_counter() - t) * 1000), "output": txt}
            out.append(rec)
            print("==", q[:40], name, rec["prompt_tokens"], rec["ms"], "ms\n   ", txt[:400].replace("\n", " "))
    f = ROOT / "eval" / "results" / f"prompt_probe_{time.strftime('%Y%m%d_%H%M%S')}.json"
    f.write_text(json.dumps({"kind": "prompt_probe", "model_revision": "27c69ee", "records": out}, ensure_ascii=False, indent=2), encoding="utf-8")
    print("WROTE", f)


if __name__ == "__main__":
    main()
