# Ask: How quickly does the draft helper notice a new pick?

- Time: 2026-09-29T18:20:51
- Model: `gemma4:e2b-it-qat` | wall 20.03 s | 1395 prompt + 47 output tokens | 24.5 tok/s | model in memory 3.9 GB | RAM free 2.3/16.7 GB
- Retrieval: hybrid (BM25 + embeddinggemma)
- Citation check: cites S1

## Answer

The app fetches picks every 3 seconds [S1]. Sleeper's CDN caches the picks endpoint for up to 30 seconds, meaning a new pick can take about 30 seconds to appear [S1].

## Retrieved sources

- [S1] `raw/Draft Copilot.md` :: Features
- [S2] `wiki/Concepts/Draft Tracking System.md` :: In [[Draft Copilot]]
- [S3] `wiki/Projects/Draft Copilot.md` :: Key points
- [S4] `wiki/Projects/Draft Copilot.md` :: Concepts
- [S5] `raw/Draft Copilot.md` :: Bugs Found and Fixed
- [S6] `wiki/Projects/Draft Copilot.md` :: Key points
- [S7] `raw/Draft Copilot.md` :: Approach > Choosing the architecture
- [S8] `wiki/Concepts/Expert Consensus Rankings.md` :: In [[Draft Copilot]]
