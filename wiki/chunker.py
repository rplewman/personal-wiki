"""Split Markdown files into ~800-character passages that keep their source path and heading path."""
import hashlib
import re
from dataclasses import dataclass, asdict
from pathlib import Path

from .config import CHUNK_CHARS, VAULT

HEADING = re.compile(r"^(#{1,6})\s+(.*?)\s*#*\s*$")
FENCE = re.compile(r"^\s*(```|~~~)")


@dataclass
class Chunk:
    id: str        # stable: <relative path>#<n>
    path: str      # relative to vault/, forward slashes, e.g. raw/PLAN.md
    section: str   # heading path, e.g. "6. Daily Coaching Experience > 6.1 Training Readiness Score"
    text: str      # passage body (without the heading path)

    def to_dict(self):
        return asdict(self)

    @property
    def search_text(self):
        """What BM25 and the embedder see: title + section + body."""
        return f"{Path(self.path).stem} | {self.section}\n{self.text}"


def strip_frontmatter(text):
    if text.startswith("---"):
        end = text.find("\n---", 3)
        if end != -1:
            return text[end + 4:].lstrip("\n")
    return text


def _sections(text):
    """Yield (heading_path, body_lines) for each heading-delimited section, ignoring headings inside code fences."""
    stack = []  # [(level, title)]
    body = []
    in_fence = False
    for line in text.splitlines():
        if FENCE.match(line):
            in_fence = not in_fence
        m = None if in_fence else HEADING.match(line)
        if m:
            yield _path(stack), body
            level = len(m.group(1))
            while stack and stack[-1][0] >= level:
                stack.pop()
            stack.append((level, m.group(2)))
            body = []
        else:
            body.append(line)
    yield _path(stack), body


def _path(stack):
    """Heading path; the document's H1 is dropped once there is a deeper heading (the file path already names it)."""
    titles = [t for level, t in stack if not (level == 1 and len(stack) > 1)]
    return " > ".join(titles)


def _pack(lines, limit):
    """Group lines into passages of at most ~limit chars, breaking at blank lines or line ends.
    Table header rows are repeated on continuation passages so each passage stays readable."""
    out, cur, size = [], [], 0
    table_header = []
    for line in lines:
        is_table = line.lstrip().startswith("|")
        if is_table and not table_header:
            table_header = [line]
        elif is_table and len(table_header) == 1 and set(line.strip()) <= set("|-: "):
            table_header.append(line)
        elif not is_table:
            table_header = []
        if size + len(line) + 1 > limit and cur:
            out.append("\n".join(cur).strip())
            cur, size = [], 0
            if is_table and len(table_header) == 2 and line not in table_header:
                cur = list(table_header)
                size = sum(len(h) + 1 for h in table_header)
        cur.append(line)
        size += len(line) + 1
    if "\n".join(cur).strip():
        out.append("\n".join(cur).strip())
    return [p for p in out if p]


def chunk_file(path: Path, limit=CHUNK_CHARS):
    rel = path.relative_to(VAULT).as_posix()
    text = strip_frontmatter(path.read_text(encoding="utf-8"))
    chunks = []
    for section, body in _sections(text):
        for passage in _pack(body, limit):
            chunks.append(Chunk(id=f"{rel}#{len(chunks)}", path=rel, section=section or Path(rel).stem, text=passage))
    return chunks


def file_hash(path: Path):
    return hashlib.sha256(path.read_bytes()).hexdigest()
