"""Document retriever for project documentation. Uses keyword-based retrieval (no new deps)."""

import re
from pathlib import Path
from typing import List, Tuple

# Project root (one level up from utils/)
_PROJECT_ROOT = Path(__file__).resolve().parent.parent

# Documentation paths to index (relative to project root)
_DOC_PATHS = [
    "README.md",
    "integrations/pinterest/SOLUTION_TRACKING.md",
    "integrations/canva/README.md",
    "integrations/pinterest/README.md",
    "agents/design/README.md",
    "workflows/canva/README.md",
    "workflows/pinterest/README.md",
    "workflows/design/README.md",
    "PINTEREST_PUBLISHER_COMPARISON.md",
    "tests/integrations/pinterest/README.md",
]

# Project structure summary for context
_PROJECT_STRUCTURE = """
Project Structure:
- agents/design/ - Design generation agents (Executor, Evaluator)
- workflows/design/ - Design workflow (theme, title, prompts, keywords)
- workflows/canva/ - Canva design workflow
- workflows/pinterest/ - Pinterest publishing workflow
- integrations/canva/ - Canva browser automation
- integrations/pinterest/ - Pinterest browser automation
- tools/ - Content generation tools (theme, title, prompts, keywords)
- ui/tabs/ - Streamlit tabs (Guide, Design Generation, Image Generation, Canva, Pinterest)
"""


def _load_doc(path: Path) -> str:
    """Load a single document. Returns empty string if file not found or unreadable."""
    try:
        if path.exists():
            return path.read_text(encoding="utf-8", errors="replace")
    except Exception:
        pass
    return ""


def _split_by_headers(text: str, source: str) -> List[Tuple[str, str]]:
    """Split markdown by ## headers. Returns list of (chunk_text, source)."""
    if not text.strip():
        return []
    # Split on lines starting with ##
    parts = re.split(r"\n(?=#{2,3}\s)", text)
    chunks = []
    for part in parts:
        part = part.strip()
        if part:
            chunks.append((part, source))
    if not chunks:
        chunks.append((text.strip(), source))
    return chunks


def _build_chunks() -> List[Tuple[str, str]]:
    """Load all docs and build chunks. Returns list of (chunk_text, source_path)."""
    chunks = []
    for rel_path in _DOC_PATHS:
        path = _PROJECT_ROOT / rel_path
        content = _load_doc(path)
        if content:
            for chunk_text, _ in _split_by_headers(content, rel_path):
                if chunk_text.strip():
                    chunks.append((chunk_text, rel_path))
    # Add project structure as a chunk
    chunks.append((_PROJECT_STRUCTURE.strip(), "project_structure"))
    return chunks


def _score_chunk(query: str, chunk: str) -> float:
    """Simple keyword scoring: count matches of query words in chunk (case-insensitive)."""
    q_words = set(w.lower() for w in re.findall(r"\w+", query) if len(w) > 2)
    if not q_words:
        return 0.0
    chunk_lower = chunk.lower()
    matches = sum(1 for w in q_words if w in chunk_lower)
    return matches / len(q_words)


def retrieve(query: str, k: int = 5) -> List[Tuple[str, str]]:
    """
    Retrieve top-k chunks most relevant to the query.

    Args:
        query: User question
        k: Number of chunks to return

    Returns:
        List of (chunk_text, source_path) tuples, sorted by relevance.
    """
    chunks = _build_chunks()
    if not chunks:
        return []
    scored = [(c, s, _score_chunk(query, c)) for c, s in chunks]
    scored.sort(key=lambda x: x[2], reverse=True)
    # Filter out zero-score chunks
    scored = [(c, s) for c, s, score in scored if score > 0]
    return scored[:k]


def get_all_chunks() -> List[Tuple[str, str]]:
    """Load all chunks (for debugging)."""
    return _build_chunks()
