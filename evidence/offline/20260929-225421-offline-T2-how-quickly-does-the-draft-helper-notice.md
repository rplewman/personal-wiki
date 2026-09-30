# Ask: How quickly does the draft helper notice a new pick?

- Time: 2026-09-29T22:54:21
- Route: answerability: yes
- Model: `gemma4:e2b-it-qat` | 2 calls (totals) | wall 33.49 s | 2533 prompt + 63 output tokens | 23.6 tok/s | model in memory 3.9 GB | RAM free 2.8/16.7 GB
- Retrieval: hybrid (BM25 + embeddinggemma)
- Citation check: cites S1, S2, S6

## Answer

The app fetches picks every 3 seconds [S1][S2]. Sleeper's CDN caches the picks endpoint for up to 30 seconds, meaning a new pick can take about 30 seconds to appear [S1][S2][S6].

## Retrieved sources

- [S1] `raw/Draft Copilot.md` :: Features
- [S2] `wiki/Projects/Draft Copilot.md` :: Details > Features
- [S3] `wiki/Concepts/Real-Time Tracking.md` :: In [[Draft Copilot]] *(linked by the connect step)*
- [S4] `raw/Draft Copilot.md` :: Bugs Found and Fixed
- [S5] `wiki/Projects/Draft Copilot.md` :: Key points
- [S6] `wiki/Concepts/Caching.md` :: In [[Draft Copilot]]
- [S7] `raw/Draft Copilot.md` :: Approach > Choosing the architecture
- [S8] `wiki/Projects/Draft Copilot.md` :: Key points

## Raw model output (before citation check)

The app fetches picks every 3 seconds [S1, S2]. Sleeper's CDN caches the picks endpoint for up to 30 seconds, meaning a new pick can take about 30 seconds to appear [S1, S2, S6].
