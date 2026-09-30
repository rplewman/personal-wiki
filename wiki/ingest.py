"""Ingest: raw source -> Gemma fact extraction -> checked facts -> wiki pages + vault/index.md.

Gemma only proposes content (facts, a title, a summary, concepts). The harness picks file names,
checks every fact against the source, renders the Markdown, and keeps data/source_catalog.json so
re-ingesting a source updates the same page instead of creating a duplicate.

Pipeline for one source:
  1. extract  split the source into ~6000-char batches of heading-labelled passages; Gemma returns
              at most 5 one-sentence facts per batch, each tied to a passage label (JSON schema enum).
  2. check    drop facts whose numbers do not appear in the cited section, and near-duplicates.
  3. plan     Gemma sees only the numbered checked facts and returns title, summary, key fact IDs
              and 2-4 concepts (JSON schema). Free-text parts get the same number check.
  4. render   every generated page (projects, concepts, index) is re-rendered from the catalog,
              keeping anything a human wrote below the human-notes marker.
"""
import datetime as dt
import json
import re
import shutil
import time
from pathlib import Path

import yaml

from . import llm
from .chunker import chunk_file, file_hash
from .config import (CATALOG_FILE, CONCEPTS_DIR, GEN_MODEL, INDEX_PAGE, INGEST_LOG_DIR, PROMPTS_DIR,
                     PROJECTS_DIR, RAW_DIR, REVIEW_FILE, VAULT, WIKI_DIR)
from .retrieval import tokenize

MARKER = "<!-- Human notes: anything below this line is kept when the page is re-ingested. -->"
GENERATOR = "wiki ingest"
BATCH_CHARS = 6000
PASSAGE_CHARS = 1500
FACTS_PER_SECTION_MAX = 4
MAX_FACT_CHARS = 240
PLAN_FACT_CHARS = 8000  # facts shown to the plan step: ~2100 tokens, leaving room for prompt and output in 4096
SUPPORTED = {".md", ".txt"}
BAD_NAME_CHARS = re.compile(r'[\\/:*?"<>|#^\[\]{}`_]+')
NUMBER = re.compile(r"\d+(?:[.,]\d+)*")


class IngestError(RuntimeError):
    pass


# ---------------------------------------------------------------- catalog

def load_catalog():
    if CATALOG_FILE.exists():
        return json.loads(CATALOG_FILE.read_text(encoding="utf-8"))
    return {"sources": {}, "concepts": {}}


def save_catalog(cat):
    CATALOG_FILE.parent.mkdir(exist_ok=True)
    CATALOG_FILE.write_text(json.dumps(cat, indent=1, ensure_ascii=False), encoding="utf-8")


def slugify(text):
    return re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")


def concept_key(name):
    k = re.sub(r"[^a-z0-9]", "", name.lower())
    return k[:-1] if k.endswith("s") else k


def find_source(cat, rel, sha):
    """Catalog entry for a raw file: by path first, then by content hash (a renamed file keeps its page)."""
    for sid, e in cat["sources"].items():
        if e["raw"] == rel:
            return sid
    for sid, e in cat["sources"].items():
        if e["sha256"] == sha:
            return sid
    return None


# ---------------------------------------------------------------- helpers

def read_prompt(name, **fields):
    text = (PROMPTS_DIR / name).read_text(encoding="utf-8")
    for k, v in fields.items():
        text = text.replace("{" + k + "}", str(v))
    return text


def frontmatter(text):
    if text.startswith("---"):
        end = text.find("\n---", 3)
        if end != -1:
            try:
                return yaml.safe_load(text[3:end]) or {}
            except yaml.YAMLError:
                return {}
    return {}


def numbers(text):
    return {n.replace(",", "") for n in NUMBER.findall(text)}


def unsupported_numbers(claim, evidence):
    """Numbers in the claim that never appear in the evidence text. Empty set = passes the check."""
    return numbers(claim) - numbers(evidence)


def clean_name(text, max_words=6):
    text = BAD_NAME_CHARS.sub(" ", text or "")
    text = re.sub(r"\.(md|txt|docx|pdf)\b", "", text, flags=re.I)
    text = re.sub(r"\s+", " ", text).strip(" .,-–—")
    if text and text == text.lower():
        text = text.title()
    words = text.split()
    return " ".join(words) if 1 <= len(words) <= max_words else ""


def heading_of(section):
    return section.split(" > ")[-1].strip()


def source_ref(raw_rel, section):
    """Obsidian link to the exact heading in the raw source, e.g. [[raw/PLAN#Build order|§ Build order]]."""
    target = raw_rel[:-3] if raw_rel.endswith(".md") else raw_rel
    h = heading_of(section)
    if not h or h == Path(raw_rel).stem or re.search(r"[#|\[\]^]", h):
        return f"[[{target}|{Path(raw_rel).name}]]"
    if re.search(r"[:`]", h):
        # Obsidian does not resolve heading links containing ':' or backticks (checked by clicking
        # "§ Appendix A: Glossary" on 2026-09-29), so link the file and name the section in the label.
        return f"[[{target}|{Path(raw_rel).name}, § {h.replace('`', '')}]]"
    return f"[[{target}#{h}|§ {h}]]"


def split_page(path):
    """(frontmatter dict, human-notes tail) of an existing page."""
    if not path.exists():
        return {}, ""
    text = path.read_text(encoding="utf-8")
    tail = text.split(MARKER, 1)[1].strip("\n") if MARKER in text else ""
    return frontmatter(text), tail


def is_generated(path):
    return str(frontmatter(path.read_text(encoding="utf-8")).get("generated_by", "")).startswith(GENERATOR)


# ---------------------------------------------------------------- 1. extract

def make_batches(path):
    """Group heading-labelled passages into batches that fit the 4096-token context with room for output."""
    chunks = chunk_file(path, limit=PASSAGE_CHARS)
    batches, cur, size = [], [], 0
    for c in chunks:
        if cur and size + len(c.text) > BATCH_CHARS:
            batches.append(cur)
            cur, size = [], 0
        cur.append(c)
        size += len(c.text)
    if cur:
        batches.append(cur)
    return chunks, batches


def extract_facts(batch, log):
    """One required JSON key per passage label, so the model has to consider every section in the batch
    (with a single free list it took all its facts from the first sections: see the first Draft Copilot log)."""
    labels, passages_per, labelled = {}, {}, []  # short label (last heading) -> full section path
    for c in batch:
        label = heading_of(c.section)
        if labels.get(label, c.section) != c.section:  # same heading text under two parents: use full path
            label = c.section
        labels[label] = c.section
        passages_per[label] = passages_per.get(label, 0) + 1
        labelled.append(f"### [{label}]\n{c.text}")
    schema = {
        "type": "object",
        "properties": {lbl: {"type": "array", "maxItems": min(FACTS_PER_SECTION_MAX, 2 * passages_per[lbl]),
                             "items": {"type": "string"}} for lbl in labels},
        "required": list(labels),
    }
    messages = [
        {"role": "system", "content": read_prompt("ingest-extract.md")},
        {"role": "user", "content": "Passages:\n\n" + "\n\n".join(labelled)},
    ]
    text, stats = llm.chat(messages, temperature=0.1, max_tokens=1000, fmt=schema)
    log["calls"].append({"step": "extract", "sections": list(labels), "output": text, "stats": stats})
    try:
        data = json.loads(text)
    except json.JSONDecodeError:
        log["problems"].append(f"extract: invalid JSON for sections {list(labels)}")
        return []
    return [{"section": labels[lbl], "fact": f.strip()}
            for lbl, items in data.items() if lbl in labels and isinstance(items, list)
            for f in items if isinstance(f, str) and f.strip()]


# ---------------------------------------------------------------- 2. check

def near_duplicate(fact, others, threshold=0.7):
    """True if the fact's content words overlap >= threshold (Jaccard) with any earlier fact.
    Catches Gemma restating one idea in several sections ("Breakaway is a data aggregator..." x4)."""
    a = set(tokenize(fact))
    for o in others:
        b = set(tokenize(o))
        if a and b and len(a & b) / len(a | b) >= threshold:
            return True
    return False


def check_facts(facts, section_text, log):
    kept = []
    for f in facts:
        fact = re.sub(r"\s+", " ", f["fact"]).strip()
        bad = unsupported_numbers(fact, f["section"] + "\n" + section_text.get(f["section"], ""))
        reason = ("too long" if len(fact) > MAX_FACT_CHARS else
                  "too short" if len(fact.split()) < 4 else
                  "near-duplicate of an earlier fact" if near_duplicate(fact, [k["fact"] for k in kept]) else
                  f"numbers not in cited section: {sorted(bad)}" if bad else None)
        if reason:
            log["rejected"].append({**f, "reason": reason})
            continue
        kept.append({"section": f["section"], "fact": fact})
    return kept


# ---------------------------------------------------------------- human review

def load_review():
    """data/review.json: {source_id: {fact text: {"action": "drop"|"replace", "text": ..., "note": ...}}}.
    Kept apart from the catalog so re-ingesting never erases a human correction."""
    return json.loads(REVIEW_FILE.read_text(encoding="utf-8")) if REVIEW_FILE.exists() else {}


def reviewed(facts, fixes):
    """Apply review fixes to a fact list; replaced facts are marked so readers know a person changed them."""
    out = []
    for f in facts:
        fix = fixes.get(f["fact"])
        if not fix:
            out.append(f)
        elif fix["action"] == "replace":
            out.append({**f, "fact": fix["text"], "corrected": True})
    return out


# ---------------------------------------------------------------- 3. plan

def sample_for_plan(facts, budget=PLAN_FACT_CHARS):
    """Facts for the plan step, round-robin across sections (first fact of every section, then second...)
    until the character budget is used, returned in source order."""
    groups = {}
    for i, f in enumerate(facts):
        groups.setdefault(f["section"], []).append(i)
    order, depth = [], 0
    while layer := [g[depth] for g in groups.values() if depth < len(g)]:
        order += layer
        depth += 1
    chosen, size = [], 0
    for i in order:
        size += len(facts[i]["fact"]) + 6
        if size > budget:
            break
        chosen.append(i)
    return [facts[i] for i in sorted(chosen)]


def plan_page(facts, source_name, existing_concepts, log):
    ids = [f"F{i}" for i in range(1, len(facts) + 1)]
    schema = {
        "type": "object",
        "properties": {
            "title": {"type": "string"},
            "summary": {"type": "string"},
            "key_facts": {"type": "array", "maxItems": 10, "items": {"type": "string", "enum": ids}},
            "concepts": {"type": "array", "maxItems": 4, "items": {
                "type": "object",
                "properties": {"name": {"type": "string"}, "how": {"type": "string"},
                               "facts": {"type": "array", "items": {"type": "string", "enum": ids}}},
                "required": ["name", "how", "facts"]}},
        },
        "required": ["title", "summary", "key_facts", "concepts"],
    }
    listing = "\n".join(f"{i}: {f['fact']}" for i, f in zip(ids, facts))
    messages = [
        {"role": "system", "content": read_prompt("ingest-page.md", source_name=source_name,
                                                  concepts=", ".join(existing_concepts) or "none yet")},
        {"role": "user", "content": f"Facts:\n{listing}"},
    ]
    text, stats = llm.chat(messages, temperature=0.2, max_tokens=700, fmt=schema)
    log["calls"].append({"step": "plan", "output": text, "stats": stats})
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        log["problems"].append("plan: invalid JSON")
        return {}


def default_title(raw_path, raw_text):
    fm = frontmatter(raw_text)
    for cand in (fm.get("project"), fm.get("title")):
        if cand and clean_name(str(cand)):
            return clean_name(str(cand))
    m = re.search(r"^#\s+(.+)$", raw_text, flags=re.M)
    if m:
        # "Plan: The GRKN – shared meal-planning app" -> "The GRKN"
        parts = re.split(r"\s[–—-]\s|:\s", m.group(1))
        part = parts[1] if len(parts) > 1 and parts[0].lower() in ("plan", "notes") else parts[0]
        if clean_name(part):
            return clean_name(part)
    return clean_name(raw_path.stem) or raw_path.stem


def page_title(proposed, fallback, taken):
    """2-6 word readable file name. One-word names get ' Project' appended so the file name reads clearly."""
    title = clean_name(proposed) or fallback
    if set(fallback.lower().split()) <= set(title.lower().split()):
        title = fallback  # "Draft Copilot Project" / "The Draft Copilot" -> the source's own name
    if len(title.split()) == 1:
        title += " Project"
    if title.lower() in taken:
        title = fallback if fallback.lower() not in taken else f"{title} Notes"
    return title


def build_entry(facts, plan, raw_text, section_text, cat, sid, log):
    by_id = {f"F{i}": f for i, f in enumerate(facts, 1)}
    # summary: keep only sentences whose numbers appear somewhere in the source
    sentences = re.split(r"(?<=[.!?])\s+", (plan.get("summary") or "").strip())
    summary = []
    for s in sentences:
        bad = unsupported_numbers(s, raw_text)
        if s and not bad:
            summary.append(s)
        elif s:
            log["rejected"].append({"summary_sentence": s, "reason": f"numbers not in source: {sorted(bad)}"})
    key_ids = [i for i in dict.fromkeys(plan.get("key_facts") or []) if i in by_id]
    if len(key_ids) < 6:  # model picked too few: top up in source order so the page is not thin
        key_ids += [i for i in by_id if i not in key_ids][: 8 - len(key_ids)]
    key_points = [by_id[i] for i in key_ids[:10]]

    project_names = {e["page"].lower() for s, e in cat["sources"].items() if s != sid}
    existing = {concept_key(n): n for n in cat["concepts"]}
    concepts = {}
    for c in plan.get("concepts") or []:
        name = clean_name(c.get("name", ""), max_words=4)
        refs = [by_id[i] for i in dict.fromkeys(c.get("facts") or []) if i in by_id]
        if not name or not refs or name.lower() in project_names or name.lower() == (plan.get("title") or "").lower():
            log["rejected"].append({"concept": c, "reason": "no name, no valid supporting facts, or names a project"})
            continue
        name = existing.get(concept_key(name), name)
        how = re.sub(r"\s+", " ", c.get("how", "")).strip()
        evidence = "\n".join(r["section"] + "\n" + section_text.get(r["section"], "") for r in refs)
        if not how or unsupported_numbers(how, evidence):
            log["rejected"].append({"concept_how": how, "reason": "empty or numbers not in supporting sections"})
            how = refs[0]["fact"]
        concepts[name] = {"how": how, "refs": refs}
    return " ".join(summary), key_points, concepts


# ---------------------------------------------------------------- ingest one source

def resolve_source(path):
    """Accept a path inside vault/raw, a bare file name in vault/raw, or an outside file (copied into raw)."""
    p = Path(path)
    if not p.exists() and (RAW_DIR / p.name).exists():
        p = RAW_DIR / p.name
    if not p.exists():
        raise IngestError(f"No such file: {path}")
    if p.suffix.lower() not in SUPPORTED:
        raise IngestError(f"{p.name}: only {', '.join(sorted(SUPPORTED))} sources are supported. Convert it to Markdown first.")
    p = p.resolve()
    if p.parent != RAW_DIR.resolve():
        target = RAW_DIR / p.name
        if target.exists() and file_hash(target) != file_hash(p):
            raise IngestError(f"vault/raw/{p.name} already exists with different content. Raw sources are never "
                              f"overwritten; rename the new file and retry.")
        if not target.exists():
            shutil.copy2(p, target)
            print(f"Copied {p.name} into vault/raw/.")
        p = target
    return p


def ingest_file(path, cat, force=False):
    raw = resolve_source(path)
    rel = raw.relative_to(VAULT).as_posix()
    sha = file_hash(raw)
    sid = find_source(cat, rel, sha)
    if sid and cat["sources"][sid]["sha256"] == sha and cat["sources"][sid]["raw"] == rel and not force:
        return {"source": rel, "status": "unchanged", "page": cat["sources"][sid]["page"]}
    status = "updated" if sid else "new"
    if not sid:
        sid = base = slugify(raw.stem)
        n = 2
        while sid in cat["sources"]:
            sid, n = f"{base}-{n}", n + 1

    raw_text = raw.read_text(encoding="utf-8")
    log = {"source": rel, "sha256": sha, "model": GEN_MODEL, "started": dt.datetime.now().isoformat(timespec="seconds"),
           "calls": [], "rejected": [], "problems": []}
    t0 = time.perf_counter()
    chunks, batches = make_batches(raw)
    section_text = {}
    for c in chunks:
        section_text[c.section] = section_text.get(c.section, "") + "\n" + c.text

    facts = []
    for n, b in enumerate(batches, 1):
        print(f"  extract {n}/{len(batches)} ({sum(len(c.text) for c in b)} chars)...", flush=True)
        facts += extract_facts(b, log)
    kept = check_facts(facts, section_text, log)
    if not kept:
        raise IngestError(f"{rel}: no facts survived checking; see the ingest log. Nothing was written.")

    plan_facts = sample_for_plan(kept)
    print(f"  plan page from {len(plan_facts)} of {len(kept)} checked facts ({len(facts) - len(kept)} rejected)...", flush=True)
    plan = plan_page(plan_facts, raw.stem, list(cat["concepts"]), log)
    summary, key_points, concepts = build_entry(plan_facts, plan, raw_text, section_text, cat, sid, log)

    if sid in cat["sources"]:
        title = cat["sources"][sid]["page"]  # never rename an existing page
    else:
        taken = {e["page"].lower() for e in cat["sources"].values()} | {c.lower() for c in cat["concepts"]}
        # A name the source declares (frontmatter project/title or its H1) beats Gemma's proposal, which
        # tended to be a description ("Intelligent Data Aggregator Plan Adjuster" for Breakaway).
        fallback = default_title(raw, raw_text)
        declared = fallback != (clean_name(raw.stem) or raw.stem)
        title = page_title(fallback if declared else plan.get("title", ""), fallback, taken)
        target = PROJECTS_DIR / f"{title}.md"
        if target.exists() and not is_generated(target):
            raise IngestError(f"{target.relative_to(VAULT)} exists and was not written by ingest; refusing to overwrite.")

    # drop this source's old concept contributions, then add the new ones
    for cname in list(cat["concepts"]):
        cat["concepts"][cname]["sources"].pop(sid, None)
    for cname, c in concepts.items():
        cat["concepts"].setdefault(cname, {"sources": {}})["sources"][sid] = c
    cat["concepts"] = {k: v for k, v in cat["concepts"].items() if v["sources"]}

    cat["sources"][sid] = {
        "raw": rel, "sha256": sha, "page": title, "summary": summary, "key_points": key_points,
        "facts": kept, "concepts": list(concepts), "proposed_title": plan.get("title", ""), "model": GEN_MODEL,
        "ingested": dt.datetime.now().isoformat(timespec="seconds"),
    }
    log["seconds"] = round(time.perf_counter() - t0, 1)
    log["result"] = cat["sources"][sid]
    INGEST_LOG_DIR.mkdir(parents=True, exist_ok=True)
    log_file = INGEST_LOG_DIR / f"{sid}-{dt.datetime.now():%Y%m%d-%H%M%S}.json"
    log_file.write_text(json.dumps(log, indent=1, ensure_ascii=False), encoding="utf-8")
    return {"source": rel, "status": status, "page": title, "facts": len(kept), "rejected": len(log["rejected"]),
            "concepts": list(concepts), "seconds": log["seconds"], "log": log_file.relative_to(VAULT.parent).as_posix()}


# ---------------------------------------------------------------- 4. render

def handwritten_notes():
    """Pages in vault/wiki that a person wrote (no generated_by frontmatter)."""
    return [p for p in sorted(WIKI_DIR.rglob("*.md")) if not is_generated(p)]


def _write_page(path, meta, body):
    _, tail = split_page(path)
    fm = yaml.safe_dump(meta, sort_keys=False, allow_unicode=True).strip()
    text = f"---\n{fm}\n---\n\n{body.strip()}\n\n{MARKER}\n"
    if tail:
        text += f"{tail}\n"
    path.parent.mkdir(parents=True, exist_ok=True)
    if not path.exists() or path.read_text(encoding="utf-8") != text:
        path.write_text(text, encoding="utf-8")


def concepts_of(cat, sid):
    """Every concept page this source contributes to: its own concepts and shared themes from `connect`."""
    return [n for n, c in cat["concepts"].items() if sid in c["sources"]]


def _point(raw, f):
    mark = " *(corrected in review)*" if f.get("corrected") else ""
    return f"- {f['fact']}{mark} ({source_ref(raw, f['section'])})"


def render_project(sid, e, cat, notes, fixes):
    raw_target = e["raw"][:-3]
    lines = [f"# {e['page']}", "",
             f"> Generated by local Gemma (`{e['model']}`) from [[{raw_target}|{Path(e['raw']).name}]] "
             f"and checked by the harness. Each point links to the section it came from.", ""]
    if e["summary"]:
        lines += ["## Summary", e["summary"], ""]
    key_points = []
    for k in reviewed(e["key_points"], fixes):
        if not near_duplicate(k["fact"], [x["fact"] for x in key_points]):
            key_points.append(k)
    lines += ["## Key points"] + [_point(e["raw"], k) for k in key_points] + [""]
    shown = {k["fact"] for k in key_points}
    details = {}
    for f in reviewed(e.get("facts", []), fixes):
        if f["fact"] not in shown:
            details.setdefault(f["section"].split(" > ")[0], []).append(f)
    if details:
        lines.append("## Details")
        for top, fs in details.items():
            lines += ["", f"### {BAD_NAME_CHARS.sub(' ', top).strip()}"]
            lines += [_point(e["raw"], f) for f in fs]
        lines.append("")
    mine = concepts_of(cat, sid)
    if mine:
        lines.append("## Concepts")
        for cname in mine:
            c = cat["concepts"][cname]
            others = [cat["sources"][o]["page"] for o in c["sources"] if o != sid]
            also = f" Also in {', '.join(f'[[{o}]]' for o in others)}." if others else ""
            lines.append(f"- [[{cname}]]: {c['sources'][sid]['how']}{also}")
        lines.append("")
    related = []
    for osid, o in cat["sources"].items():
        shared = [c for c in mine if osid != sid and osid in cat["concepts"][c]["sources"]]
        if shared:
            related.append(f"- [[{o['page']}]]: shares {', '.join(f'[[{c}]]' for c in shared)}")
    if related:
        lines += ["## Related projects"] + related + [""]
    stem = Path(e["raw"]).stem
    linked = [n for n in notes if any(f"[[{t}" in n.read_text(encoding="utf-8") for t in (stem, raw_target))]
    if linked:
        lines += ["## Related notes"] + [f"- [[{n.stem}]] (hand-written)" for n in linked] + [""]
    if fixes:
        lines += ["## Review", f"A person checked this page against the source. {len(fixes)} generated "
                  f"fact{'s were' if len(fixes) != 1 else ' was'} corrected or removed (listed in `data/review.json`).", ""]
    lines += ["## Source", f"- `vault/{e['raw']}`: [[{raw_target}|{Path(e['raw']).name}]]"]
    meta = {"type": "project", "source": e["raw"], "source_sha256": e["sha256"], "generated_by": f"{GENERATOR} ({e['model']})",
            "ingested": e["ingested"], "reviewed": bool(fixes), "concepts": mine}
    _write_page(PROJECTS_DIR / f"{e['page']}.md", meta, "\n".join(lines))


def render_concept(cname, c, cat, review):
    srcs = cat["sources"]
    n = len(c["sources"])
    lines = [f"# {cname}", "",
             f"> Concept page assembled by `wiki ingest` from facts local Gemma found in each source. "
             f"Mentioned in {n} source{'s' if n != 1 else ''}.", ""]
    for sid, s in c["sources"].items():
        e = srcs[sid]
        via = " *(linked by the connect step)*" if s.get("via") == "connect" else ""
        lines += [f"## In [[{e['page']}]]{via}", s["how"], ""]
        lines += [_point(e["raw"], r) for r in reviewed(s["refs"], review.get(sid, {}))] + [""]
    meta = {"type": "concept", "sources": [srcs[s]["raw"] for s in c["sources"]],
            "generated_by": GENERATOR, "updated": max(srcs[s]["ingested"] for s in c["sources"])}
    _write_page(CONCEPTS_DIR / f"{cname}.md", meta, "\n".join(lines))


def render_index(cat, notes):
    srcs = sorted(cat["sources"].values(), key=lambda e: e["page"].lower())
    lines = ["# Personal Wiki Index", "",
             f"_Rebuilt by `wiki ingest` on {dt.date.today().isoformat()}. Do not edit: changes here are overwritten._", "",
             "## Projects"]
    for e in srcs:
        first = re.split(r"(?<=[.!?])\s", e["summary"], maxsplit=1)[0] if e["summary"] else ""
        lines.append(f"- [[{e['page']}]]{': ' + first if first else ''}")
    shared = {n: c for n, c in cat["concepts"].items() if len(c["sources"]) > 1}
    if shared:
        lines += ["", "## Shared across projects"]
        for cname, c in sorted(shared.items(), key=lambda kv: kv[0].lower()):
            pages = ", ".join(f"[[{cat['sources'][s]['page']}]]" for s in c["sources"])
            lines.append(f"- [[{cname}]]: in {pages}")
    lines += ["", "## Concepts by project"]
    for sid, e in sorted(cat["sources"].items(), key=lambda kv: kv[1]["page"].lower()):
        own = [n for n in concepts_of(cat, sid) if n not in shared]
        if own:
            lines.append(f"- [[{e['page']}]]: {', '.join(f'[[{n}]]' for n in own)}")
    if notes:
        lines += ["", "## Hand-written notes"] + [f"- [[{n.stem}]]" for n in notes]
    ingested = {e["raw"]: e for e in cat["sources"].values()}
    lines += ["", "## Raw sources"]
    for f in sorted(RAW_DIR.glob("*")):
        if f.is_file():
            rel = f.relative_to(VAULT).as_posix()
            e = ingested.get(rel)
            state = (f"ingested into [[{e['page']}]]" + (" (changed since, re-ingest)" if e["sha256"] != file_hash(f) else "")
                     if e else "not ingested yet")
            lines.append(f"- [[{rel.rsplit('.', 1)[0]}|{f.name}]]: {state}")
    INDEX_PAGE.write_text("\n".join(lines) + "\n", encoding="utf-8")


def render_all(cat):
    notes = handwritten_notes()
    review = load_review()
    for sid, e in cat["sources"].items():
        render_project(sid, e, cat, notes, review.get(sid, {}))
    for cname, c in cat["concepts"].items():
        render_concept(cname, c, cat, review)
    # remove generated pages no longer backed by the catalog (only if nobody added human notes to them)
    wanted = {PROJECTS_DIR / f"{e['page']}.md" for e in cat["sources"].values()} | \
             {CONCEPTS_DIR / f"{n}.md" for n in cat["concepts"]}
    for p in list(PROJECTS_DIR.glob("*.md")) + list(CONCEPTS_DIR.glob("*.md")):
        if p not in wanted and is_generated(p) and not split_page(p)[1]:
            p.unlink()
    render_index(cat, notes)


# ---------------------------------------------------------------- 5. connect (shared themes across sources)

CANDIDATES_PER_SOURCE = 5


def _fact_vectors(texts):
    """embeddinggemma vectors for facts, reusing the retrieval embedding cache (keyed by text hash)."""
    import numpy as np
    from .retrieval import _key, _load_cache, _normalise, _save_cache
    prompts = [f"title: none | text: {t}" for t in texts]
    cache = _load_cache()
    todo = [p for p in dict.fromkeys(prompts) if _key(p) not in cache]
    if todo:
        for p, v in zip(todo, llm.embed(todo)):
            cache[_key(p)] = np.asarray(v, dtype=np.float32)
        _save_cache(cache)
    return _normalise(np.stack([cache[_key(p)] for p in prompts]))


def _candidates(facts, vecs, query, qvec, k=CANDIDATES_PER_SOURCE):
    """Top facts of one source for a theme query: BM25 and cosine ranks fused with RRF (as in retrieval)."""
    import numpy as np
    from rank_bm25 import BM25Okapi
    bm = BM25Okapi([tokenize(f["fact"]) or ["_"] for f in facts]).get_scores(tokenize(query))
    cos = vecs @ qvec
    score = np.zeros(len(facts))
    for ranks in (np.argsort(-bm), np.argsort(-cos)):
        for r, i in enumerate(ranks):
            score[i] += 1 / (60 + r + 1)
    return [facts[i] for i in np.argsort(-score)[:k]]


HEDGES = re.compile(r"\b(impl(y|ies|ied)|suggests?|could|might|may|possibly|indirectly)\b", re.I)
CONFIRM_SCHEMA = {"type": "object", "properties": {"answer": {"type": "string", "enum": ["yes", "no"]},
                                                   "quote": {"type": "string"}}, "required": ["answer", "quote"]}


def _confirm(theme, project, fact, log):
    """Second, per-fact check for a connect contribution. The batch verify call judged all facts of all
    projects at once and let through links like "data aggregator ... implies tracking state". Here Gemma
    sees one fact alone and must quote the words that show the theme; the harness keeps the fact only if
    the answer is yes and the quote is really in the fact and names something beyond the project name."""
    text, stats = llm.chat([{"role": "system", "content": read_prompt("connect-confirm.md", theme=theme, project=project)},
                            {"role": "user", "content": f"Fact: {fact}"}], temperature=0.0, max_tokens=80, fmt=CONFIRM_SCHEMA)
    try:
        a = json.loads(text)
    except json.JSONDecodeError:
        a = {}
    quote = re.sub(r"\s+", " ", a.get("quote") or "").strip().strip('"').rstrip(".")
    content = set(tokenize(quote)) - set(tokenize(project))
    if a.get("answer") != "yes":
        reason = "answered no"
    elif not quote or quote.lower() not in fact.lower():
        reason = "quote not found in fact"
    elif len(content) < 2:
        reason = "quote too thin"
    elif HEDGES.search(quote):
        reason = "hedged quote"
    else:
        reason = None
    log["calls"].append({"step": "confirm", "theme": theme, "project": project, "fact": fact, "output": text,
                         "kept": reason is None, "reason": reason, "stats": stats})
    return reason is None


def connect(cat):
    """Find themes shared by two or more sources and add them as concept pages that link those projects.
    Gemma proposes themes from the project summaries; the harness retrieves candidate facts per source;
    Gemma then picks (by constrained ID) which facts really show each project using the theme, and each
    picked fact is re-checked on its own with a quoted-evidence yes/no (`_confirm`). A theme needs supporting facts from at least two projects to be kept.
    (Plain embedding similarity between facts was tried first and matched surface words like "free" or
    "cached", so it is only used to shortlist candidates here.)"""
    for c in cat["concepts"].values():  # connect output is always recomputed from scratch
        c["sources"] = {s: v for s, v in c["sources"].items() if v.get("via") != "connect"}
    cat["concepts"] = {k: v for k, v in cat["concepts"].items() if v["sources"]}
    srcs = cat["sources"]
    if len(srcs) < 2:
        return []
    log = {"started": dt.datetime.now().isoformat(timespec="seconds"), "model": GEN_MODEL, "calls": [], "themes": []}

    desc = "\n\n".join(f"Project: {e['page']}\n{e['summary']}\nIdeas: {', '.join(concepts_of(cat, sid))}"
                       for sid, e in srcs.items())
    schema = {"type": "object", "properties": {"themes": {"type": "array", "maxItems": 4, "items": {
        "type": "object", "properties": {"name": {"type": "string"}, "query": {"type": "string"}},
        "required": ["name", "query"]}}}, "required": ["themes"]}
    text, stats = llm.chat([{"role": "system", "content": read_prompt("connect-themes.md")},
                            {"role": "user", "content": desc}], temperature=0.2, max_tokens=300, fmt=schema)
    log["calls"].append({"step": "themes", "output": text, "stats": stats})
    try:
        themes = json.loads(text).get("themes", [])
    except json.JSONDecodeError:
        themes = []

    sids = list(srcs)
    vecs = {sid: _fact_vectors([f["fact"] for f in srcs[sid]["facts"]]) for sid in sids}
    existing = {concept_key(n): n for n in cat["concepts"]}
    project_names = {e["page"].lower() for e in srcs.values()}
    kept = []
    for th in themes:
        name, query = clean_name(th.get("name", ""), max_words=4), (th.get("query") or "").strip()
        if not name or not query or name.lower() in project_names:
            continue
        qvec = _fact_vectors([query])[0]  # same prompt format as the facts: symmetric similarity
        ids, by_id, listing, props = {}, {}, [], {}
        n = 0
        for sid in sids:
            ids[sid] = []
            listing.append(f"Project: {srcs[sid]['page']}")
            for f in _candidates(srcs[sid]["facts"], vecs[sid], query, qvec):
                n += 1
                ids[sid].append(f"F{n}")
                by_id[f"F{n}"] = f
                listing.append(f"F{n}: {f['fact']}")
            props[srcs[sid]["page"]] = {"type": "object", "properties": {
                "facts": {"type": "array", "items": {"type": "string", "enum": ids[sid]}}, "how": {"type": "string"}},
                "required": ["facts", "how"]}
        schema = {"type": "object", "properties": props, "required": list(props)}
        text, stats = llm.chat([{"role": "system", "content": read_prompt("connect-verify.md", theme=name)},
                                {"role": "user", "content": "\n".join(listing)}], temperature=0.1, max_tokens=500, fmt=schema)
        log["calls"].append({"step": "verify", "theme": name, "query": query, "output": text, "stats": stats})
        try:
            ans = json.loads(text)
        except json.JSONDecodeError:
            continue
        support = {}
        for sid in sids:
            a = ans.get(srcs[sid]["page"]) or {}
            proposed = [by_id[i] for i in dict.fromkeys(a.get("facts") or []) if i in ids[sid]]
            refs = [f for f in proposed if _confirm(name, srcs[sid]["page"], f["fact"], log)]
            how = re.sub(r"\s+", " ", a.get("how") or "").strip()
            if refs:
                # Gemma's sentence may lean on facts the confirm step dropped, or on inference
                if (len(refs) < len(proposed) or not how or HEDGES.search(how)
                        or unsupported_numbers(how, " ".join(r["fact"] for r in refs))):
                    how = refs[0]["fact"]
                support[sid] = {"how": how, "refs": refs, "via": "connect"}
        log["themes"].append({"name": name, "query": query, "supported_by": [srcs[s]["page"] for s in support],
                              "kept": len(support) >= 2})
        if len(support) < 2:
            continue
        cname = existing.get(concept_key(name), name)
        entry = cat["concepts"].setdefault(cname, {"sources": {}})
        for sid, contrib in support.items():
            entry["sources"].setdefault(sid, contrib)  # a source's own ingest contribution wins
        kept.append(cname)
    INGEST_LOG_DIR.mkdir(parents=True, exist_ok=True)
    (INGEST_LOG_DIR / f"connect-{dt.datetime.now():%Y%m%d-%H%M%S}.json").write_text(
        json.dumps(log, indent=1, ensure_ascii=False), encoding="utf-8")
    return kept


def ingest(paths, force=False, reconnect=False):
    cat = load_catalog()
    if not paths:
        paths = sorted(RAW_DIR.glob("*.md")) + sorted(RAW_DIR.glob("*.txt"))
    results = []
    for p in paths:
        print(f"Ingesting {Path(p).name}", flush=True)
        r = ingest_file(p, cat, force=force)
        results.append(r)
        save_catalog(cat)  # after each source, so a failure later keeps earlier work
    shared = None
    if reconnect or any(r["status"] != "unchanged" for r in results):
        print("Connecting sources (shared themes)...", flush=True)
        try:
            shared = connect(cat)
            save_catalog(cat)
        except llm.OllamaError as e:
            print(f"  skipped: {e}")
    render_all(cat)
    return results, shared
