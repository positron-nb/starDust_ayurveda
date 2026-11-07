# Third-party components

Components actually used by PRAMAAN (versions pinned in `backend/requirements.lock.txt` and
`frontend/package-lock.json`). Licences as stated by each project; verify before redistribution.

## Models
| Component | Use | Licence |
|---|---|---|
| bharatgenai/AyurParam @ 27c69eeef492bbc9e2c0048fc1e95959ffc0820e | Core domain model: query/concept expansion and per-passage explanations | HF metadata: Apache-2.0 (model card badge shows CC-BY-4.0 — conflict recorded in DATA_NOTICE.md). Custom code `modeling_parambharatgen.py` (sha256 4745b5bc…) and `config_parambharatgen.py` (9d89451d…) reviewed before `trust_remote_code`. |
| intfloat/multilingual-e5-small @ 614241f622f53c4eeff9890bdc4f31cfecc418b3 | Dense passage/query embeddings (`query:` / `passage:` prefixes, 512-token limit, normalised) | MIT |

## Python
| Package | Licence |
|---|---|
| PyTorch 2.7.1 (+cu128) | BSD-3-Clause |
| transformers 4.53.1, tokenizers 0.21.2, safetensors, accelerate, huggingface_hub | Apache-2.0 |
| sentence-transformers 4.1.0 | Apache-2.0 |
| qdrant-client 1.14.2 (embedded local mode; Qdrant server in Docker Compose) | Apache-2.0 |
| rank-bm25 0.2.2 | Apache-2.0 |
| indic-transliteration 2.3.69 (script transliteration only — not translation) | MIT |
| lxml 5.4.0 | BSD-3-Clause |
| FastAPI 0.115, Starlette, Uvicorn, Pydantic 2, httpx | MIT / BSD |
| PyYAML | MIT |
| pytest | MIT |

## JavaScript
| Package | Licence |
|---|---|
| React 18.3.1, React DOM | MIT |
| Vite 5, @vitejs/plugin-react | MIT |
| Tailwind CSS 3.4, PostCSS, Autoprefixer | MIT |
| TypeScript 5.6 | Apache-2.0 |

## Fonts (loaded from Google Fonts at runtime; system fallbacks offline)
Noto Sans, Noto Sans Devanagari, Noto Serif Devanagari — SIL Open Font License 1.1.

## Not used (inspected as inspiration only)
LightRAG (MIT) and Ragas (Apache-2.0) were considered. No code was copied from either. Ragas is not
a dependency; PRAMAAN's evaluation is a self-contained runner with explicit "not measured" states.
