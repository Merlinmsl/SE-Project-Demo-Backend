from __future__ import annotations

from collections import Counter
from pathlib import Path
from typing import Dict, List

from app.rag.config import RESOURCES_DIR, CHUNK_SIZE_CHARS, CHUNK_OVERLAP_CHARS
from app.rag.pdfreader import read_pdf_pages
from app.rag.chunking import Chunk, chunk_pages


def list_pdfs(resources_dir: Path = RESOURCES_DIR) -> List[Path]:
    resources_dir.mkdir(parents=True, exist_ok=True)
    return sorted(resources_dir.glob("*.pdf"))


def _infer_subject(filename: str) -> str:
    stem = Path(filename).stem.lower().strip()
    for sep in ["-", "_"]:
        stem = stem.replace(sep, " ")
    parts = [p for p in stem.split() if p]
    return parts[0] if parts else "unknown"


def _remove_boilerplate(pages_text: List[str], min_ratio: float = 0.60, max_line_len: int = 80) -> List[str]:
    """
    Remove repeated header/footer lines that appear in many pages.
    This improves retrieval quality for textbooks.
    """
    if not pages_text:
        return pages_text

    per_page_lines = []
    for t in pages_text:
        lines = [ln.strip() for ln in t.splitlines() if ln.strip()]
        small_lines = [ln for ln in lines if len(ln) <= max_line_len]
        per_page_lines.append(set(small_lines))

    counts = Counter()
    for s in per_page_lines:
        counts.update(s)

    threshold = int(len(per_page_lines) * min_ratio)
    boilerplate = {line for line, c in counts.items() if c >= threshold}

    cleaned = []
    for t in pages_text:
        lines = t.splitlines()
        kept = [ln for ln in lines if ln.strip() not in boilerplate]
        cleaned.append("\n".join(kept).strip())

    return cleaned


def build_chunks_from_pdf(pdf_path: Path) -> List[Chunk]:
    pages = read_pdf_pages(pdf_path)
    page_texts = [p.text for p in pages]

    # remove repeating headers/footers
    page_texts = _remove_boilerplate(page_texts)

    base_meta: Dict[str, object] = {
        "source_file": pdf_path.name,
        "subject": _infer_subject(pdf_path.name),
        "grade": "9",
    }

    usable_pages = []
    for i, t in enumerate(page_texts, start=1):
        if t and len(t) > 30:
            usable_pages.append((i, t))

    if len(usable_pages) < max(3, int(0.05 * max(1, len(pages)))):
        print(f"[WARN] Very little text extracted from {pdf_path.name}. If it's scanned, you need OCR.")

    return chunk_pages(
        usable_pages,
        base_metadata=base_meta,
        chunk_size_chars=CHUNK_SIZE_CHARS,
        overlap_chars=CHUNK_OVERLAP_CHARS,
    )
