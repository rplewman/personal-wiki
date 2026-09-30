"""Retrieval-only check: do the top-k passages for each test question contain the expected evidence?
Run before involving Gemma:  .venv\\Scripts\\python.exe tests\\check_retrieval.py [--mode hybrid|bm25|dense] [-k 6]"""
import argparse
import sys
from pathlib import Path

import yaml

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from wiki.config import MAX_PER_SOURCE  # noqa: E402
from wiki.retrieval import Retriever  # noqa: E402


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--mode", default="hybrid")
    ap.add_argument("-k", type=int, default=6)
    ap.add_argument("--max-per-source", type=int, default=MAX_PER_SOURCE, help="0 = no cap")
    a = ap.parse_args()
    tests = yaml.safe_load((Path(__file__).parent / "questions.yaml").read_text(encoding="utf-8"))
    r = Retriever()
    passed = 0
    for t in tests:
        hits = r.search(t["question"], k=a.k, mode=a.mode, max_per_source=a.max_per_source or None)
        ok_all = True
        print(f"\n{t['id']} ({t['kind']}): {t['question']}")
        for src, needles in t["retrieval_must_contain"].items():
            path = src  # already relative to vault/
            found = [n + 1 for n, h in enumerate(hits)
                     if h.chunk.path == path and all(s in h.chunk.text for s in needles)]
            ok = bool(found)
            ok_all &= ok
            print(f"  {'PASS' if ok else 'FAIL'}  {path} contains {needles}  -> rank {found or '-'}")
        for n, h in enumerate(hits, 1):
            print(f"     {n}. {h.chunk.path} :: {h.chunk.section[:70]}")
        passed += ok_all
    if r.note:
        print(f"\n[note] {r.note}")
    print(f"\n{passed}/{len(tests)} questions retrieved all expected passages (mode={a.mode}, k={a.k}, max_per_source={a.max_per_source}).")


if __name__ == "__main__":
    main()
