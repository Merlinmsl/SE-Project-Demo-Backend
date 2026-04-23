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
    # Try splitting at logical breaks
    for sep in ["\n\n", "\n", ". ", "? ", "! ", "; ", ", ", " "]:
        idx = window.rfind(sep)
        # Only split if we have at least 60% of the max_len to avoid tiny chunks
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
    Tries to be precise about which pages contribute to each chunk.
    """
    chunks: List[Chunk] = []
    
    # We maintain a list of (char_offset_in_buf, page_number)
    # to know exactly which page a slice of buf belongs to.
    buf = ""
    # List of (starting_pos_in_buf, page_number)
    page_map: List[Tuple[int, int]] = []
    
    chunk_index = 0

    for pnum, ptext in pages:
        if not ptext:
            continue
        
        # Mark where this page starts in the buffer
        page_map.append((len(buf), pnum))
        buf += ptext.strip() + "\n\n"

        while len(buf) > chunk_size_chars:
            cut = _nice_cut(buf, chunk_size_chars)
            piece = buf[:cut].strip()
            
            # Determine pages covered by [0, cut]
            pages_in_chunk = []
            for i, (offset, pn) in enumerate(page_map):
                # If page start offset is before the cut, it might be in this chunk
                if offset < cut:
                    pages_in_chunk.append(pn)
                else:
                    break
            
            # If a page starts after the cut but some of its text was before the cut (unlikely with nice_cut but possible)
            # Or if the last page in pages_in_chunk continues after the cut
            
            p_start = min(pages_in_chunk) if pages_in_chunk else pnum
            p_end = max(pages_in_chunk) if pages_in_chunk else pnum

            meta = dict(base_metadata)
            meta.update({
                "page_start": int(p_start), 
                "page_end": int(p_end), 
                "chunk_index": int(chunk_index),
                "pages": ",".join(map(str, sorted(set(pages_in_chunk))))
            })

            cid = _stable_id(
                str(meta.get("source_file", "")),
                str(chunk_index),
                piece[:100],
            )

            chunks.append(Chunk(chunk_id=cid, text=piece, metadata=meta))
            chunk_index += 1

            # Shift buffer
            keep_from = max(0, cut - overlap_chars)
            buf = buf[keep_from:].lstrip()
            
            # Rebuild page_map for the new buffer
            new_map = []
            shift = keep_from
            for offset, pn in page_map:
                # If the page end (next page start) is after where we keep, it's still in buf
                # But for simplicity, we just adjust offsets and filter those that are completely gone
                new_offset = offset - shift
                # Even if new_offset is negative, it means this page started before the kept part
                new_map.append((new_offset, pn))
            
            # Filter pages that are completely before the new buffer start
            # (A page is still relevant if it ends after the new buffer start)
            final_map = []
            for i in range(len(new_map)):
                off, pn = new_map[i]
                next_off = new_map[i+1][0] if i+1 < len(new_map) else len(buf) + shift
                if next_off > 0: # Page ends after the cut
                    final_map.append((max(0, off), pn))
            page_map = final_map

    # Flush remaining
    remaining = buf.strip()
    if remaining:
        pages_in_chunk = [pn for off, pn in page_map]
        p_start = min(pages_in_chunk) if pages_in_chunk else 1
        p_end = max(pages_in_chunk) if pages_in_chunk else 1
        
        meta = dict(base_metadata)
        meta.update({
            "page_start": int(p_start), 
            "page_end": int(p_end), 
            "chunk_index": int(chunk_index),
            "pages": ",".join(map(str, sorted(set(pages_in_chunk))))
        })

        cid = _stable_id(
            str(meta.get("source_file", "")),
            str(chunk_index),
            remaining[:100],
        )

        chunks.append(Chunk(chunk_id=cid, text=remaining, metadata=meta))

    return chunks
