"""Ask mode (neutral, no history, cited) and chat mode (persona, recent turns, retrieval only when needed)."""
import re

from . import llm
from .config import PROMPTS_DIR, TOP_K
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


def _sources_block(hits):
    return "\n\n".join(f"[S{i}] {h.chunk.path} :: {h.chunk.section}\n{_plain(h.chunk.text)[:PASSAGE_CHARS]}"
                       for i, h in enumerate(hits, 1))


def check_citations(text, n_sources, require=True):
    """Remove citations to sources that were not retrieved. Returns (clean text, check summary).
    Gemma sometimes writes [S1, S2] or [[S1]]; these are normalised to [S1][S2] first."""
    text = GROUPED.sub(lambda m: "".join(f"[{s}]" for s in re.findall(r"S\d+", m.group(1))), text)
    bad = sorted({int(m) for m in CITE.findall(text) if not 1 <= int(m) <= n_sources})
    clean = CITE.sub(lambda m: m.group(0) if 1 <= int(m.group(1)) <= n_sources else "", text)
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


def ask(question, retriever=None, k=TOP_K):
    r = retriever or Retriever()
    hits = r.search(question, k=k)
    sources = [h.chunk for h in hits]
    if not hits:
        return {"question": question, "answer": "Insufficient evidence. No passage in the notes matches the question.",
                "raw_answer": "", "sources": [], "stats": None, "check": "no passages retrieved", "retrieval_note": r.note}
    messages = [{"role": "system", "content": _prompt("wiki-instructions.md")},
                {"role": "user", "content": f"Sources:\n\n{_sources_block(hits)}\n\nQuestion: {question}"}]
    raw, stats = llm.chat(messages, temperature=0.1, max_tokens=300)
    answer, check = check_citations(raw, len(hits))
    return {"question": question, "answer": answer, "raw_answer": raw, "sources": sources, "stats": stats,
            "check": check, "retrieval_note": r.note}


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
