# Ask: How quickly does the draft helper notice a new pick?

- Time: 2026-09-29T20:28:47
- Model: `gemma4:e2b-it-qat` | wall 18.99 s | 1215 prompt + 56 output tokens | 22.0 tok/s | model in memory 3.9 GB | RAM free 2.2/16.7 GB
- Retrieval: hybrid (BM25 + embeddinggemma)
- Citation check: cites S1, S2, S7

## Answer

The app fetches picks every 3 seconds [S1][S2]. Sleeper's CDN caches the picks endpoint for up to 30 seconds, meaning a new pick can take about 30 seconds to appear [S1][S2][S7].

## Retrieved sources

- [S1] `raw/Draft Copilot.md` :: Features
- [S2] `wiki/Projects/Draft Copilot.md` :: Key points
- [S3] `raw/Draft Copilot.md` :: Bugs Found and Fixed
- [S4] `wiki/Projects/Draft Copilot.md` :: Details > Bugs Found and Fixed
- [S5] `raw/Draft Copilot.md` :: Approach > Choosing the architecture
- [S6] `wiki/Projects/Draft Copilot.md` :: Summary
- [S7] `wiki/Concepts/Caching.md` :: In [[Draft Copilot]]
- [S8] `wiki/Shared Themes.md` :: Combining several sources into one recommendation

## Raw model output (before citation check)

The app fetches picks every 3 seconds [S1, S2]. Sleeper's CDN caches the picks endpoint for up to 30 seconds, meaning a new pick can take about 30 seconds to appear [S1, S2, S7].
