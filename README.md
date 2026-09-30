# Personal Wiki: local Gemma + RAG

Class 5, Assignment 4. A personal wiki about three of my app projects. It has a small Python harness and a CLI (`chat`, `ask`, `search`, `ingest`, `help`), and it runs fully offline on local Gemma through Ollama. Only `vault/` is opened in Obsidian. Code, index, embeddings, logs, tests and evidence live outside it.

## Setup

Requirements: Windows, Python 3.12, and [Ollama](https://ollama.com) 0.34.3.

```bash
# while online, once
ollama pull gemma4:e2b-it-qat
ollama pull embeddinggemma
python -m venv .venv
.venv\Scripts\pip install rank-bm25 numpy requests PyYAML pypdf psutil
```

After that no network is needed. Start Ollama (the app, or `ollama serve`) and use `wiki.cmd`, or `.venv\Scripts\python.exe -m wiki` from any shell.

## Commands

| Command | What it does |
|---|---|
| `wiki help` | Lists the commands. |
| `wiki search Vercel hosting` | Prints the top passages with path, section and BM25/dense ranks. No answer is generated. It works without Gemma, and falls back to BM25 only if Ollama is down. |
| `wiki ask "What weights make up Breakaway's training readiness score?"` | Neutral answer with no history and no persona. It cites `[S1]…[Sn]` or says "Insufficient evidence." The harness removes citations to passages it didn't retrieve. Saved to `evidence/ask/`. |
| `wiki chat` | Persona from `prompts/persona.md` and the last 4 turns. It retrieves only when a turn needs the notes: questions about itself use no notes, and edits like "make that shorter" reuse the previous turn's notes. Commands: `/help`, `/clear`, `/exit`. The transcript is saved to `evidence/mode-checks/`. |
| `wiki ingest [file] [--force]` | Raw source → Gemma facts → harness checks → page in `vault/wiki/Projects/` plus concept pages and `vault/index.md`. Re-ingesting updates the same page (see `data/source_catalog.json`). |
| `wiki index` | Rebuilds the search index (only new passages are embedded). |

Evaluation: `.venv\Scripts\python.exe tests\run_eval.py --label online`. The offline run is `offline_run.cmd`, which refuses to start while the internet is reachable. The retrieval-only check is `tests\check_retrieval.py`.

## Model, runtime and device

| Item | Value |
|---|---|
| Generation model | `gemma4:e2b-it-qat`: Gemma 4 E2B instruction-tuned, quantization-aware-trained **Q4_0**, 4.3 GB on disk, about 3.9 GB loaded, context 4096, thinking off (`think: false`) |
| Embeddings | `embeddinggemma:latest` (768-dim) |
| Runtime | Ollama 0.34.3, `localhost:11434`, 100% CPU (the Intel Arc iGPU isn't used by Ollama) |
| Device | Intel Core Ultra 5 226V (8 cores), 15.5 GB RAM, Windows 11 Home |

The default `gemma4:e2b` tag is 7.2 GB, too heavy for this machine. The QAT Q4_0 build is the course's suggested E2B at Q4_0. Details: [evidence/device-and-model.md](evidence/device-and-model.md).

**Memory and timing (measured):** about 24 tok/s generation. Only **1.6–2.2 GB of RAM was free** while the model was loaded. Ask answers took 16–25 s online and 19–24 s offline. Chat turns took 6–16 s. The first call after a cold start adds about 12–15 s of model load. Ingest took 68–125 s for Draft Copilot, 361 s for The GRKN and 462 s for Breakaway (a 128-fact PRD).

## Architecture trace (`wiki ask`)

1. `wiki/cli.py` → `answer.ask(question)`.
2. `retrieval.Retriever.search`: `data/index.json` holds passages of about 800 characters, split by Markdown heading (`chunker.py`), from `vault/raw` and `vault/wiki`. BM25 (light stemming) and embeddinggemma cosine scores are fused with reciprocal rank fusion. A cap of 3 passages per file keeps one long source from crowding out the rest. Top 8.
3. The passages are labelled `[S1]…[S8]` with path and section (Obsidian link syntax stripped, 700 characters each) and sent with `prompts/wiki-instructions.md` to Gemma (`llm.py`: timing and memory stats, clear errors if Ollama or the model is missing).
4. `check_citations` normalises `[S1, S2]` and `[[S1]]`, removes citations to passages that weren't retrieved, and reports them (demonstrated without the model in [evidence/mode-checks/citation-check-unit.txt](evidence/mode-checks/citation-check-unit.txt)).
5. `evidence.py` writes the answer, sources, check result, time and memory to `evidence/`.

**Ingest** (`wiki/ingest.py`): Gemma extracts facts per section, with a JSON schema that has one required key per section label. The harness drops any fact whose numbers aren't in the cited section, plus near-duplicates. Gemma plans the title, summary, key facts and concepts from the numbered facts only. The harness picks file names (it uses the source's own name), renders every page with a link back to its `raw/` section, and keeps anything written below the human-notes marker. Human corrections live in `data/review.json`, so re-ingest can't erase them.

## Design choices

- **Hybrid retrieval, not BM25 alone.** BM25 alone failed the cross-source test in every run ("hosting" vs "hosted"). Run history: [evidence/retrieval-checks.md](evidence/retrieval-checks.md).
- **k raised from 6 to 8** once wiki pages were indexed, because they pushed out the Breakaway hosting passage ([retrieval-checks-k8.txt](evidence/retrieval-checks-k8.txt)).
- **The harness checks facts, not only the model.** Number checks, constrained IDs and citation filtering catch errors a 2B model makes. In review, 5 faulty facts on the GRKN page were corrected via `data/review.json`.
- **Sources are never edited.** Corrections and review notes go in `vault/wiki/`, for example `Breakaway PRD Review Notes` and the review section on `Draft Copilot`.
- **Sources are checked by hash.** Opening the vault in Obsidian rewrote the line endings of two raw files (CRLF to LF, same text). The hash check caught it, and the original bytes were restored so the sources match their ingest hashes.
- **Chat history is never evidence.** Ask has no history. Transcripts are saved outside the vault, so they're never indexed.

## Test results

Test questions and expected passages: [tests/questions.yaml](tests/questions.yaml). Full summaries: [online](evidence/eval-online-20260929-182625.md) and [offline](evidence/eval-offline-20260929-203048.md).

| Test | Online | Offline |
|---|---|---|
| T1 direct: readiness weights 45/35/20% | ✅ | ✅ |
| T2 paraphrased: "how quickly does it notice a pick" → 3 s polling, up to about 30 s CDN cache | ✅ | ✅ |
| T3 cross-source: Vercel across projects | 🟡 GRKN and Breakaway correct and cited; Draft Copilot ("considered and dropped") left out | 🟡 GRKN correct; Railway is attributed as if it were GRKN's backend; Draft Copilot left out |
| T4 unsupported: chosen price | 🟡 Says pricing is still open with options listed; doesn't claim a chosen price, but doesn't start with "Insufficient evidence" | 🟡 Same |
| Mode: "what can you help me with?" | ✅ Accurate list of commands | ✅ |
| Mode: draft, then "make that shorter" | 🟡 Shorter with the same facts, but the draft doesn't add `[S]` citations for facts taken from notes | 🟡 Same |
| Mode: search gives passages only | ✅ | ✅ |
| Mode: "$9/month" claimed in chat, then ask | ✅ Ask says insufficient evidence; $9 never appears | ✅ |

The first online run failed more (citation formats not parsed, T4 listing the options only). One fix pass followed (citation parsing, link stripping, a prompt rule for "what was chosen" questions), and both runs are kept in `evidence/`. An earlier "offline" run turned out to have the network up, so it's kept separately in `evidence/offline-invalid-network-was-up/` and not counted.

**Offline:** `offline_run.cmd` confirmed google.com was unreachable, then ran help, search, ingest of `Draft Copilot.md` and the full evaluation. Log: [evidence/offline/offline-run-log.txt](evidence/offline/offline-run-log.txt). Screenshot: [evidence/offline/offline-run-airplane-mode.png](evidence/offline/offline-run-airplane-mode.png).

## Obsidian

Screenshots in `evidence/screenshots/`: an open project note with its source links, the index, and the graph view filtered with `path:wiki/`, with attachments hidden and orphans shown.

## Limitation and proposed improvement

**Cross-source synthesis is weak.** Gemma E2B with a 4096-token context reliably answers single-source questions, but it loses one of three sources in T3 and once mixed two projects' facts. The same weakness showed up in ingest. An automatic "connect" step (themes proposed by Gemma, candidate facts retrieved, each supporting fact confirmed on its own with a quoted-evidence yes/no) was first too permissive (spurious links like "data aggregator implies tracking state"). After the per-fact check it was too strict, and no shared themes survived (`data/ingest_log/connect-*.json`). The shared themes are therefore a hand-written note (`vault/wiki/Shared Themes.md`). Project-specific concepts, such as `API Pre-Check`, are also weaker than general ones.

**Improvement:** answer cross-source questions per source, then merge. Retrieve per project, have Gemma answer the question for each project separately (short prompts, one source), then combine the per-project answers with a final call. Each call stays small enough for E2B on CPU, and the harness can check that every expected project appears in the final answer.
