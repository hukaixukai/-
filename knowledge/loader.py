# new-agent/knowledge/loader.py
"""Load and chunk documents (PDF, images, text) for the knowledge base."""

from __future__ import annotations

import re
from pathlib import Path

import fitz  # PyMuPDF
from PIL import Image


def load_pdf(file_path: str | Path) -> str:
    """Extract text from a PDF file."""
    doc = fitz.open(str(file_path))
    try:
        texts = []
        for page in doc:
            text = page.get_text()
            if text.strip():
                texts.append(text)
        return "\n\n".join(texts)
    finally:
        doc.close()


def load_image(file_path: str | Path) -> str:
    """Extract text from an image via OCR (requires pytesseract)."""
    try:
        import pytesseract
        img = Image.open(file_path)
        return pytesseract.image_to_string(img, lang="chi_sim+eng")
    except ImportError:
        return f"[图片文件: {file_path.name} - 需要安装 pytesseract 才能提取图片中的文字]"


def load_text(file_path: str | Path) -> str:
    """Load a plain text or markdown file."""
    return Path(file_path).read_text(encoding="utf-8")


def load_document(file_path: str | Path) -> tuple[str, str]:
    """Load any supported document. Returns (text, source_name)."""
    p = Path(file_path)
    suffix = p.suffix.lower()

    if suffix == ".pdf":
        return load_pdf(p), p.name
    elif suffix in (".png", ".jpg", ".jpeg", ".bmp", ".tiff", ".gif"):
        return load_image(p), p.name
    elif suffix in (".txt", ".md", ".py", ".java", ".c", ".cpp", ".h", ".js", ".ts", ".html", ".css", ".json", ".yaml", ".yml"):
        return load_text(p), p.name
    else:
        # Try as text
        try:
            return load_text(p), p.name
        except Exception:
            return "", p.name


def chunk_text(text: str, chunk_size: int = 500, overlap: int = 100) -> list[str]:
    """Split text into overlapping chunks.

    Uses paragraph-level splitting first, then falls back to sentence-level.
    """
    if not text.strip():
        return []

    # Split by paragraphs
    paragraphs = re.split(r"\n\s*\n", text)
    paragraphs = [p.strip() for p in paragraphs if p.strip()]

    chunks: list[str] = []
    current = ""

    for para in paragraphs:
        if len(current) + len(para) + 2 <= chunk_size:
            current = current + "\n\n" + para if current else para
        else:
            if current:
                chunks.append(current.strip())
            # If a single paragraph exceeds chunk_size, split by sentences
            if len(para) > chunk_size:
                sentences = re.split(r"(?<=[。！？.!?])\s*", para)
                current = ""
                for sent in sentences:
                    if len(current) + len(sent) + 1 <= chunk_size:
                        current = current + " " + sent if current else sent
                    else:
                        if current:
                            chunks.append(current.strip())
                        # If single sentence > chunk_size, force-append it as its own chunk
                        if len(sent) > chunk_size:
                            chunks.append(sent.strip())
                            current = ""
                        else:
                            current = sent
            else:
                current = para

    if current.strip():
        chunks.append(current.strip())

    # Apply overlap: prepend tail of previous chunk
    if overlap > 0 and len(chunks) > 1:
        overlapped = [chunks[0]]
        for i in range(1, len(chunks)):
            prev_tail = chunks[i - 1][-overlap:]
            overlapped.append(prev_tail + " ... " + chunks[i])
        chunks = overlapped

    return chunks


def load_and_chunk(file_path: str | Path, chunk_size: int = 500, overlap: int = 100) -> list[dict]:
    """Load a document and return chunked results with metadata.

    Returns list of {"text": str, "source": str, "chunk_id": int}.
    """
    text, source = load_document(file_path)
    if not text.strip():
        return []
    chunks = chunk_text(text, chunk_size, overlap)
    return [{"text": c, "source": source, "chunk_id": i} for i, c in enumerate(chunks)]
