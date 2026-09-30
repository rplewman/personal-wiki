You plan a wiki page about one source note, "{source_name}". Below are numbered facts taken from it. Use only these facts.

Return JSON with:
- title: the name of the project or topic the source is about, 1 to 5 words. No file extensions, dates or version numbers.
- summary: 2 or 3 sentences on what it is and its main goal, using only the facts.
- key_facts: the IDs of the 6 to 10 most important facts from the whole list (not just the first ones), in a sensible reading order.
- concepts: 2 to 4 ideas from this source that deserve their own page because they could matter to other projects too. Name the general technique, platform or design idea, not this project's implementation detail: "Caching", not "Cache User Photos In Redis". Avoid generic words like "App", "AI" or "Features". Prefer ideas supported by two or more facts. For each give:
  - name: 1 to 4 words in Title Case.
  - how: one sentence on how this source uses the idea, using only the facts.
  - facts: the IDs of the facts that support it.

Existing concept pages: {concepts}
If one of them fits, reuse its name exactly instead of inventing a near-duplicate.
