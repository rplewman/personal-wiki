---
type: concept
sources:
- raw/PLAN.md
generated_by: wiki ingest
updated: '2026-09-29T17:45:44'
---

# Recipe Generation Integration

> Concept page assembled by `wiki ingest` from facts local Gemma found in each source. Mentioned in 1 source.

## In [[The GRKN]]
The system uses the Claude integration with structured output to generate valid, typed recipes, incorporating rules about gluten risk and household taste profiles.

- The Claude integration uses the `@anthropic-ai/sdk` with structured output for valid, typed recipes. ([[raw/PLAN#Claude integration (`convex/ai.ts`, a Node server function)|§ Claude integration (`convex/ai.ts`, a Node server function)]])
- The system prompt always includes the gluten rule requiring Claude to set `glutenRisk` for every ingredient. ([[raw/PLAN#Claude integration (`convex/ai.ts`, a Node server function)|§ Claude integration (`convex/ai.ts`, a Node server function)]])
- The system prompt also includes the household taste profile summary and dislikes. ([[raw/PLAN#Claude integration (`convex/ai.ts`, a Node server function)|§ Claude integration (`convex/ai.ts`, a Node server function)]])

<!-- Human notes: anything below this line is kept when the page is re-ingested. -->
