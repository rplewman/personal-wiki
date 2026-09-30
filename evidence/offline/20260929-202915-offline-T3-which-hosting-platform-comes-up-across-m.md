# Ask: Which hosting platform comes up across my app projects, and did each one end up using it?

- Time: 2026-09-29T20:29:15
- Model: `gemma4:e2b-it-qat` | wall 24.26 s | 1188 prompt + 83 output tokens | 17.2 tok/s | model in memory 3.9 GB | RAM free 2.1/16.7 GB
- Retrieval: hybrid (BM25 + embeddinggemma)
- Citation check: cites S1, S2

## Answer

The Vercel hosting platform comes up in relation to the GRKN being planned for hosting [S1]. For the frontend, it is planned to be hosted on Vercel [S1], and the frontend uses Next.js (App Router) + TypeScript + Tailwind + shadcn/ui and is hosted on Vercel [S2]. The backend is planned to use Railway [S1].

## Retrieved sources

- [S1] `wiki/Shared Themes.md` :: Hosting on Vercel
- [S2] `raw/PLAN.md` :: Decisions (confirmed)
- [S3] `raw/Draft Copilot.md` :: Approach > Choosing the architecture
- [S4] `raw/PLAN.md` :: Build order
- [S5] `raw/Draft Copilot.md` :: Lessons
- [S6] `wiki/Concepts/Caching.md` :: In [[Draft Copilot]]
- [S7] `wiki/Shared Themes.md` :: Shared Themes
- [S8] `raw/Breakaway_PRD_v3.0.md` :: 10. Technical Architecture > 10.1 Stack
