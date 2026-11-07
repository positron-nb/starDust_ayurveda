"""Probe 2: per-passage explanation prompts (citation bound server-side). Dev queries only."""
import json, sys, time
from pathlib import Path
import torch
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))
from pramaan.config import settings
from pramaan.corpus.store import CorpusStore
from pramaan.llm import LLMAdapter, sanitize
from pramaan.pipeline import Engine
from pramaan.retrieval import Retriever
from pramaan.safety import load_policy
from pramaan.schemas import QueryRequest
from pramaan.terms import load_terminology
from transformers import AutoModelForCausalLM, AutoTokenizer

QUERIES = ["What is āma and how is it formed?", "Why should food be taken in proper quantity (mātrā)?", "आम क्या है और यह कैसे बनता है?", "What are the signs of ajīrṇa (indigestion)?"]
def P(q, c, lang, gloss=True):
    p = c.passage
    g = f" (unreviewed draft gloss: {sanitize(p.gloss.text)})" if gloss and p.gloss else ""
    lw = "Hindi" if lang == "hi" else "English"
    return (f"<context> Passage from {p.work}, {p.verse_label}: {sanitize(p.text_iast)}{g} "
            f"Task: In one or two short sentences in {lw}, explain what THIS passage says that is relevant to the question. "
            f"Use only this passage; do not add other knowledge. If the passage is not relevant to the question, write only: NOT RELEVANT. "
            f"<user> {sanitize(q)} <assistant>")
store = CorpusStore(settings.corpus_db); terms, policy = load_terminology(), load_policy()
eng = Engine(store, terms, policy, LLMAdapter(), Retriever(store, terms, enable_dense=False))
tok = AutoTokenizer.from_pretrained(str(settings.model_dir))
model = AutoModelForCausalLM.from_pretrained(str(settings.model_dir), trust_remote_code=True, torch_dtype=torch.bfloat16).to("cuda").eval()
out = []
for q in QUERIES:
    lang = "hi" if any("ऀ" <= ch <= "ॿ" for ch in q) else "en"
    r = eng.run(QueryRequest(query=q, lang=lang, use_model=False))
    for c in [c for c in r.evidence if c.role == "primary"][:3]:
        for gloss in (True, False):
            if not c.passage.gloss and not gloss: continue
            p = P(q, c, lang, gloss)
            ids = tok(p, return_tensors="pt", add_special_tokens=False).to("cuda")
            t = time.perf_counter()
            with torch.inference_mode():
                o = model.generate(**ids, max_new_tokens=90, do_sample=False, repetition_penalty=1.15, eos_token_id=[tok.eos_token_id, 3], pad_token_id=tok.pad_token_id)
            txt = tok.decode(o[0][ids["input_ids"].shape[1]:], skip_special_tokens=True)
            rec = {"query": q, "passage": c.passage.passage_id, "gloss": gloss, "prompt_tokens": int(ids["input_ids"].shape[1]), "ms": round((time.perf_counter()-t)*1000), "output": txt}
            out.append(rec); print("==", q[:30], c.passage.passage_id, "gloss" if gloss else "nogloss", rec["prompt_tokens"], rec["ms"], "\n   ", txt[:300].replace("\n"," "))
f = ROOT / "eval" / "results" / f"prompt_probe2_{time.strftime('%Y%m%d_%H%M%S')}.json"
f.write_text(json.dumps({"kind": "prompt_probe_per_passage", "records": out}, ensure_ascii=False, indent=2), encoding="utf-8"); print("WROTE", f)
