# Ask: What weights make up Breakaway's training readiness score?

- Time: 2026-09-29T18:23:56
- Model: `gemma4:e2b-it-qat` | wall 19.99 s | 1250 prompt + 81 output tokens | 24.5 tok/s | model in memory 3.9 GB | RAM free 2.0/16.7 GB
- Retrieval: hybrid (BM25 + embeddinggemma)
- Citation check: cites S1

## Answer

The weights for Breakaway's training readiness score are: Recovery / HRV at 45% (Whoop (primary), Garmin body battery (secondary)) [S1], Training Load Balance at 35% (CTL vs. ATL from Strava + Garmin power data) [S1], and Nutrition / Carb Availability at 20% (Native macro logger) [S1].

## Retrieved sources

- [S1] `raw/Breakaway_PRD_v3.0.md` :: 6. Daily Coaching Experience > 6.1 Training Readiness Score
- [S2] `raw/Breakaway_PRD_v3.0.md` :: 6. Daily Coaching Experience > 6.1 Training Readiness Score
- [S3] `wiki/Projects/Breakaway Project.md` :: Key points
- [S4] `wiki/Projects/Breakaway Project.md` :: Details > 6. Daily Coaching Experience
- [S5] `raw/Breakaway_PRD_v3.0.md` :: Appendix A: Glossary
- [S6] `wiki/Projects/Breakaway Project.md` :: Summary
- [S7] `wiki/Concepts/Structured Onboarding Questionnaire.md` :: In [[Breakaway Project]]
- [S8] `wiki/Breakaway PRD Review Notes.md` :: Changes made during conversion
