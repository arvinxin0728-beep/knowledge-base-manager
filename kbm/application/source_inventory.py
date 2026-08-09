"""Reconcile source libraries, processed records, and renamed refinements."""

from __future__ import annotations

import hashlib
import json
import re
import unicodedata
from collections import defaultdict
from pathlib import Path
from typing import Any, Optional, Union

from kbm.domain.markdown import collect_markdown_files, markdown_title, split_frontmatter
from kbm.platform.paths import kb_path, system_active_file

SOURCE_EXTS = {".md", ".markdown", ".txt", ".html", ".htm", ".docx", ".epub", ".pdf"}


def _inside(path: Path, root: Path) -> bool:
    try:
        path.resolve().relative_to(root.resolve())
        return True
    except ValueError:
        return False


def normalized_source_name(value: Union[str, Path]) -> str:
    name = Path(str(value)).stem.strip()
    while re.match(r"^\d{4}-\d{2}-\d{2}\s+", name):
        name = name[11:].strip()
    normalized = unicodedata.normalize("NFKC", name).casefold()
    return "".join(char for char in normalized if unicodedata.category(char)[0] in {"L", "N"})


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def index_rows(cfg: dict[str, Any]) -> list[dict[str, Any]]:
    path = system_active_file(cfg, "processed-index.jsonl")
    if not path.exists():
        return []
    rows = []
    for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
        try:
            value = json.loads(line)
        except json.JSONDecodeError:
            continue
        if isinstance(value, dict):
            rows.append(value)
    return rows


def source_files(cfg: dict[str, Any]) -> list[Path]:
    files = []
    for raw in cfg.get("source_libraries", {}).values():
        if not raw:
            continue
        root = Path(raw).expanduser()
        if root.exists():
            files.extend(path.resolve() for path in root.rglob("*") if path.is_file() and path.suffix.lower() in SOURCE_EXTS)
    return sorted(set(files), key=str)


class RefinementCatalog:
    def __init__(self, cfg: dict[str, Any]) -> None:
        self.root = kb_path(cfg, "source_refinements").resolve()
        self.by_source_path: dict[str, list[Path]] = defaultdict(list)
        self.by_source_name: dict[str, list[Path]] = defaultdict(list)
        self.by_title: dict[str, list[Path]] = defaultdict(list)
        for refinement in collect_markdown_files(self.root):
            text = refinement.read_text(encoding="utf-8", errors="replace")
            meta, _body = split_frontmatter(text)
            source = str(meta.get("source_file") or meta.get("source_path") or "").strip()
            if not source:
                continue
            self.by_source_path[str(Path(source).expanduser().resolve())].append(refinement.resolve())
            identity = normalized_source_name(source)
            if identity:
                self.by_source_name[identity].append(refinement.resolve())
            title_identity = normalized_source_name(markdown_title(refinement, text))
            if title_identity:
                self.by_title[title_identity].append(refinement.resolve())

    @staticmethod
    def _unique(candidates: list[Path]) -> Optional[Path]:
        existing = sorted({path for path in candidates if path.is_file()}, key=str)
        return existing[0] if len(existing) == 1 else None

    def resolve(self, source: Path, record: Optional[dict[str, Any]] = None) -> Optional[Path]:
        if record:
            raw_output = record.get("output_file") or record.get("refinement_file")
            if raw_output:
                output = Path(str(raw_output)).expanduser()
                if output.is_file() and _inside(output, self.root):
                    return output.resolve()
        exact = self._unique(self.by_source_path.get(str(source.resolve()), []))
        if exact:
            return exact
        identity = normalized_source_name(source)
        by_source_name = self._unique(self.by_source_name.get(identity, []))
        if by_source_name:
            return by_source_name
        return self._unique(self.by_title.get(identity, []))


def audit_sources(cfg: dict[str, Any], include_hashes: bool = False) -> dict[str, Any]:
    rows = index_rows(cfg)
    by_path: dict[str, dict[str, Any]] = {}
    by_hash: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for record in rows:
        source = record.get("source_path") or record.get("source_file")
        if source:
            by_path[str(Path(str(source)).expanduser().resolve())] = record
        source_hash = str(record.get("source_sha256") or record.get("sha256") or "")
        if source_hash:
            by_hash[source_hash].append(record)
    catalog = RefinementCatalog(cfg)
    sources = source_files(cfg)
    unprocessed = []
    match_basis: dict[str, int] = defaultdict(int)
    for source in sources:
        record = by_path.get(str(source))
        source_hash = ""
        basis = "path" if record else ""
        if record is None and by_hash:
            source_hash = sha256_file(source)
            matches = by_hash.get(source_hash, [])
            if len(matches) == 1:
                record, basis = matches[0], "hash"
        refinement = catalog.resolve(source, record)
        if record and refinement:
            match_basis[basis or "refinement"] += 1
            continue
        if include_hashes and not source_hash:
            source_hash = sha256_file(source)
        unprocessed.append({
            "path": str(source), "sha256": source_hash or None,
            "reason": "missing_index_record" if record is None else "missing_or_ambiguous_refinement",
        })
    return {
        "ai_knowledge_base": cfg.get("ai_knowledge_base"),
        "source_count": len(sources), "processed_index_count": len(rows),
        "verified_processed_count": len(sources) - len(unprocessed),
        "match_basis_counts": dict(match_basis),
        "unprocessed_count": len(unprocessed), "unprocessed": unprocessed,
    }
