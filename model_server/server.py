"""AyurParam inference service (separate process so the API/UI never depends on loading weights).

    python model_server/server.py            # binds 127.0.0.1:8601 by default

Security: binds to localhost by default; no auth is provided, so do not expose it publicly.
trust_remote_code is enabled ONLY for the pinned revision whose modeling/config files were
reviewed (imports limited to torch/transformers; no I/O or network code).
"""
from __future__ import annotations

import os
import threading
import time
from pathlib import Path

import torch
import uvicorn
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field

MODEL_ID = "bharatgenai/AyurParam"
REVISION = "27c69eeef492bbc9e2c0048fc1e95959ffc0820e"
CONTEXT_LIMIT = 2048  # config.json max_position_embeddings at REVISION
LOCAL_DIR = Path(os.environ.get("AYURPARAM_LOCAL_DIR", Path(__file__).resolve().parents[1] / "models" / "AyurParam"))
# Hashes of the reviewed remote-code files (sha256), checked before trust_remote_code.
REVIEWED_CODE = {
    "modeling_parambharatgen.py": "4745b5bc5596aa906ce880c14d15bdc3197cd04337e7685ebbed4d4f9ea719b5",
    "config_parambharatgen.py": "9d89451dabb06aa289b35d48fc24bc8d0818d48fe51cad80c5d21df95abed3eb",
}

state: dict = {"loaded": False, "loading": False, "error": None, "device": None, "dtype": None, "load_s": None,
               "use_cache": None}
_lock = threading.Lock()
app = FastAPI(title="AyurParam model server")


def _sha256(p: Path) -> str:
    import hashlib

    return hashlib.sha256(p.read_bytes()).hexdigest()


def pick_device_dtype():
    forced = os.environ.get("AYURPARAM_DEVICE")
    if forced == "cpu" or not torch.cuda.is_available():
        dt = torch.bfloat16 if os.environ.get("AYURPARAM_CPU_BF16") == "1" else torch.float32
        return "cpu", dt
    major, _ = torch.cuda.get_device_capability(0)
    return "cuda", (torch.bfloat16 if major >= 8 else torch.float16)


def load():
    from transformers import AutoModelForCausalLM, AutoTokenizer

    state["loading"] = True
    t0 = time.time()
    try:
        src = str(LOCAL_DIR) if (LOCAL_DIR / "config.json").exists() else MODEL_ID
        kw = {} if src == str(LOCAL_DIR) else {"revision": REVISION}
        if src == str(LOCAL_DIR):
            for fname, expected in REVIEWED_CODE.items():
                if expected and _sha256(LOCAL_DIR / fname) != expected:
                    raise RuntimeError(f"{fname} hash differs from reviewed hash; refusing trust_remote_code")
        device, dtype = pick_device_dtype()
        tok = AutoTokenizer.from_pretrained(src, trust_remote_code=False, **kw)
        model = AutoModelForCausalLM.from_pretrained(src, trust_remote_code=True, torch_dtype=dtype,
                                                     low_cpu_mem_usage=True, **kw)
        model.to(device)
        model.eval()
        state.update(tok=tok, model=model, device=f"{device}:{torch.cuda.get_device_name(0)}" if device == "cuda" else "cpu",
                     dtype=str(dtype).replace("torch.", ""), loaded=True, load_s=round(time.time() - t0, 1),
                     use_cache=os.environ.get("AYURPARAM_USE_CACHE", "1") == "1")
    except Exception as e:  # surfaced via /health
        state["error"] = f"{type(e).__name__}: {e}"[:500]
    finally:
        state["loading"] = False


class GenReq(BaseModel):
    prompt: str = Field(..., max_length=20000)
    max_new_tokens: int = Field(256, ge=1, le=512)
    repetition_penalty: float = Field(1.15, ge=1.0, le=2.0)


@app.get("/health")
def health():
    out = {k: v for k, v in state.items() if k not in ("tok", "model")}
    # 'loaded' alone is not enough: a broken CUDA context means generation cannot succeed.
    out["loaded"] = bool(state.get("loaded")) and not state.get("cuda_broken", False)
    out.update(model_id=MODEL_ID, revision=REVISION, context_limit=CONTEXT_LIMIT,
               torch=torch.__version__, cuda=torch.version.cuda)
    if torch.cuda.is_available():
        out["gpu_mem_allocated_mb"] = round(torch.cuda.memory_allocated() / 2**20)
    return out


@app.post("/generate")
def generate(req: GenReq):
    if not state["loaded"] or state.get("cuda_broken"):
        raise HTTPException(503, detail=state.get("last_error") or state["error"] or "model loading")
    tok, model = state["tok"], state["model"]
    ids = tok(req.prompt, return_tensors="pt", add_special_tokens=False)
    n = ids["input_ids"].shape[1]
    if n + req.max_new_tokens > CONTEXT_LIMIT:
        raise HTTPException(422, detail=f"prompt {n} + max_new_tokens {req.max_new_tokens} exceeds {CONTEXT_LIMIT}")
    dev = "cuda" if state["device"].startswith("cuda") else "cpu"
    ids = {k: v.to(dev) for k, v in ids.items()}
    eos = list({tok.eos_token_id, 3, tok.convert_tokens_to_ids("</actual_response>")} - {None})
    t0 = time.perf_counter()
    with _lock:
        try:
            with torch.inference_mode():
                out = model.generate(**ids, max_new_tokens=req.max_new_tokens, do_sample=False,
                                     repetition_penalty=req.repetition_penalty, eos_token_id=eos,
                                     pad_token_id=tok.pad_token_id, use_cache=state["use_cache"])
        except (torch.OutOfMemoryError, RuntimeError) as e:
            # Release cached blocks and report honestly; a sticky CUDA error marks the server unhealthy.
            state["failures"] = state.get("failures", 0) + 1
            state["last_error"] = f"{type(e).__name__}: {str(e)[:200]}"
            if dev == "cuda":
                try:
                    torch.cuda.empty_cache()
                    torch.zeros(1, device="cuda").sum().item()  # probe: is the CUDA context still usable?
                except Exception:
                    state["cuda_broken"] = True
            raise HTTPException(503, detail="generation failed: " + state["last_error"])
        finally:
            if dev == "cuda":
                torch.cuda.empty_cache()
    ms = (time.perf_counter() - t0) * 1000
    gen = out[0][n:]
    text = tok.decode(gen, skip_special_tokens=False)
    for t in ("<s>", "</s>", "<actual_response>", "</actual_response>"):
        text = text.replace(t, "")
    return {"text": text.strip(), "prompt_tokens": n, "completion_tokens": int(gen.shape[0]), "ms": round(ms, 1),
            "model_id": MODEL_ID, "revision": REVISION, "device": state["device"], "dtype": state["dtype"],
            "decoding": {"do_sample": False, "repetition_penalty": req.repetition_penalty, "use_cache": state["use_cache"]}}


if __name__ == "__main__":
    threading.Thread(target=load, daemon=True).start()
    uvicorn.run(app, host=os.environ.get("AYURPARAM_HOST", "127.0.0.1"), port=int(os.environ.get("AYURPARAM_PORT", "8601")))
