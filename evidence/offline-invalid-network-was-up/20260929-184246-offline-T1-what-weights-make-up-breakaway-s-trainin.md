# Ask: What weights make up Breakaway's training readiness score?

- Time: 2026-09-29T18:42:46
- Model: `gemma4:e2b-it-qat` | wall 26.94 s | 1354 prompt + 67 output tokens | 23.2 tok/s | model in memory 3.9 GB | RAM free 1.5/16.7 GB
- Retrieval: embeddings missing (run `wiki index` with Ollama running); using BM25 only
- Citation check: cites S3

## Answer

The weights for the input signals that synthesize into a single 0–100 score for Breakaway's training readiness score are: Recovery / HRV at 45% [S3], Training Load Balance at 35% [S3], and Nutrition / Carb Availability at 20% [S3].

## Retrieved sources

- [S1] `wiki/Projects/Breakaway Project.md` :: Details > 6. Daily Coaching Experience
- [S2] `raw/Breakaway_PRD_v3.0.md` :: 6. Daily Coaching Experience > 6.1 Training Readiness Score
- [S3] `raw/Breakaway_PRD_v3.0.md` :: 6. Daily Coaching Experience > 6.1 Training Readiness Score
- [S4] `wiki/Projects/Breakaway Project.md` :: Key points
- [S5] `raw/Breakaway_PRD_v3.0.md` :: Appendix A: Glossary
- [S6] `wiki/Projects/Breakaway Project.md` :: Summary
- [S7] `raw/Draft Copilot.md` :: Approach > Rankings dataset
- [S8] `wiki/Breakaway PRD Review Notes.md` :: Changes made during conversion
