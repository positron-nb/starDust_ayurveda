"""AyurParam inference-only Gradio Space for Hugging Face ZeroGPU (EXPERIMENT).

Exposes one function, `generate(prompt, max_new_tokens, repetition_penalty)`, with the same contract
as model_server/server.py /generate. Retrieval, ledger and safety stay in the PRAMAAN backend.

ZeroGPU pattern (per https://huggingface.co/docs/hub/spaces-zerogpu, read 2026-11-09):
`import spaces` first; model placed on 'cuda' at module level; GPU work inside @spaces.GPU.
Outside ZeroGPU the decorator is a no-op, so this file also runs on a normal local GPU for testing.
"""
import spaces  # noqa: I001  (must precede torch/CUDA usage on ZeroGPU)

import hashlib
import json
import os
import time
from pathlib import Path

import gradio as gr
import torch
from huggingface_hub import snapshot_download
from transformers import AutoModelForCausalLM, AutoTokenizer

MODEL_ID = "bharatgenai/AyurParam"
REVISION = "27c69eeef492bbc9e2c0048fc1e95959ffc0820e"
CONTEXT_LIMIT = 2048  # config.json max_position_embeddings at REVISION
MAX_NEW_TOKENS = 512
# sha256 of the remote-code files reviewed for PRAMAAN; loading is refused if they differ.
REVIEWED_CODE = {
    "modeling_parambharatgen.py": "4745b5bc5596aa906ce880c14d15bdc3197cd04337e7685ebbed4d4f9ea719b5",
    "config_parambharatgen.py": "9d89451dabb06aa289b35d48fc24bc8d0818d48fe51cad80c5d21df95abed3eb",
}

t0 = time.time()
LOCAL = Path(os.environ.get("AYURPARAM_LOCAL_DIR") or snapshot_download(
    MODEL_ID, revision=REVISION, allow_patterns=["*.json", "*.py", "*.safetensors"]))
for fname, expected in REVIEWED_CODE.items():
    got = hashlib.sha256((LOCAL / fname).read_bytes()).hexdigest()
    if got != expected:
        raise RuntimeError(f"{fname} sha256 {got} != reviewed {expected}; refusing trust_remote_code")

tok = AutoTokenizer.from_pretrained(str(LOCAL), trust_remote_code=False)
model = AutoModelForCausalLM.from_pretrained(str(LOCAL), trust_remote_code=True, torch_dtype=torch.bfloat16,
                                             low_cpu_mem_usage=True)
model.to("cuda")  # module level, as the ZeroGPU docs require
model.eval()
LOAD_S = round(time.time() - t0, 1)
EOS = list({tok.eos_token_id, 3, tok.convert_tokens_to_ids("</actual_response>")} - {None})


@spaces.GPU(duration=60)
def _run(prompt: str, max_new_tokens: int, repetition_penalty: float):
    ids = tok(prompt, return_tensors="pt", add_special_tokens=False).to("cuda")
    n = int(ids["input_ids"].shape[1])
    t = time.perf_counter()
    with torch.inference_mode():
        out = model.generate(**ids, max_new_tokens=max_new_tokens, do_sample=False, repetition_penalty=repetition_penalty,
                             eos_token_id=EOS, pad_token_id=tok.pad_token_id, use_cache=True)
    ms = (time.perf_counter() - t) * 1000
    gen = out[0][n:]
    text = tok.decode(gen, skip_special_tokens=False)
    for s in ("<s>", "</s>", "<actual_response>", "</actual_response>"):
        text = text.replace(s, "")
    return text.strip(), n, int(gen.shape[0]), ms, torch.cuda.get_device_name(0)


def generate(prompt: str, max_new_tokens: float = 256, repetition_penalty: float = 1.15) -> str:
    """Returns a JSON string: {text, prompt_tokens, completion_tokens, ms, model_id, revision, device, error}."""
    max_new_tokens = int(max_new_tokens)
    base = {"model_id": MODEL_ID, "revision": REVISION, "load_s": LOAD_S, "torch": torch.__version__}
    if not prompt or len(prompt) > 20000 or not (1 <= max_new_tokens <= MAX_NEW_TOKENS) or not (1.0 <= repetition_penalty <= 2.0):
        return json.dumps({**base, "error": "invalid request"})
    n = len(tok(prompt, add_special_tokens=False)["input_ids"])
    if n + max_new_tokens > CONTEXT_LIMIT:
        return json.dumps({**base, "error": f"prompt {n} + max_new_tokens {max_new_tokens} exceeds {CONTEXT_LIMIT}"})
    try:
        text, n, m, ms, dev = _run(prompt, max_new_tokens, repetition_penalty)
    except Exception as e:  # report, never hide
        return json.dumps({**base, "error": f"{type(e).__name__}: {str(e)[:300]}"})
    return json.dumps({**base, "text": text, "prompt_tokens": n, "completion_tokens": m, "ms": round(ms, 1), "device": dev,
                       "dtype": "bfloat16", "decoding": {"do_sample": False, "repetition_penalty": repetition_penalty}})


with gr.Blocks(title="AyurParam inference (PRAMAAN experiment)") as demo:
    gr.Markdown("AyurParam @ 27c69ee — raw inference endpoint for the PRAMAAN backend. Not a chatbot; no safety layer here. "
                "Use synthetic inputs only.")
    p = gr.Textbox(label="prompt", lines=6)
    k = gr.Number(label="max_new_tokens", value=128, precision=0)
    r = gr.Number(label="repetition_penalty", value=1.15)
    o = gr.Textbox(label="result (JSON)")
    gr.Button("Generate").click(generate, [p, k, r], o, api_name="generate")

if __name__ == "__main__":
    demo.queue(max_size=8).launch(server_name=os.environ.get("GRADIO_SERVER_NAME", "127.0.0.1"))
