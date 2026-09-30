# Ask: How quickly does the draft helper notice a new pick?

- Time: 2026-09-29T22:38:17
- Route: answerability: yes
- Model: `gemma4:e2b-it-qat` | 2 calls (totals) | wall 32.52 s | 2391 prompt + 63 output tokens | 21.8 tok/s | model in memory 3.9 GB | RAM free 1.7/16.7 GB
- Retrieval: hybrid (BM25 + embeddinggemma)
- Citation check: cites S1, S2, S7

## Answer

The app fetches picks every 3 seconds [S1][S2]. Sleeper's CDN caches the picks endpoint for up to 30 seconds, meaning a new pick can take about 30 seconds to appear [S1][S2][S7].

## Retrieved sources

- [S1] `raw/Draft Copilot.md` :: Features
- [S2] `wiki/Projects/Draft Copilot.md` :: Key points
- [S3] `raw/Draft Copilot.md` :: Bugs Found and Fixed
- [S4] `wiki/Projects/Draft Copilot.md` :: Details > Bugs Found and Fixed
- [S5] `raw/Draft Copilot.md` :: Features
- [S6] `wiki/Projects/Draft Copilot.md` :: Summary
- [S7] `wiki/Concepts/Caching.md` :: In [[Draft Copilot]]
- [S8] `wiki/Shared Themes.md` :: Combining several sources into one recommendation

## Raw model output (before citation check)

The app fetches picks every 3 seconds [S1, S2]. Sleeper's CDN caches the picks endpoint for up to 30 seconds, meaning a new pick can take about 30 seconds to appear [S1, S2, S7].
