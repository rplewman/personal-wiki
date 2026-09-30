# Ask: How quickly does the draft helper notice a new pick?

- Time: 2026-09-29T18:43:08
- Model: `gemma4:e2b-it-qat` | wall 19.82 s | 1383 prompt + 53 output tokens | 20.5 tok/s | model in memory 3.9 GB | RAM free 1.3/16.7 GB
- Retrieval: embeddings missing (run `wiki index` with Ollama running); using BM25 only
- Citation check: cites S1, S7

## Answer

The app fetches picks every 3 seconds [S1][S7]. Sleeper's CDN caches the picks endpoint for up to 30 seconds, meaning a new pick can take about 30 seconds to appear [S1][S7].

## Retrieved sources

- [S1] `raw/Draft Copilot.md` :: Features
- [S2] `wiki/Concepts/Draft Tracking System.md` :: In [[Draft Copilot]]
- [S3] `raw/Draft Copilot.md` :: Bugs Found and Fixed
- [S4] `wiki/Projects/Draft Copilot.md` :: Details > Bugs Found and Fixed
- [S5] `raw/Draft Copilot.md` :: Approach > Choosing the architecture
- [S6] `wiki/Projects/Draft Copilot.md` :: Details > Features
- [S7] `wiki/Projects/Draft Copilot.md` :: Key points
- [S8] `raw/PLAN.md` :: Screens (4 tabs at the bottom, big tap targets)

## Raw model output (before citation check)

The app fetches picks every 3 seconds [S1, S7]. Sleeper's CDN caches the picks endpoint for up to 30 seconds, meaning a new pick can take about 30 seconds to appear [S1, S7].
