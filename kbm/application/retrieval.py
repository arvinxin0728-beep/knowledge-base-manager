"""Device-local, citation-first lexical retrieval over durable knowledge artifacts."""

from __future__ import annotations

import hashlib
import math
import re
import sqlite3
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable

from kbm.platform.paths import runtime_dir


LAYERS = {
    "source_refinement": "source_refinements",
    "topic_page": "topic_pages",
    "reusable_asset": "reusable_assets",
    "output": "outputs",
}
TOKEN_RE = re.compile(r"[A-Za-z0-9_]+|[\u3400-\u9fff]")
NAVIGATION_HEADINGS = {"关联知识", "相关输出", "关联输出", "相关来源", "关联来源", "related outputs", "related sources", "related knowledge"}


def now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def retrieval_db_path(cfg: dict[str, Any]) -> Path:
    return runtime_dir(cfg) / "retrieval.sqlite3"


def connect_index(cfg: dict[str, Any], *, create: bool = False) -> sqlite3.Connection:
    path = retrieval_db_path(cfg)
    if not create and not path.exists():
        raise ValueError("retrieval_index_not_initialized")
    path.parent.mkdir(parents=True, exist_ok=True)
    db = sqlite3.connect(path, timeout=30)
    db.row_factory = sqlite3.Row
    db.executescript(
        """
        CREATE TABLE IF NOT EXISTS chunks (
          chunk_id TEXT PRIMARY KEY,
          artifact_id TEXT NOT NULL,
          layer TEXT NOT NULL,
          title TEXT NOT NULL,
          path TEXT NOT NULL,
          relative_path TEXT NOT NULL,
          start_line INTEGER NOT NULL,
          end_line INTEGER NOT NULL,
          heading TEXT,
          content TEXT NOT NULL,
          content_sha256 TEXT NOT NULL,
          indexed_at TEXT NOT NULL
        );
        CREATE INDEX IF NOT EXISTS chunks_layer_idx ON chunks(layer);
        CREATE INDEX IF NOT EXISTS chunks_artifact_idx ON chunks(artifact_id);
        CREATE TABLE IF NOT EXISTS retrieval_meta (key TEXT PRIMARY KEY, value TEXT NOT NULL);
        """
    )
    return db


def artifact_roots(cfg: dict[str, Any]) -> list[tuple[str, Path]]:
    base = Path(cfg["ai_knowledge_base"]).expanduser().resolve()
    roots = []
    for layer, mapping_key in LAYERS.items():
        relative = cfg.get("mapping", {}).get(mapping_key)
        if relative:
            roots.append((layer, base / relative))
    return roots


def discover_artifacts(cfg: dict[str, Any], layers: Iterable[str] = ()) -> list[tuple[str, Path]]:
    selected = set(layers)
    return [
        (layer, path)
        for layer, root in artifact_roots(cfg) if not selected or layer in selected
        for path in sorted(root.rglob("*.md"), key=str) if path.is_file()
    ]


def _title(lines: list[str], fallback: str) -> str:
    for line in lines:
        if line.startswith("# "):
            return line[2:].strip() or fallback
    return fallback


def _segments(lines: list[str], max_chars: int = 1400, line_offset: int = 0) -> list[tuple[int, int, str, str]]:
    segments: list[tuple[int, int, str, str]] = []
    start = 1 + line_offset
    heading = ""
    buffer: list[str] = []

    def flush(end: int) -> None:
        nonlocal start, buffer
        content = "\n".join(buffer).strip()
        has_prose = any(line.strip() and not line.startswith("#") for line in buffer)
        if content and has_prose:
            segments.append((start, end, heading, content))
        buffer = []

    for number, line in enumerate(lines, 1 + line_offset):
        is_heading = line.startswith("#") and line.lstrip("#").startswith(" ")
        projected = sum(len(item) + 1 for item in buffer) + len(line)
        if buffer and (is_heading or projected > max_chars):
            flush(number - 1)
            start = number
        if is_heading:
            heading = line.lstrip("# ").strip()
        buffer.append(line)
    flush(len(lines) + line_offset)
    return segments


def build_rows(cfg: dict[str, Any], layers: Iterable[str] = ()) -> list[dict[str, Any]]:
    base = Path(cfg["ai_knowledge_base"]).expanduser().resolve()
    stamp = now()
    rows = []
    for layer, path in discover_artifacts(cfg, layers):
        text = path.read_text(encoding="utf-8", errors="ignore")
        lines = text.splitlines()
        body_lines = lines
        line_offset = 0
        if lines and lines[0].strip() == "---":
            closing = next((index for index, line in enumerate(lines[1:], 1) if line.strip() == "---"), None)
            if closing is not None:
                line_offset = closing + 1
                body_lines = lines[line_offset:]
        relative = str(path.resolve().relative_to(base))
        artifact_id = hashlib.sha256(relative.encode("utf-8")).hexdigest()[:20]
        title = _title(body_lines, path.stem)
        for start, end, heading, content in _segments(body_lines, line_offset=line_offset):
            chunk_id = hashlib.sha256(f"{relative}:{start}:{end}:{content}".encode("utf-8")).hexdigest()[:24]
            rows.append({
                "chunk_id": chunk_id, "artifact_id": artifact_id, "layer": layer,
                "title": title, "path": str(path.resolve()), "relative_path": relative,
                "start_line": start, "end_line": end, "heading": heading,
                "content": content, "content_sha256": hashlib.sha256(content.encode("utf-8")).hexdigest(),
                "indexed_at": stamp,
            })
    return rows


def rebuild(cfg: dict[str, Any], *, layers: Iterable[str] = (), apply: bool = False) -> dict[str, Any]:
    rows = build_rows(cfg, layers)
    artifacts = len({row["artifact_id"] for row in rows})
    result = {"applied": apply, "engine": "lexical-v1", "artifacts": artifacts, "chunks": len(rows), "database": str(retrieval_db_path(cfg))}
    if not apply:
        return result
    with connect_index(cfg, create=True) as db:
        db.execute("BEGIN")
        db.execute("DELETE FROM chunks")
        db.executemany(
            "INSERT INTO chunks(chunk_id,artifact_id,layer,title,path,relative_path,start_line,end_line,heading,content,content_sha256,indexed_at) VALUES(:chunk_id,:artifact_id,:layer,:title,:path,:relative_path,:start_line,:end_line,:heading,:content,:content_sha256,:indexed_at)",
            rows,
        )
        db.execute("INSERT OR REPLACE INTO retrieval_meta(key,value) VALUES('engine','lexical-v1')")
        db.execute("INSERT OR REPLACE INTO retrieval_meta(key,value) VALUES('built_at',?)", (now(),))
        db.commit()
    return result


def tokens(value: str) -> list[str]:
    return [token.lower() for token in TOKEN_RE.findall(value)]


def _snippet(content: str, query: str, limit: int = 260) -> str:
    flat = re.sub(r"\s+", " ", content).strip()
    position = flat.lower().find(query.lower())
    if position < 0:
        position = min((flat.lower().find(term) for term in tokens(query) if flat.lower().find(term) >= 0), default=0)
    start = max(0, position - 70)
    snippet = flat[start:start + limit]
    return ("…" if start else "") + snippet + ("…" if start + limit < len(flat) else "")


def query(cfg: dict[str, Any], text: str, *, limit: int = 10, layers: Iterable[str] = ()) -> dict[str, Any]:
    terms = tokens(text)
    if not terms:
        raise ValueError("query_has_no_searchable_terms")
    with connect_index(cfg) as db:
        required_entities = {term for term in terms if len(term) >= 2 and re.fullmatch(r"[a-z0-9_]+", term)}
        selected = tuple(layers)
        if selected:
            placeholders = ",".join("?" for _ in selected)
            rows = db.execute(f"SELECT * FROM chunks WHERE layer IN ({placeholders})", selected).fetchall()
        else:
            rows = db.execute("SELECT * FROM chunks").fetchall()
        document_frequency = Counter()
        row_terms = []
        for row in rows:
            counts = Counter(tokens(f"{row['heading'] or ''} {row['content']}"))
            title_terms = set(tokens(row["title"]))
            row_terms.append((row, counts, title_terms))
            document_frequency.update((set(counts) | title_terms) & set(terms))
        total = max(len(rows), 1)
        ranked = []
        for row, counts, title_terms in row_terms:
            if required_entities and not required_entities <= (set(counts) | title_terms):
                continue
            score = 0.0
            for term in terms:
                if counts[term]:
                    score += (1 + math.log(counts[term])) * (1 + math.log((total + 1) / (document_frequency[term] + 1)))
                if term in title_terms:
                    score += 1.5
            body = f"{row['heading'] or ''} {row['content']}".lower()
            if text.lower() in body:
                score += 5.0
            elif text.lower() in row["title"].lower():
                score += 3.0
            if (row["heading"] or "").strip().lower() in NAVIGATION_HEADINGS:
                score *= 0.25
            if score:
                ranked.append((score, row))
        ranked.sort(key=lambda item: (-item[0], item[1]["relative_path"], item[1]["start_line"]))
        results = [
            {
                "rank": rank, "score": round(score, 4), "chunk_id": row["chunk_id"],
                "artifact_id": row["artifact_id"], "layer": row["layer"], "title": row["title"],
                "heading": row["heading"], "citation": {
                    "path": row["path"], "relative_path": row["relative_path"],
                    "start_line": row["start_line"], "end_line": row["end_line"],
                },
                "snippet": _snippet(row["content"], text),
            }
            for rank, (score, row) in enumerate(ranked[:limit], 1)
        ]
        built = db.execute("SELECT value FROM retrieval_meta WHERE key='built_at'").fetchone()
    return {"engine": "lexical-v1", "query": text, "built_at": built["value"] if built else None, "result_count": len(results), "results": results}


def status(cfg: dict[str, Any]) -> dict[str, Any]:
    path = retrieval_db_path(cfg)
    if not path.exists():
        return {"initialized": False, "engine": "lexical-v1", "database": str(path), "artifacts": 0, "chunks": 0}
    with connect_index(cfg) as db:
        counts = db.execute("SELECT COUNT(DISTINCT artifact_id) AS artifacts,COUNT(*) AS chunks FROM chunks").fetchone()
        built = db.execute("SELECT value FROM retrieval_meta WHERE key='built_at'").fetchone()
    return {"initialized": True, "engine": "lexical-v1", "database": str(path), "built_at": built["value"] if built else None, **dict(counts)}
