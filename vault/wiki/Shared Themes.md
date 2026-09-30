# Shared Themes

Hand-written on 2026-09-29. Links between my three app projects, each backed by the raw source. The automatic connect step in `wiki ingest` did not find reliable shared themes (see README, limitation), so these links are written by hand.

## Hosting on Vercel
- [[The GRKN]] is planned to be hosted on Vercel, and installed on both iPhones from the Vercel URL ([[raw/PLAN#Decisions (confirmed)|PLAN.md § Decisions]]).
- [[Breakaway Project]] plans Vercel for the frontend and Railway for the backend ([[raw/Breakaway_PRD_v3.0#10.1 Stack|PRD § 10.1 Stack]]).
- [[Draft Copilot]] considered Vercel hosting and dropped it in favour of running locally ([[raw/Draft Copilot#Choosing the architecture|Draft Copilot.md § Choosing the architecture]]).

## Claude inside the app
- [[The GRKN]] uses Claude to generate recipes and to check imported ones ([[raw/PLAN|PLAN.md]]).
- [[Breakaway Project]] passes structured data summaries to Claude, which returns plan adjustments and coaching notes; raw data is never passed directly ([[raw/Breakaway_PRD_v3.0|Breakaway_PRD_v3.0.md]]).

## Combining several sources into one recommendation
- [[Breakaway Project]] aggregates wearable data (Whoop, Strava) into one daily recommendation ([[Athlete Data Layer]]).
- [[Draft Copilot]] blends FantasyPros consensus and ESPN rankings to recommend the next pick ([[Expert Consensus Rankings]]).
