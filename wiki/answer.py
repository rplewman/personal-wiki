"""Ask mode (neutral, no history, cited) and chat mode (persona, recent turns, retrieval only when needed)."""
import json
import re

from . import llm
from .config import CATALOG_FILE, PROMPTS_DIR, TOP_K
from .retrieval import Retriever

PASSAGE_CHARS = 700        # per source in the prompt: 8 x 700 chars keeps the prompt well inside num_ctx 4096
CHAT_TURNS = 4             # conversation turns (user + reply) kept in chat
CITE = re.compile(r"\[S(\d+)\]")
INSUFFICIENT = "insufficient evidence"
# chat turns about the assistant itself need no notes; edits of the previous reply reuse that reply's notes
META = re.compile(r"^\s*(what can you|what do you|who are you|help\b|how do i use|what commands|thanks|thank you|hi\b|hello)", re.I)
EDIT = re.compile(r"^\s*((make|keep) (it|that|this)|shorter|longer|rephrase|rewrite|reword|shorten)", re.I)


def _prompt(name):
    return (PROMPTS_DIR / name).read_text(encoding="utf-8").strip()


WIKILINK = re.compile(r"\[\[([^\]|]+)(?:\|([^\]]+))?\]\]")
GROUPED = re.compile(r"\[+\s*(S\d+(?:\s*[,;]\s*S\d+)*)\s*\]+")


def _plain(text):
    """Obsidian [[target|label]] -> label: the link syntax wasted the passage budget and leaked into answers."""
    return WIKILINK.sub(lambda m: m.group(2) or m.group(1).split("#")[0].split("/")[-1], text)


def _sources_block(hits, start=1):
    return "\n\n".join(f"[S{i}] {h.chunk.path} :: {h.chunk.section}\n{_plain(h.chunk.text)[:PASSAGE_CHARS]}"
                       for i, h in enumerate(hits, start))


def check_citations(text, n_sources, require=True, allowed=None):
    """Remove citations to sources that were not retrieved (or, with `allowed`, not given to this call).
    Returns (clean text, check summary). Gemma sometimes writes [S1, S2] or [[S1]]; these are normalised to [S1][S2] first."""
    ok = set(allowed) if allowed is not None else set(range(1, n_sources + 1))
    text = GROUPED.sub(lambda m: "".join(f"[{s}]" for s in re.findall(r"S\d+", m.group(1))), text)
    bad = sorted({int(m) for m in CITE.findall(text) if int(m) not in ok})
    clean = CITE.sub(lambda m: m.group(0) if int(m.group(1)) in ok else "", text)
    used = sorted({int(m) for m in CITE.findall(clean)})
    notes = []
    if bad:
        notes.append(f"REJECTED citations to unretrieved sources {', '.join(f'S{b}' for b in bad)} (removed)")
    if used:
        notes.append(f"cites {', '.join(f'S{u}' for u in used)}")
    elif require and INSUFFICIENT in text.lower():
        notes.append("insufficient evidence (no citations needed)")
    elif require:
        notes.append("WARNING: answer has no citations")
    else:
        notes.append("no citations")
    return re.sub(r"[ \t]+([.,;])", r"\1", clean).strip(), "; ".join(notes)


def merge_stats(all_stats):
    """One stats dict for an ask that made several Gemma calls: times and tokens are summed, memory is the last call's."""
    all_stats = [s for s in all_stats if s]
    if not all_stats:
        return None
    out = dict(all_stats[-1])
    for key in ("wall_s", "load_s"):
        out[key] = round(sum(s[key] for s in all_stats), 2)
    for key in ("prompt_tokens", "output_tokens"):
        out[key] = sum(s[key] for s in all_stats)
    gen_s = sum(s["output_tokens"] / s["tok_per_s"] for s in all_stats if s["tok_per_s"])
    out["tok_per_s"] = round(out["output_tokens"] / gen_s, 1) if gen_s else None
    out["calls"] = len(all_stats)
    return out


# ---------- routing: questions spanning several projects are answered per project (T3) ----------

MULTI_PROJECT = re.compile(r"\b(projects|apps|each (one|project|app)|across|all (my|three)|compare|which of my)\b", re.I)
PER_PROJECT_K = 20         # retrieve wider, then keep the best few passages of each project
PER_PROJECT_PASSAGES = 3
NOT_IN_NOTES = "not in the notes"
REVIEW_NOTES = {"wiki/Breakaway PRD Review Notes.md": "breakaway-prd-v3-0"}


def project_of(path, catalog):
    """Project page name for a passage's file, or None for shared pages (e.g. wiki/Shared Themes.md)."""
    sources = catalog.get("sources", {})
    for sid, s in sources.items():
        if s.get("raw") == path:
            return s.get("page")
    if path in REVIEW_NOTES:
        return sources.get(REVIEW_NOTES[path], {}).get("page")
    folder, _, name = path.rpartition("/")
    name = name.removesuffix(".md")
    if folder == "wiki/Projects":
        return name
    if folder == "wiki/Concepts":
        sids = list(catalog.get("concepts", {}).get(name, {}).get("sources", {}))
        if len(sids) == 1:
            return sources.get(sids[0], {}).get("page")
    return None


def _load_catalog():
    return json.loads(CATALOG_FILE.read_text(encoding="utf-8")) if CATALOG_FILE.exists() else {}


def _ask_per_project(question, r, catalog):
    hits = r.search(question, k=PER_PROJECT_K)
    projects = [s["page"] for s in catalog.get("sources", {}).values() if s.get("page")]
    groups = {p: [] for p in projects}
    for h in hits:
        p = project_of(h.chunk.path, catalog)
        if p in groups and len(groups[p]) < PER_PROJECT_PASSAGES:
            groups[p].append(h)
    system = _prompt("ask-per-project.md")
    sources, lines, raws, checks, stats, n_calls = [], [], [], [], [], 0
    for p in projects:
        g = groups[p]
        if not g:
            lines.append(f"**{p}:** Not in the notes (no passage retrieved).")
            checks.append(f"{p}: no passages")
            continue
        start = len(sources) + 1
        sources += [h.chunk for h in g]
        labels = range(start, start + len(g))
        messages = [{"role": "system", "content": system},
                    {"role": "user", "content": f"Project: {p}\n\nSources:\n\n{_sources_block(g, start)}\n\nQuestion: {question}"}]
        raw, st = llm.chat(messages, temperature=0.1, max_tokens=150)
        n_calls += 1
        stats.append(st)
        raws.append(f"**{p}:** {raw}")
        if NOT_IN_NOTES in raw.lower():
            lines.append(f"**{p}:** Not in the notes.")
            checks.append(f"{p}: not in the notes")
            continue
        text, check = check_citations(raw, len(sources), allowed=labels)
        lines.append(f"**{p}:** {text}")
        checks.append(f"{p}: {check}")
    if all(NOT_IN_NOTES in line.lower() for line in lines):
        lines = ["Insufficient evidence. None of the projects' notes answer this question."] + lines
    return {"question": question, "answer": "\n".join(lines), "raw_answer": "\n".join(raws), "sources": sources,
            "stats": merge_stats(stats), "check": " | ".join(checks), "retrieval_note": r.note,
            "route": f"per-project: {n_calls} calls"}


# ---------- single-project path: answerability check first (T4) ----------

ANSWERED_SCHEMA = {"type": "object", "properties": {"answered": {"type": "string", "enum": ["yes", "no"]}},
                   "required": ["answered"]}
NOT_ANSWERED_NOTE = ("The sources do not directly answer this question. Start your reply with \"Insufficient evidence.\" "
                     "Then say in one or two sentences what the notes do say about it, citing the sources.")


def _answerable(question, block):
    messages = [{"role": "system", "content": _prompt("ask-answerable.md")},
                {"role": "user", "content": f"Sources:\n\n{block}\n\nQuestion: {question}"}]
    raw, stats = llm.chat(messages, temperature=0, max_tokens=20, fmt=ANSWERED_SCHEMA)
    try:
        verdict = json.loads(raw).get("answered")
    except (json.JSONDecodeError, AttributeError):
        verdict = None
    return verdict != "no", verdict, stats   # an unreadable verdict falls back to the normal answer


def ask(question, retriever=None, k=TOP_K):
    r = retriever or Retriever()
    if MULTI_PROJECT.search(question):
        catalog = _load_catalog()
        if catalog.get("sources"):
            return _ask_per_project(question, r, catalog)
    hits = r.search(question, k=k)
    sources = [h.chunk for h in hits]
    if not hits:
        return {"question": question, "answer": "Insufficient evidence. No passage in the notes matches the question.",
                "raw_answer": "", "sources": [], "stats": None, "check": "no passages retrieved", "retrieval_note": r.note,
                "route": "no passages"}
    block = _sources_block(hits)
    answered, verdict, check_stats = _answerable(question, block)
    user = f"Sources:\n\n{block}\n\nQuestion: {question}"
    if not answered:
        user += f"\n\n{NOT_ANSWERED_NOTE}"
    messages = [{"role": "system", "content": _prompt("wiki-instructions.md")}, {"role": "user", "content": user}]
    raw, stats = llm.chat(messages, temperature=0.1, max_tokens=300)
    answer, check = check_citations(raw, len(hits))
    if not answered and not answer.lower().startswith(INSUFFICIENT):
        answer = "Insufficient evidence. " + answer
        check += "; 'Insufficient evidence.' prepended by the harness"
    return {"question": question, "answer": answer, "raw_answer": raw, "sources": sources,
            "stats": merge_stats([check_stats, stats]), "check": check, "retrieval_note": r.note,
            "route": f"answerability: {verdict or 'unreadable'}"}


class Chat:
    def __init__(self, retriever=None):
        self.retriever = retriever or Retriever()
        self.history = []   # list of {"user", "reply", "hits", "sources", "check", "stats"}
        self.persona = _prompt("persona.md")

    def notes_for(self, message):
        if META.search(message):
            return []
        if EDIT.search(message) and self.history:
            return self.history[-1]["hits"]
        return self.retriever.search(message, k=4)

    def send(self, message):
        hits = self.notes_for(message)
        system = self.persona
        if hits:
            system += "\n\nNotes that may help with the latest message:\n\n" + _sources_block(hits)
        messages = [{"role": "system", "content": system}]
        for t in self.history[-CHAT_TURNS:]:
            messages += [{"role": "user", "content": t["user"]}, {"role": "assistant", "content": t["reply"]}]
        messages.append({"role": "user", "content": message})
        raw, stats = llm.chat(messages, temperature=0.5, max_tokens=350)
        reply, check = check_citations(raw, len(hits), require=False)
        turn = {"user": message, "reply": reply, "hits": hits, "sources": [h.chunk for h in hits], "check": check, "stats": stats}
        self.history.append(turn)
        return turn
