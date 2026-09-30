# Ask: How quickly does the draft helper notice a new pick?

- Time: 2026-09-29T18:45:30
- Model: `gemma4:e2b-it-qat` | wall 19.13 s | 1317 prompt + 50 output tokens | 23.2 tok/s | model in memory 3.9 GB | RAM free 1.8/16.7 GB
- Retrieval: hybrid (BM25 + embeddinggemma)
- Citation check: cites S1, S6, S7

## Answer

The app fetches picks every 3 seconds [S6]. Sleeper's CDN caches the picks endpoint for up to 30 seconds, meaning a new pick can take about 30 seconds to appear [S1][S7].

## Retrieved sources

- [S1] `raw/Draft Copilot.md` :: Features
- [S2] `raw/Draft Copilot.md` :: Bugs Found and Fixed
- [S3] `wiki/Projects/Draft Copilot.md` :: Key points
- [S4] `raw/Draft Copilot.md` :: Features
- [S5] `wiki/Projects/Draft Copilot.md` :: Concepts
- [S6] `wiki/Projects/Draft Copilot.md` :: Key points
- [S7] `wiki/Concepts/Caching.md` :: In [[Draft Copilot]]
- [S8] `wiki/Shared Themes.md` :: Combining several sources into one recommendation

## Raw model output (before citation check)

The app fetches picks every 3 seconds [S6]. Sleeper's CDN caches the picks endpoint for up to 30 seconds, meaning a new pick can take about 30 seconds to appear [S1, S7].
