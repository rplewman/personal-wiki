# Search check (no model answer)

Query: `wiki search Draft Copilot polling interval`
Note: hybrid

1. `wiki/Projects/Draft Copilot.md` :: Review (2026-09-29, after the offline re-ingest)
   - All 20 points checked against [[raw/Draft Copilot|Draft Copilot.md]]: no invented facts. - Correction: the Caching line says the app "leverages" the CDN cache. It doesn't. The 30-second cache is a d
2. `raw/Draft Copilot.md` :: Features
   - **Live polling:** the app fetches picks every 3 seconds. Sleeper's CDN caches the picks endpoint for up to 30 seconds (`s-maxage=30`), so a new pick can take up to about 30 seconds to appear. That's
3. `wiki/Projects/Draft Copilot.md` :: Details > Features
   - The app fetches picks every 3 seconds. ([[raw/Draft Copilot#Features|§ Features]]) - Sleeper's CDN caches the picks endpoint for up to 30 seconds. ([[raw/Draft Copilot#Features|§ Features]]) - Best 
4. `wiki/Projects/Draft Copilot.md` :: Key points
   - The value model adds position scarcity as a secondary nudge to the raw consensus rank. ([[raw/Draft Copilot#The Value Model|§ The Value Model]]) - The fix for the 'My Team' empty issue is to identif
