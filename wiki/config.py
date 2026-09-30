"""Paths and model settings. Everything the harness writes lives outside vault/ except wiki pages."""
import os
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
VAULT = ROOT / "vault"
RAW_DIR = VAULT / "raw"
WIKI_DIR = VAULT / "wiki"
PROMPTS_DIR = ROOT / "prompts"
DATA_DIR = ROOT / "data"
EVIDENCE_DIR = ROOT / "evidence"
TESTS_DIR = ROOT / "tests"

INDEX_FILE = DATA_DIR / "index.json"
EMBED_CACHE = DATA_DIR / "embed_cache.npz"
CATALOG_FILE = DATA_DIR / "source_catalog.json"
INGEST_LOG_DIR = DATA_DIR / "ingest_log"
REVIEW_FILE = DATA_DIR / "review.json"

PROJECTS_DIR = WIKI_DIR / "Projects"
CONCEPTS_DIR = WIKI_DIR / "Concepts"
INDEX_PAGE = VAULT / "index.md"

OLLAMA_URL = os.environ.get("WIKI_OLLAMA_URL", "http://localhost:11434")
GEN_MODEL = "gemma4:e2b-it-qat"
EMBED_MODEL = "embeddinggemma:latest"
NUM_CTX = 4096

CHUNK_CHARS = 800
TOP_K = 8  # was 6; raised after wiki pages started crowding out raw passages (evidence/retrieval-checks-k8.txt)
MAX_PER_SOURCE = 3  # diversity cap so one long source can't crowd out the others (see evidence/retrieval-checks.md)
