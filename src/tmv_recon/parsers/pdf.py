"""Local PDF extraction. Use as deterministic pre-pass before LLM."""
from __future__ import annotations
from pathlib import Path
import pypdf
import pdfplumber


def text(pdf_path: str | Path) -> str:
    r = pypdf.PdfReader(str(pdf_path))
    return "\n\n".join((p.extract_text() or "") for p in r.pages)


def pages(pdf_path: str | Path) -> list[str]:
    r = pypdf.PdfReader(str(pdf_path))
    return [(p.extract_text() or "") for p in r.pages]


def tables(pdf_path: str | Path) -> list[list[list[str]]]:
    """All tables across all pages, in order."""
    out: list[list[list[str]]] = []
    with pdfplumber.open(str(pdf_path)) as doc:
        for pg in doc.pages:
            for tbl in pg.extract_tables() or []:
                out.append(tbl)
    return out
