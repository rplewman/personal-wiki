# Ask: Which hosting platform comes up across my app projects, and did each one end up using it?

- Time: 2026-09-29T22:54:55
- Route: per-project: 3 calls
- Model: `gemma4:e2b-it-qat` | 3 calls (totals) | wall 26.19 s | 1837 prompt + 66 output tokens | 27.8 tok/s | model in memory 3.9 GB | RAM free 2.8/16.7 GB
- Retrieval: hybrid (BM25 + embeddinggemma)
- Citation check: Draft Copilot: cites S1, S3 | The GRKN: cites S4 | Breakaway Project: cites S7

## Answer

**Draft Copilot:** Vercel hosting was considered for the project but was dropped in favor of running the application locally [S1][S3].
**The GRKN:** The application is hosted on Vercel [S4].
**Breakaway Project:** The hosting platform mentioned for the Breakaway Project is Vercel for the frontend and Railway for the backend [S7].

## Retrieved sources

- [S1] `wiki/Projects/Draft Copilot.md` :: Review (2026-09-29, after the offline re-ingest)
- [S2] `wiki/Concepts/Caching.md` :: In [[Draft Copilot]]
- [S3] `raw/Draft Copilot.md` :: Approach > Choosing the architecture
- [S4] `raw/PLAN.md` :: Decisions (confirmed)
- [S5] `raw/PLAN.md` :: Build order
- [S6] `raw/PLAN.md` :: Verification
- [S7] `raw/Breakaway_PRD_v3.0.md` :: 10. Technical Architecture > 10.1 Stack
- [S8] `raw/Breakaway_PRD_v3.0.md` :: 3. Product Vision & Goals > 3.3 What Breakaway Is and Is Not
- [S9] `wiki/Projects/Breakaway Project.md` :: Details > 4. Race-Specific Onboarding Questionnaire

## Raw model output (before citation check)

**Draft Copilot:** Vercel hosting was considered for the project but was dropped in favor of running the application locally [S1, S3].
**The GRKN:** The application is hosted on Vercel [S4].
**Breakaway Project:** The hosting platform mentioned for the Breakaway Project is Vercel for the frontend and Railway for the backend [S7].
