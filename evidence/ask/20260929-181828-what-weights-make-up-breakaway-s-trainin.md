# Ask: What weights make up Breakaway's training readiness score?

- Time: 2026-09-29T18:18:28
- Model: `gemma4:e2b-it-qat` | wall 19.64 s | 1169 prompt + 84 output tokens | 24.6 tok/s | model in memory 3.9 GB | RAM free 1.6/16.7 GB
- Retrieval: hybrid (BM25 + embeddinggemma)
- Citation check: cites S1

## Answer

The weights for Breakaway's training readiness score are as follows: Recovery / HRV has a weight of 45% [S1]. Training Load Balance has a weight of 35%, derived from CTL vs. ATL from Strava + Garmin power data [S1]. Nutrition / Carb Availability has a weight of 20%, which is estimated from training load if nothing is logged [S1].

## Retrieved sources

- [S1] `raw/Breakaway_PRD_v3.0.md` :: 6. Daily Coaching Experience > 6.1 Training Readiness Score
- [S2] `raw/Breakaway_PRD_v3.0.md` :: 6. Daily Coaching Experience > 6.1 Training Readiness Score
- [S3] `wiki/Projects/Breakaway Project.md` :: Key points
- [S4] `wiki/Projects/Breakaway Project.md` :: Details > 6. Daily Coaching Experience
- [S5] `raw/Breakaway_PRD_v3.0.md` :: Appendix A: Glossary
- [S6] `wiki/Projects/Breakaway Project.md` :: Summary
