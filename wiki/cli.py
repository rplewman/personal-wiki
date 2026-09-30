"""Command-line entry point: `wiki <command>`."""
import argparse
import sys

from .config import TOP_K


def cmd_index(args):
    from .retrieval import build_index
    s = build_index()
    print(f"Indexed {s['files']} files into {s['chunks']} passages ({s['newly_embedded']} newly embedded).")
    if s["embed_error"]:
        print(f"Warning: embeddings not updated, BM25 only until fixed. {s['embed_error']}")


def cmd_search(args):
    from .retrieval import Retriever
    r = Retriever()
    hits = r.search(" ".join(args.query), k=args.k, mode=args.mode)
    if r.note:
        print(f"[note] {r.note}\n")
    if not hits:
        print("No matching passages.")
        return
    for n, h in enumerate(hits, 1):
        ranks = f"bm25 #{h.bm25_rank + 1 if h.bm25_rank is not None else '-'}, dense #{h.dense_rank + 1 if h.dense_rank is not None else '-'}"
        print(f"[{n}] {h.chunk.path} :: {h.chunk.section}  ({ranks})")
        body = h.chunk.text.replace("\n", " ")
        print(f"    {body[:args.chars]}{'…' if len(body) > args.chars else ''}\n")


def cmd_ask(args):
    from .answer import ask
    from .evidence import save_ask
    print("Searching your notes and asking Gemma (usually 20-40 s on this CPU)...", flush=True)
    res = ask(" ".join(args.question))
    print(res["answer"])
    if res["sources"]:
        print("\nSources:")
        for i, c in enumerate(res["sources"], 1):
            print(f"  [S{i}] {c.path} :: {c.section}")
    s = res["stats"]
    print(f"\n[{res['check']}]" + (f" [{s['wall_s']} s, {s['tok_per_s']} tok/s, RAM free {s['ram_available_gb']} GB]" if s else "")
          + f" [route: {res.get('route', 'single call')}]")
    if res["retrieval_note"]:
        print(f"[note] {res['retrieval_note']}")
    if not args.no_save:
        print(f"[saved {save_ask(res)}]")


CHAT_HELP = """Chat commands: /help this list, /clear forget the conversation, /exit end the chat (saves a transcript).
Other commands (run outside chat): wiki ask, wiki search, wiki ingest, wiki help."""


def cmd_chat(args):
    from .answer import Chat
    from .evidence import save_chat
    chat = Chat()
    print("Wiki chat (local Gemma, offline). " + CHAT_HELP.splitlines()[0])
    while True:
        try:
            msg = input("\nyou> ").strip()
        except (EOFError, KeyboardInterrupt):
            msg = "/exit"
        if not msg:
            continue
        if msg == "/help":
            print(CHAT_HELP)
            continue
        if msg == "/clear":
            chat.history.clear()
            print("Conversation cleared.")
            continue
        if msg == "/exit":
            if chat.history and not args.no_save:
                print(f"Transcript saved to {save_chat(chat.history, label=args.label)}")
            return
        print("  (thinking...)", flush=True)
        t = chat.send(msg)
        print(f"\nwiki> {t['reply']}")
        if t["sources"]:
            print("  notes: " + "; ".join(f"[S{i}] {c.path} :: {c.section}" for i, c in enumerate(t["sources"], 1)))
        print(f"  [{t['check']}; {t['stats']['wall_s']} s]")


def cmd_ingest(args):
    from .ingest import IngestError, ingest, load_catalog, render_all
    from .retrieval import build_index
    if args.render_only:
        render_all(load_catalog())
        print("Re-rendered wiki pages and vault/index.md from data/source_catalog.json (no model calls).")
        return
    try:
        results, shared = ingest(args.files, force=args.force, reconnect=args.connect)
    except IngestError as e:
        print(f"Error: {e}", file=sys.stderr)
        return
    for r in results:
        if r["status"] == "unchanged":
            print(f"{r['source']}: unchanged, page [[{r['page']}]] kept (use --force to regenerate).")
        else:
            print(f"{r['source']}: {r['status']} -> [[{r['page']}]]  {r['facts']} facts kept, {r['rejected']} items "
                  f"rejected, concepts: {', '.join(r['concepts']) or 'none'}  ({r['seconds']} s, log {r['log']})")
    if shared is not None:
        print(f"Shared themes linking projects: {', '.join(shared) or 'none found'}")
    s = build_index()
    print(f"vault/index.md rebuilt. Search index: {s['chunks']} passages ({s['newly_embedded']} newly embedded).")


def build_parser():
    p = argparse.ArgumentParser(
        prog="wiki",
        description="Personal Wiki: search and question your notes with local Gemma (Ollama), fully offline.",
    )
    sub = p.add_subparsers(dest="command", metavar="<command>")

    s = sub.add_parser("search", help="Show the passages that best match a query. No answer is generated; works without Gemma.")
    s.add_argument("query", nargs="+")
    s.add_argument("-k", type=int, default=TOP_K, help=f"number of passages (default {TOP_K})")
    s.add_argument("--mode", choices=["hybrid", "bm25", "dense"], default="hybrid")
    s.add_argument("--chars", type=int, default=240, help="characters of each passage to print")
    s.set_defaults(func=cmd_search)

    a = sub.add_parser("ask", help="Answer one question from your notes with citations [S1].. or 'insufficient evidence'. No chat history, no persona.")
    a.add_argument("question", nargs="+")
    a.add_argument("--no-save", action="store_true", help="do not save the answer to evidence/ask/")
    a.set_defaults(func=cmd_ask)

    c = sub.add_parser("chat", help="Talk with the wiki assistant: persona, remembers the last few turns, uses your notes when needed.")
    c.add_argument("--no-save", action="store_true", help="do not save the transcript to evidence/mode-checks/")
    c.add_argument("--label", default="chat", help="name used in the saved transcript file")
    c.set_defaults(func=cmd_chat)

    g = sub.add_parser("ingest", help="Turn raw sources into checked wiki pages with Gemma. No files = every new or changed file in vault/raw.")
    g.add_argument("files", nargs="*", help="source files (in vault/raw, or elsewhere to copy them in)")
    g.add_argument("--force", action="store_true", help="regenerate even if the source is unchanged")
    g.add_argument("--connect", action="store_true", help="re-run the shared-theme step even if no source changed")
    g.add_argument("--render-only", action="store_true", help="rebuild pages and index from the catalog without calling Gemma")
    g.set_defaults(func=cmd_ingest)

    i = sub.add_parser("index", help="Rebuild the search index from vault/raw and vault/wiki (embeds new passages only).")
    i.set_defaults(func=cmd_index)

    h = sub.add_parser("help", help="Show this help.")
    h.set_defaults(func=lambda a: p.print_help())
    return p


def main(argv=None):
    p = build_parser()
    args = p.parse_args(argv)
    if not getattr(args, "func", None):
        p.print_help()
        return 0
    from .llm import OllamaError
    try:
        args.func(args)
    except OllamaError as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1
    return 0
