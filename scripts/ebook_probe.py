#!/usr/bin/env python3
"""Extract orientation text and chunks from common ebook formats."""

from __future__ import annotations

import argparse
import html
import json
import re
import sys
import zipfile
from pathlib import Path
from xml.etree import ElementTree as ET


TEXT_SUFFIXES = {".txt", ".md", ".markdown"}
HTML_SUFFIXES = {".html", ".htm", ".xhtml"}


def clean_text(text: str) -> str:
    text = html.unescape(text)
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def strip_tags(text: str) -> str:
    text = re.sub(r"(?is)<(script|style).*?>.*?</\1>", " ", text)
    text = re.sub(r"(?is)<br\s*/?>", "\n", text)
    text = re.sub(r"(?is)</(p|div|h[1-6]|li|tr|section|article)>", "\n", text)
    text = re.sub(r"(?is)<[^>]+>", " ", text)
    return clean_text(text)


def read_text_file(path: Path) -> str:
    for encoding in ("utf-8", "utf-8-sig", "gb18030", "latin-1"):
        try:
            return clean_text(path.read_text(encoding=encoding))
        except UnicodeDecodeError:
            continue
    raise ValueError(f"Unable to decode text file: {path}")


def read_docx(path: Path) -> str:
    with zipfile.ZipFile(path) as zf:
        names = [n for n in zf.namelist() if n.startswith("word/document") and n.endswith(".xml")]
        if not names:
            raise ValueError("DOCX document XML not found")
        root = ET.fromstring(zf.read("word/document.xml"))
    ns = {"w": "http://schemas.openxmlformats.org/wordprocessingml/2006/main"}
    paragraphs = []
    for para in root.findall(".//w:p", ns):
        parts = [node.text or "" for node in para.findall(".//w:t", ns)]
        if parts:
            paragraphs.append("".join(parts))
    return clean_text("\n\n".join(paragraphs))


def epub_manifest(zf: zipfile.ZipFile) -> tuple[str | None, list[str]]:
    container = ET.fromstring(zf.read("META-INF/container.xml"))
    ns = {"c": "urn:oasis:names:tc:opendocument:xmlns:container"}
    rootfile = container.find(".//c:rootfile", ns)
    if rootfile is None:
        return None, []
    opf_path = rootfile.attrib["full-path"]
    opf_root = ET.fromstring(zf.read(opf_path))
    base = str(Path(opf_path).parent)
    if base == ".":
        base = ""
    manifest = {}
    for item in opf_root.findall(".//{*}manifest/{*}item"):
        manifest[item.attrib.get("id")] = item.attrib.get("href", "")
    spine_items = []
    for itemref in opf_root.findall(".//{*}spine/{*}itemref"):
        href = manifest.get(itemref.attrib.get("idref"))
        if href:
            spine_items.append(str(Path(base, href)))
    title_node = opf_root.find(".//{http://purl.org/dc/elements/1.1/}title")
    title = title_node.text.strip() if title_node is not None and title_node.text else None
    return title, spine_items


def read_epub(path: Path) -> tuple[str | None, str]:
    with zipfile.ZipFile(path) as zf:
        title, spine = epub_manifest(zf)
        parts = []
        candidates = spine or [n for n in zf.namelist() if Path(n).suffix.lower() in HTML_SUFFIXES]
        for name in candidates:
            try:
                raw = zf.read(name).decode("utf-8", errors="replace")
            except KeyError:
                continue
            parts.append(strip_tags(raw))
    return title, clean_text("\n\n".join(p for p in parts if p))


def read_pdf(path: Path) -> str:
    errors = []
    for module_name in ("pypdf", "PyPDF2"):
        try:
            module = __import__(module_name)
            reader = module.PdfReader(str(path))
            return clean_text("\n\n".join(page.extract_text() or "" for page in reader.pages))
        except Exception as exc:  # noqa: BLE001
            errors.append(f"{module_name}: {exc}")
    try:
        import pdfplumber  # type: ignore

        with pdfplumber.open(path) as pdf:
            return clean_text("\n\n".join(page.extract_text() or "" for page in pdf.pages))
    except Exception as exc:  # noqa: BLE001
        errors.append(f"pdfplumber: {exc}")
    raise ValueError("PDF text extraction failed. This may need OCR. " + " | ".join(errors))


def extract(path: Path) -> tuple[str | None, str]:
    suffix = path.suffix.lower()
    if suffix in TEXT_SUFFIXES:
        return None, read_text_file(path)
    if suffix in HTML_SUFFIXES:
        return None, strip_tags(read_text_file(path))
    if suffix == ".docx":
        return None, read_docx(path)
    if suffix == ".epub":
        return read_epub(path)
    if suffix == ".pdf":
        return None, read_pdf(path)
    raise ValueError(f"Unsupported file type: {suffix}")


def candidate_chapters(text: str) -> list[dict[str, object]]:
    pattern = re.compile(
        r"(?im)^(chapter\s+\d+|第[一二三四五六七八九十百千0-9]+[章节回]|[0-9]+\.\s+\S.{0,80}|#{1,3}\s+.+)$"
    )
    chapters = []
    for match in pattern.finditer(text):
        chapters.append({"title": match.group(0).strip("# ").strip(), "char_offset": match.start()})
    return chapters[:200]


def chunk_text(text: str, size: int = 5000, overlap: int = 350) -> list[dict[str, object]]:
    chunks = []
    start = 0
    index = 1
    while start < len(text):
        end = min(len(text), start + size)
        if end < len(text):
            boundary = max(text.rfind("\n\n", start, end), text.rfind(". ", start, end))
            if boundary > start + int(size * 0.55):
                end = boundary + 1
        body = text[start:end].strip()
        if body:
            chunks.append({"id": f"chunk-{index:04d}", "start": start, "end": end, "text": body})
            index += 1
        if end >= len(text):
            break
        start = max(end - overlap, start + 1)
    return chunks


def main() -> int:
    parser = argparse.ArgumentParser(description="Extract text and reading chunks from an ebook.")
    parser.add_argument("book", type=Path)
    parser.add_argument("--out-dir", type=Path, required=True)
    parser.add_argument("--chunk-size", type=int, default=5000)
    args = parser.parse_args()

    book = args.book.expanduser().resolve()
    out_dir = args.out_dir.expanduser().resolve()
    out_dir.mkdir(parents=True, exist_ok=True)

    title, text = extract(book)
    if not text:
        raise SystemExit("No extractable text found. The file may be scanned or encrypted.")

    chunks = chunk_text(text, size=args.chunk_size)
    full_text_path = out_dir / "full_text.txt"
    chunks_path = out_dir / "chunks.jsonl"
    manifest_path = out_dir / "manifest.json"
    full_text_path.write_text(text, encoding="utf-8")
    with chunks_path.open("w", encoding="utf-8") as fh:
        for chunk in chunks:
            fh.write(json.dumps(chunk, ensure_ascii=False) + "\n")

    words = re.findall(r"\w+", text, flags=re.UNICODE)
    manifest = {
        "source_file": str(book),
        "detected_format": book.suffix.lower().lstrip("."),
        "title": title or book.stem,
        "characters": len(text),
        "approx_words": len(words),
        "chunk_count": len(chunks),
        "candidate_chapters": candidate_chapters(text),
        "outputs": {"full_text": str(full_text_path), "chunks": str(chunks_path)},
    }
    manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({"manifest": str(manifest_path), "chunks": len(chunks)}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
