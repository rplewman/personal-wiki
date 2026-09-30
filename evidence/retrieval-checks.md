# Retrieval checks (before involving Gemma)

Run on 2026-09-29, online, with `.venv\Scripts\python.exe tests\check_retrieval.py [--mode …] [--max-per-source …]`.
Index: 4 files (3 raw sources + 1 hand-written wiki page), 175 passages (82–796 chars, mean 536), embedded with `embeddinggemma:latest`.
A test passes when, for every expected source, a top-6 passage from that source contains all of its `retrieval_must_contain` strings (`tests/questions.yaml`).

## Run history (failures kept)

| # | Change | BM25 | Dense | Hybrid (RRF) | Notes |
|---|---|---|---|---|---|
| 1 | Baseline; T3 needle was just `"Vercel"` | 3/4 | 4/4 | 4/4 | The PLAN hit for T3 was the *Build order* chunk ("a Vercel project"), not the hosting decision, so the needle was too loose. |
| 2 | T3 needles tightened to the actual hosting sentences; H1 dropped from section paths | 3/4 | 4/4 | **3/4** | T3 hybrid FAIL: PLAN "Decisions" chunk was dense #2 but BM25 #47 ("hosting" ≠ "hosted"), so fused rank 9. |
| 3 | Light suffix stemming in BM25 tokenizer | 3/4 | 4/4 | **3/4** | PLAN now #1, but Breakaway §10.1 Stack fell out of top 6. The long PLAN crowded the list. |
| 4 | Per-source cap = 2 | – | – | 4/4 | T3 ranks: PLAN 1, Draft Copilot 3, PRD 5. |
| 5 | Per-source cap = 3 (**chosen default**) | 3/4 | 4/4 | **4/4** | T3 ranks: PLAN 1, Draft Copilot 4, PRD 6. Chosen over 2 so single-source questions keep more depth. |

BM25 alone fails T3 in every run (no Vercel hosting passage in its top 6). That's why hybrid is the default.

## Known fragility
With cap 3, T3's Breakaway passage is at rank 6 of 6, so the margin is small. Revisit once generated wiki pages are indexed, because they add more passages that could compete for the top 6.

Update, same day: once generated wiki pages and the hand-written `Shared Themes` note were indexed (282–290 passages), T3 failed at k=6. The Breakaway §10.1 passage was pushed out by two Shared Themes passages. Raising the default to k=8 gives 4/4 again, with the PRD at rank 7. Output of both runs: [retrieval-checks-k8.txt](retrieval-checks-k8.txt).

## Fallback
With Ollama unreachable (`WIKI_OLLAMA_URL=http://localhost:1`), `wiki search` prints
`[note] embedding model unavailable (OllamaUnavailable); using BM25 only` and still returns results.

## Gemma client smoke test (wiki/llm.py, think=false)
`{"wall_s": 20.36, "load_s": 15.14, "prompt_tokens": 19, "output_tokens": 43, "tok_per_s": 17.1, "model_loaded_gb": 3.9, "ram_available_gb": 0.2}`
It produced 43 output tokens for one sentence, compared with 343 in the setup smoke test with thinking on. Only 0.2 GB of system RAM was free while the model was loaded.
