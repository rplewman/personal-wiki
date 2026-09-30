"""Hybrid retrieval: BM25 + embeddinggemma vectors, fused with reciprocal rank fusion.
The index and embedding cache live in data/ (outside the vault)."""
import hashlib
import json
import re
from dataclasses import dataclass

import numpy as np
from rank_bm25 import BM25Okapi

from . import llm
from .chunker import Chunk, chunk_file, file_hash
from .config import DATA_DIR, EMBED_CACHE, INDEX_FILE, MAX_PER_SOURCE, RAW_DIR, TOP_K, VAULT, WIKI_DIR

STOPWORDS = set("""a an and are as at be but by did do does for from how i in is it its my of on or so that the
their this to was were what when which who why will with you your""".split())
RRF_K = 60


def stem(t):
    """Light suffix stripping so 'hosting'/'hosted'/'hosts' all match 'host'. Deliberately crude: BM25 only."""
    for suf in ("ing", "ed", "es", "s"):
        if len(t) > len(suf) + 3 and t.endswith(suf):
            return t[: -len(suf)]
    return t


def tokenize(text):
    return [stem(t) for t in re.findall(r"[a-z0-9]+", text.lower()) if t not in STOPWORDS]


def source_files():
    """Files that are searchable: raw sources and wiki pages (not index.md, not attachments)."""
    files = sorted(RAW_DIR.glob("*.md")) + sorted(WIKI_DIR.rglob("*.md"))
    return [f for f in files if f.is_file()]


# ---------- embedding cache (keyed by text hash, so unchanged passages are never re-embedded) ----------

def _key(text):
    return hashlib.sha256(text.encode("utf-8")).hexdigest()[:24]


def _load_cache():
    if EMBED_CACHE.exists():
        z = np.load(EMBED_CACHE)
        return dict(zip(z["keys"].tolist(), z["vecs"]))
    return {}


def _save_cache(cache):
    DATA_DIR.mkdir(exist_ok=True)
    keys = list(cache)
    np.savez(EMBED_CACHE, keys=np.array(keys), vecs=np.stack([cache[k] for k in keys]) if keys else np.zeros((0, 768)))


def _doc_prompt(c: Chunk):
    return f"title: {c.path} {c.section} | text: {c.text}"


def _query_prompt(q):
    return f"task: search result | query: {q}"


def _normalise(m):
    m = np.asarray(m, dtype=np.float32)
    return m / np.clip(np.linalg.norm(m, axis=-1, keepdims=True), 1e-9, None)


# ---------- index ----------

def build_index(verbose=False):
    """Re-chunk every source; embed only passages not already cached. Returns summary dict.
    If Ollama is down, the index is still written (BM25 works) and vectors are marked missing."""
    files = source_files()
    chunks = [c for f in files for c in chunk_file(f)]
    cache = _load_cache()
    todo = [c for c in chunks if _key(_doc_prompt(c)) not in cache]
    embedded, embed_error = 0, None
    if todo:
        try:
            vecs = llm.embed([_doc_prompt(c) for c in todo])
            for c, v in zip(todo, vecs):
                cache[_key(_doc_prompt(c))] = np.asarray(v, dtype=np.float32)
            embedded = len(todo)
            _save_cache(cache)
        except llm.OllamaError as e:
            embed_error = str(e)
    DATA_DIR.mkdir(exist_ok=True)
    INDEX_FILE.write_text(json.dumps({
        "files": {f.relative_to(VAULT).as_posix(): file_hash(f) for f in files},
        "chunks": [c.to_dict() for c in chunks],
    }, indent=1), encoding="utf-8")
    summary = {"files": len(files), "chunks": len(chunks), "newly_embedded": embedded, "embed_error": embed_error}
    if verbose:
        print(summary)
    return summary


def _index_is_stale(idx):
    current = {f.relative_to(VAULT).as_posix(): file_hash(f) for f in source_files()}
    return current != idx.get("files")


@dataclass
class Hit:
    chunk: Chunk
    score: float
    bm25_rank: int | None
    dense_rank: int | None


class Retriever:
    def __init__(self, auto_rebuild=True):
        if not INDEX_FILE.exists() or (auto_rebuild and _index_is_stale(json.loads(INDEX_FILE.read_text(encoding="utf-8")))):
            build_index()
        idx = json.loads(INDEX_FILE.read_text(encoding="utf-8"))
        self.chunks = [Chunk(**c) for c in idx["chunks"]]
        self.bm25 = BM25Okapi([tokenize(c.search_text) for c in self.chunks])
        cache = _load_cache()
        keys = [_key(_doc_prompt(c)) for c in self.chunks]
        self.has_vectors = bool(self.chunks) and all(k in cache for k in keys)
        self.vecs = _normalise(np.stack([cache[k] for k in keys])) if self.has_vectors else None
        self.note = None

    def _dense_ranks(self, query):
        if not self.has_vectors:
            self.note = "embeddings missing (run `wiki index` with Ollama running); using BM25 only"
            return None
        try:
            q = _normalise(llm.embed([_query_prompt(query)])[0])
        except llm.OllamaError as e:
            self.note = f"embedding model unavailable ({e.__class__.__name__}); using BM25 only"
            return None
        return self.vecs @ q

    def search(self, query, k=TOP_K, mode="hybrid", max_per_source=MAX_PER_SOURCE):
        self.note = None
        n = len(self.chunks)
        bm = self.bm25.get_scores(tokenize(query))
        bm_order = np.argsort(-bm)
        bm_rank = {int(i): r for r, i in enumerate(bm_order) if bm[i] > 0}
        dense = self._dense_ranks(query) if mode in ("hybrid", "dense") else None
        dn_rank = {int(i): r for r, i in enumerate(np.argsort(-dense))} if dense is not None else {}

        fused = np.zeros(n)
        for i in range(n):
            if mode != "dense" and i in bm_rank:
                fused[i] += 1 / (RRF_K + bm_rank[i] + 1)
            if i in dn_rank:
                fused[i] += 1 / (RRF_K + dn_rank[i] + 1)

        hits, per_source = [], {}
        for i in np.argsort(-fused):
            i = int(i)
            if fused[i] <= 0:
                break
            c = self.chunks[i]
            if max_per_source and per_source.get(c.path, 0) >= max_per_source:
                continue
            per_source[c.path] = per_source.get(c.path, 0) + 1
            hits.append(Hit(c, float(fused[i]), bm_rank.get(i), dn_rank.get(i)))
            if len(hits) >= k:
                break
        return hits
