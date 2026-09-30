"""Save ask answers and chat transcripts as Markdown evidence under evidence/ (outside the vault)."""
import datetime as dt
import re

from .config import EVIDENCE_DIR, GEN_MODEL


def _slug(text, n=40):
    return re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")[:n] or "item"


def _stats_line(stats):
    if not stats:
        return "- Model not called."
    calls = f" | {stats['calls']} calls (totals)" if stats.get("calls", 1) > 1 else ""
    return (f"- Model: `{GEN_MODEL}`{calls} | wall {stats['wall_s']} s | {stats['prompt_tokens']} prompt + "
            f"{stats['output_tokens']} output tokens | {stats['tok_per_s']} tok/s | model in memory "
            f"{stats['model_loaded_gb']} GB | RAM free {stats['ram_available_gb']}/{stats['ram_total_gb']} GB")


def save_ask(result, folder="ask", label=""):
    d = EVIDENCE_DIR / folder
    d.mkdir(parents=True, exist_ok=True)
    now = dt.datetime.now()
    path = d / f"{now:%Y%m%d-%H%M%S}-{label + '-' if label else ''}{_slug(result['question'])}.md"
    lines = [f"# Ask: {result['question']}", "", f"- Time: {now.isoformat(timespec='seconds')}",
             f"- Route: {result.get('route', 'single call')}",
             _stats_line(result["stats"]), f"- Retrieval: {result['retrieval_note'] or 'hybrid (BM25 + embeddinggemma)'}",
             f"- Citation check: {result['check']}", "", "## Answer", "", result["answer"], "", "## Retrieved sources", ""]
    lines += [f"- [S{i}] `{s.path}` :: {s.section}" for i, s in enumerate(result["sources"], 1)]
    if result["raw_answer"] != result["answer"]:
        lines += ["", "## Raw model output (before citation check)", "", result["raw_answer"]]
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return path


def save_chat(turns, folder="mode-checks", label="chat"):
    d = EVIDENCE_DIR / folder
    d.mkdir(parents=True, exist_ok=True)
    now = dt.datetime.now()
    path = d / f"{now:%Y%m%d-%H%M%S}-{label}.md"
    lines = [f"# Chat transcript ({label})", "", f"- Time: {now.isoformat(timespec='seconds')}", ""]
    for t in turns:
        lines += [f"**You:** {t['user']}", "", f"**Wiki:** {t['reply']}", "",
                  f"- Retrieval: {', '.join(f'[S{i}] {s.path} :: {s.section}' for i, s in enumerate(t['sources'], 1)) or 'none (not needed)'}",
                  f"- Citation check: {t['check']}", _stats_line(t["stats"]), ""]
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return path
