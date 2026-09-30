# Ask: Which hosting platform comes up across my app projects, and did each one end up using it?

- Time: 2026-09-29T18:45:44
- Model: `gemma4:e2b-it-qat` | wall 9.73 s | 1184 prompt + 80 output tokens | 26.1 tok/s | model in memory 3.9 GB | RAM free 1.9/16.7 GB
- Retrieval: hybrid (BM25 + embeddinggemma)
- Citation check: cites S1, S7

## Answer

The GRKN is planned to be hosted on Vercel, and it is planned to be installed on both iPhones from the Vercel URL [S1]. The Breakaway Project plans Vercel for the frontend and Railway for the backend [S1]. The technical architecture section indicates Vercel for the frontend and Railway for the backend for simple deployment for the MVP [S7].

## Retrieved sources

- [S1] `wiki/Shared Themes.md` :: Hosting on Vercel
- [S2] `raw/PLAN.md` :: Decisions (confirmed)
- [S3] `raw/Draft Copilot.md` :: Approach > Choosing the architecture
- [S4] `raw/PLAN.md` :: Build order
- [S5] `raw/Draft Copilot.md` :: Lessons
- [S6] `wiki/Shared Themes.md` :: Shared Themes
- [S7] `raw/Breakaway_PRD_v3.0.md` :: 10. Technical Architecture > 10.1 Stack
- [S8] `raw/PLAN.md` :: Keeping the build efficient (Claude Code token use)
