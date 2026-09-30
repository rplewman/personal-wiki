---
type: concept
sources:
- raw/Draft Copilot.md
generated_by: wiki ingest
updated: '2026-09-29T20:23:16'
---

# Caching

> Concept page assembled by `wiki ingest` from facts local Gemma found in each source. Mentioned in 1 source.

## In [[Draft Copilot]]
Sleeper's CDN caches the picks endpoint for up to 30 seconds, which the application leverages.

- Sleeper's CDN caches the picks endpoint for up to 30 seconds. ([[raw/Draft Copilot#Features|§ Features]])

<!-- Human notes: anything below this line is kept when the page is re-ingested. -->
## Review (2026-09-29)
- Correction: the app does not "leverage" the cache. The 30-second CDN cache is a delay the app lives with, since it polls every 3 seconds.
