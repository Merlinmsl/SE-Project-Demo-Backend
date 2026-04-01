from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path
from typing import List

from pypdf import PdfReader


@dataclass(frozen=True)
class PDFPage:
    source_file: str
    page_number: int  # 1-based
    text: str


_HYPHEN_LINEBREAK = re.compile(r"(\w)-\n(\w)")
_MANY_NEWLINES = re.compile(r"\n{3,}")
_SPACE_BEFORE_NEWLINE = re.compile(r"[ \t]+\n")


def clean_text(text: str) -> str:
    if not text:
        return ""
    text = text.replace("\r", "\n")
    text = _SPACE_BEFORE_NEWLINE.sub("\n", text)
    text = _HYPHEN_LINEBREAK.sub(r"\1\2", text)
    text = re.sub(r"[ \t]{2,}", " ", text)
    text = _MANY_NEWLINES.sub("\n\n", text)
    return text.strip()


def read_pdf_pages(pdf_path: Path) -> List[PDFPage]:
    """
    Extract text page-by-page.
    If the PDF is scanned (image-only), extracted text may be empty -> needs OCR.
    """
    reader = PdfReader(str(pdf_path))
    out: List[PDFPage] = []

    for i, page in enumerate(reader.pages, start=1):
        raw = page.extract_text() or ""
        out.append(
            PDFPage(
                source_file=pdf_path.name,
                page_number=i,
                text=clean_text(raw),
            )
        )
    return out
