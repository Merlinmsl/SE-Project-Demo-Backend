from __future__ import annotations

import hashlib
from dataclasses import dataclass
from typing import Dict, Iterable, List, Tuple


@dataclass(frozen=True)
class Chunk:
    chunk_id: str
    text: str
    metadata: Dict[str, object]


def _stable_id(*parts: str) -> str:
    h = hashlib.sha1()
    for p in parts:
        h.update(p.encode("utf-8", errors="ignore"))
        h.update(b"\x1f")
    return h.hexdigest()


def _nice_cut(text: str, max_len: int) -> int:
    """Find a good split point near max_len (paragraph > newline > sentence > space)."""
    if len(text) <= max_len:
        return len(text)

    window = text[:max_len]
    for sep in ["\n\n", "\n", ". ", "? ", "! ", "; ", ", ", " "]:
        idx = window.rfind(sep)
        if idx != -1 and idx > max_len * 0.6:
            return idx + len(sep)
    return max_len


def chunk_pages(
    pages: Iterable[Tuple[int, str]],
    *,
    base_metadata: Dict[str, object],
    chunk_size_chars: int,
    overlap_chars: int,
) -> List[Chunk]:
    """
    Builds overlapping chunks from (page_number, page_text) items.
    Each chunk stores page_start/page_end metadata for citation.
    """
    chunks: List[Chunk] = []
    buf = ""
    page_start = None
    page_end = None
    chunk_index = 0

    for pnum, ptext in pages:
        if not ptext:
            continue

        if page_start is None:
            page_start = pnum
        page_end = pnum

        buf += ptext.strip() + "\n\n"

        while len(buf) > chunk_size_chars:
            cut = _nice_cut(buf, chunk_size_chars)
            piece = buf[:cut].strip()

            meta = dict(base_metadata)
            meta.update({"page_start": int(page_start), "page_end": int(page_end), "chunk_index": int(chunk_index)})

            cid = _stable_id(
                str(meta.get("source_file", "")),
                str(meta["page_start"]),
                str(meta["page_end"]),
                str(chunk_index),
                piece[:200],
            )

            chunks.append(Chunk(chunk_id=cid, text=piece, metadata=meta))
            chunk_index += 1

            keep_from = max(0, cut - overlap_chars)
            buf = buf[keep_from:].lstrip()

    # flush remaining buffer
    remaining = buf.strip()
    if remaining:
        meta = dict(base_metadata)
        meta.update({"page_start": int(page_start or 1), "page_end": int(page_end or 1), "chunk_index": int(chunk_index)})

        cid = _stable_id(
            str(meta.get("source_file", "")),
            str(meta["page_start"]),
            str(meta["page_end"]),
            str(chunk_index),
            remaining[:200],
        )

        chunks.append(Chunk(chunk_id=cid, text=remaining, metadata=meta))

    return chunks
