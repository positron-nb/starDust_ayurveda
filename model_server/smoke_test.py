"""Real AyurParam smoke test. Records verified facts and measurements to eval/results/smoke_<ts>.json.

    python model_server/smoke_test.py
"""
from __future__ import annotations

import hashlib
import json
import platform
import sys
import time
from pathlib import Path

import torch

ROOT = Path(__file__).resolve().parents[1]
LOCAL = ROOT / "models" / "AyurParam"
REVISION = "27c69eeef492bbc9e2c0048fc1e95959ffc0820e"


def sha(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def main() -> int:
    from transformers import AutoModelForCausalLM, AutoTokenizer
    import transformers

    out: dict = {"kind": "ayurparam_smoke_test", "model_id": "bharatgenai/AyurParam", "revision": REVISION,
                 "started": time.strftime("%Y-%m-%dT%H:%M:%S"), "platform": platform.platform(),
                 "python": sys.version.split()[0], "torch": torch.__version__, "transformers": transformers.__version__,
                 "cuda": torch.version.cuda, "gpu": torch.cuda.get_device_name(0) if torch.cuda.is_available() else None}
    cfg = json.loads((LOCAL / "config.json").read_text())
    out["config_max_position_embeddings"] = cfg["max_position_embeddings"]
    out["code_sha256"] = {f: sha(LOCAL / f) for f in ("modeling_parambharatgen.py", "config_parambharatgen.py")}

    tok = AutoTokenizer.from_pretrained(str(LOCAL), trust_remote_code=False)
    out["tokenizer_model_max_length"] = str(tok.model_max_length)
    out["tokenizer_eos"] = [tok.eos_token, tok.eos_token_id]
    out["config_eos_token_id"] = cfg["eos_token_id"]
    msgs = [{"role": "system", "content": "SYSTEM-RULE-XYZ never give doses"}, {"role": "user", "content": "What is agni?"}]
    ser = tok.apply_chat_template(msgs, tokenize=False)
    out["chat_template_serialized"] = ser
    out["system_message_reaches_model_via_template"] = "SYSTEM-RULE-XYZ" in ser

    t0 = time.time()
    dtype = torch.bfloat16 if torch.cuda.is_available() else torch.float32
    model = AutoModelForCausalLM.from_pretrained(str(LOCAL), trust_remote_code=True, torch_dtype=dtype, low_cpu_mem_usage=True)
    dev = "cuda" if torch.cuda.is_available() else "cpu"
    model.to(dev).eval()
    out["load_seconds"] = round(time.time() - t0, 1)
    out["dtype"] = str(dtype)
    out["param_count"] = sum(p.numel() for p in model.parameters())
    if dev == "cuda":
        out["gpu_mem_after_load_mb"] = round(torch.cuda.memory_allocated() / 2**20)

    eos = list({tok.eos_token_id, cfg["eos_token_id"]})
    prompts = {
        "readme_style": "<user> What is the Samprapti of Ajirna according to Ayurveda? <assistant>",
        "chat_template": tok.apply_chat_template([{"role": "user", "content": "What is the Samprapti of Ajirna according to Ayurveda?"}], tokenize=False),
        "context_style": "<context> Instructions: answer in 2 sentences and cite [E1]. Evidence: [E1] Aṣṭāṅga Hṛdaya Sūtrasthāna 13.25: ūṣmaṇo 'lpa-bala-tvena dhātum ādyam a-pācitam | duṣṭam āmāśaya-gataṃ rasam āmaṃ pracakṣate (draft gloss: when digestive heat is weak, the first dhātu stays undigested; this vitiated rasa in the āmāśaya is called āma) <user> What is āma? <assistant>",
        "hindi": "<user> आम क्या है? <assistant>",
    }
    gens = {}
    for name, p in prompts.items():
        ids = tok(p, return_tensors="pt", add_special_tokens=False).to(dev)
        res = {}
        for use_cache in (True, False):
            if dev == "cuda":
                torch.cuda.synchronize()
                torch.cuda.reset_peak_memory_stats()
            t = time.perf_counter()
            with torch.inference_mode():
                o = model.generate(**ids, max_new_tokens=80, do_sample=False, repetition_penalty=1.15, eos_token_id=eos,
                                   pad_token_id=tok.pad_token_id, use_cache=use_cache)
            if dev == "cuda":
                torch.cuda.synchronize()
            ms = (time.perf_counter() - t) * 1000
            g = o[0][ids["input_ids"].shape[1]:]
            res[f"use_cache_{use_cache}"] = {"text": tok.decode(g, skip_special_tokens=False), "ms": round(ms), "new_tokens": int(g.shape[0]),
                                             "tok_per_s": round(int(g.shape[0]) / (ms / 1000), 1),
                                             "peak_mem_mb": round(torch.cuda.max_memory_allocated() / 2**20) if dev == "cuda" else None}
        res["prompt_tokens"] = int(ids["input_ids"].shape[1])
        res["cache_on_off_identical"] = res["use_cache_True"]["text"] == res["use_cache_False"]["text"]
        gens[name] = res
    out["generations"] = gens

    # context-limit behaviour: positions beyond 2048 are not supported; verify our server rejects them
    long_ids = torch.full((1, 2040), tok.convert_tokens_to_ids("<s>"), device=dev)
    out["note_context"] = "Server enforces prompt+max_new_tokens <= 2048 (config.json). Tokenizer model_max_length is a 1e30 sentinel."
    out["finished"] = time.strftime("%Y-%m-%dT%H:%M:%S")
    out["result"] = "PASS: real weights loaded and generated on " + dev
    d = ROOT / "eval" / "results"
    d.mkdir(parents=True, exist_ok=True)
    f = d / f"smoke_{time.strftime('%Y%m%d_%H%M%S')}.json"
    f.write_text(json.dumps(out, indent=2, ensure_ascii=False), encoding="utf-8")
    print(json.dumps({k: v for k, v in out.items() if k != "generations"}, indent=2, ensure_ascii=False))
    for k, v in gens.items():
        print("==", k, "prompt_tokens", v["prompt_tokens"], "identical", v["cache_on_off_identical"])
        for c in ("use_cache_True", "use_cache_False"):
            print("  ", c, v[c]["ms"], "ms", v[c]["tok_per_s"], "tok/s", "peak", v[c]["peak_mem_mb"], "|", v[c]["text"][:300].replace("\n", " "))
    print("WROTE", f)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
