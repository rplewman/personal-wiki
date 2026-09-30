# Device and Model Record

Recorded 2026-09-29 during setup (online).

## Device
| Item | Value |
|---|---|
| OS | Windows 11 Home 10.0.26200 |
| CPU | Intel Core Ultra 5 226V (8 cores / 8 threads) |
| RAM | 15.5 GB total (≈1.4 GB free at first check, with other apps open) |
| GPU | Intel Arc 130V integrated — shares system RAM, no dedicated VRAM |
| Free disk | 245 GB on C: |
| Python | 3.12.10 (venv in `.venv/`) |

## Runtime and models
| Item | Value |
|---|---|
| Runtime | Ollama 0.34.3 (local server at `http://localhost:11434`) |
| Generation model | `gemma4:e2b-it-qat` — Gemma 4 E2B instruction-tuned, quantization-aware-trained Q4_0, 4.3 GB on disk, digest `07ea59a47401` |
| Embedding model | `embeddinggemma:latest` — 768-dim, 621 MB, digest `85462619ee72` |
| Source | https://ollama.com/library/gemma4 and https://ollama.com/library/embeddinggemma |

## Why this model
- Default `gemma4:e2b` tag is Q4_K_M but 7.2 GB (bundles vision/audio towers and per-layer embeddings) — too heavy for 16 GB shared memory.
- The QAT Q4_0 build matches the course's "E2B at Q4_0" guidance and loads at ~3.9 GB.
- Ollama runs it 100% on CPU on this machine (Intel Arc iGPU not used), so the smaller model keeps latency usable.

## First smoke test (online, before harness)
- Prompt: "In one sentence, what is retrieval augmented generation?"
- Loaded size (`ollama ps`): 3.9 GB, 100% CPU, context 4096
- Wall time 32.2 s (includes cold model load), 343 generated tokens, 20.9 tok/s
- Observation: 343 tokens for one sentence indicates Gemma 4 thinking mode was on; harness will send `think: false`.
