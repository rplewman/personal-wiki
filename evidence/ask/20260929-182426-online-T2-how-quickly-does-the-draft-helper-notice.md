# Ask: How quickly does the draft helper notice a new pick?

- Time: 2026-09-29T18:24:26
- Model: `gemma4:e2b-it-qat` | wall 25.37 s | 1348 prompt + 72 output tokens | 24.1 tok/s | model in memory 3.9 GB | RAM free 1.9/16.7 GB
- Retrieval: hybrid (BM25 + embeddinggemma)
- Citation check: cites S1, S2, S3

## Answer

The application fetches picks every 3 seconds [S1][S3]. Sleeper's CDN caches the picks endpoint for up to 30 seconds, meaning a new pick can take about 30 seconds to appear [S1]. The application also tracks every pick in real time and recommends who to take next [S2][S3].

## Retrieved sources

- [S1] `raw/Draft Copilot.md` :: Features
- [S2] `wiki/Concepts/Draft Tracking System.md` :: In [[Draft Copilot]]
- [S3] `wiki/Projects/Draft Copilot.md` :: Key points
- [S4] `wiki/Projects/Draft Copilot.md` :: Concepts
- [S5] `raw/Draft Copilot.md` :: Bugs Found and Fixed
- [S6] `wiki/Projects/Draft Copilot.md` :: Key points
- [S7] `raw/Draft Copilot.md` :: Approach > Choosing the architecture
- [S8] `wiki/Concepts/Expert Consensus Rankings.md` :: In [[Draft Copilot]]

## Raw model output (before citation check)

The application fetches picks every 3 seconds [S1, S3]. Sleeper's CDN caches the picks endpoint for up to 30 seconds, meaning a new pick can take about 30 seconds to appear [S1]. The application also tracks every pick in real time and recommends who to take next [S2, S3].
