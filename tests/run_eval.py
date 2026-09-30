"""Run the 4 ask tests and the mode checks, saving everything under evidence/.
    .venv\\Scripts\\python.exe tests\\run_eval.py --label online     (or --label offline)"""
import argparse
import datetime as dt
import re
import sys
from pathlib import Path

import yaml

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from wiki import llm  # noqa: E402
from wiki.answer import Chat, ask  # noqa: E402
from wiki.config import EVIDENCE_DIR  # noqa: E402
from wiki.evidence import save_ask, save_chat  # noqa: E402
from wiki.retrieval import Retriever  # noqa: E402


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--label", required=True, help="online or offline")
    a = ap.parse_args()
    folder = "offline" if a.label == "offline" else "ask"
    mode_folder = "offline" if a.label == "offline" else "mode-checks"
    tests = yaml.safe_load((Path(__file__).parent / "questions.yaml").read_text(encoding="utf-8"))
    r = Retriever()
    out = [f"# Evaluation run ({a.label})", "", f"- Time: {dt.datetime.now().isoformat(timespec='seconds')}",
           f"- Ollama reachable: {llm.is_up()}", f"- Memory: {llm.system_memory()}", "", "## Ask tests", ""]

    for t in tests:
        print(f"{t['id']}: {t['question']}", flush=True)
        res = ask(t["question"], retriever=r)
        p = save_ask(res, folder=folder, label=f"{a.label}-{t['id']}")
        cited = sorted({res["sources"][int(n) - 1].path for n in re.findall(r"\[S(\d+)\]", res["answer"])})
        out += [f"### {t['id']} ({t['kind']}): {t['question']}", "", f"**Answer:** {res['answer']}", "",
                f"- Expected: {t['expected_behaviour'].strip()}", f"- Expected sources: {', '.join(t['expected_sources'])}",
                f"- Cited sources: {', '.join(cited) or 'none'}", f"- Citation check: {res['check']}",
                f"- Time: {res['stats']['wall_s'] if res['stats'] else '-'} s | evidence: `{p.relative_to(EVIDENCE_DIR.parent).as_posix()}`", ""]

    out += ["## Mode checks", ""]
    # 1. chat describes itself, drafts, then revises using the conversation
    print("chat: capabilities + draft + shorter", flush=True)
    c = Chat(retriever=r)
    for m in ["What can you help me with?",
              "Draft a short paragraph introducing my Draft Copilot project for my portfolio.",
              "Make that shorter."]:
        c.send(m)
    p = save_chat(c.history, folder=mode_folder, label=f"{a.label}-chat-capabilities-draft-shorter")
    out += [f"- Chat capabilities, draft and 'make that shorter': `{p.relative_to(EVIDENCE_DIR.parent).as_posix()}`"]

    # 2. search returns passages with no generated answer
    print("search", flush=True)
    hits = r.search("Draft Copilot polling interval", k=4)
    lines = ["# Search check (no model answer)", "", "Query: `wiki search Draft Copilot polling interval`",
             f"Note: {r.note or 'hybrid'}", ""] + [f"{n}. `{h.chunk.path}` :: {h.chunk.section}\n   {h.chunk.text[:200].replace(chr(10), ' ')}"
                                                   for n, h in enumerate(hits, 1)]
    sp = EVIDENCE_DIR / mode_folder / f"{dt.datetime.now():%Y%m%d-%H%M%S}-{a.label}-search-no-answer.md"
    sp.write_text("\n".join(lines) + "\n", encoding="utf-8")
    out += [f"- Search with no generated answer: `{sp.relative_to(EVIDENCE_DIR.parent).as_posix()}`"]

    # 3. a claim made only in chat must not become evidence for ask
    print("chat claim vs ask", flush=True)
    c2 = Chat(retriever=r)
    c2.send("Just so you know, I decided Breakaway will cost $9 per month.")
    p1 = save_chat(c2.history, folder=mode_folder, label=f"{a.label}-chat-claim")
    res = ask("What monthly subscription price was chosen for Breakaway?", retriever=r)
    p2 = save_ask(res, folder=mode_folder, label=f"{a.label}-after-chat-claim")
    out += [f"- Chat claim '$9 per month' then ask about the price: `{p1.relative_to(EVIDENCE_DIR.parent).as_posix()}`, "
            f"`{p2.relative_to(EVIDENCE_DIR.parent).as_posix()}`",
            f"  - Ask answer: {res['answer']}", f"  - '$9' appears in the ask answer: {bool(re.search(r'[$]9(?![0-9])', res['answer']))}"]

    summary = EVIDENCE_DIR / f"eval-{a.label}-{dt.datetime.now():%Y%m%d-%H%M%S}.md"
    summary.write_text("\n".join(out) + "\n", encoding="utf-8")
    print(f"Summary: {summary}")


if __name__ == "__main__":
    main()
