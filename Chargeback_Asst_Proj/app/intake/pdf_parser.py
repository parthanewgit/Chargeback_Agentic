from __future__ import annotations

from pathlib import Path

try:
    import fitz
except Exception:  # pragma: no cover
    fitz = None


def extract_pdf_text(file_path: str | Path) -> str:
    path = str(file_path)
    if fitz is None:
        raise RuntimeError('PyMuPDF is required for PDF text extraction.')
    doc = fitz.open(path)
    texts = []
    for page in doc:
        texts.append(page.get_text())
    return '\n'.join(texts)
