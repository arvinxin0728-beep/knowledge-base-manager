#!/usr/bin/env python3
"""Add Obsidian metadata, backlinks, and MOC pages for knowledge-base outputs."""

from __future__ import annotations

import argparse
import json
import re
from datetime import date
from pathlib import Path
from typing import Any

DEFAULT_TOPIC_PAGE_SUBDIRS = {
    "pages": "pages",
    "moc": "moc",
}

STAGE_TAGS = {
    "20-topic-pages": "主题页",
    "30-reusable-assets": "可复用资产",
    "40-outputs": "输出",
    "主题页": "主题页",
    "可复用资产": "可复用资产",
    "输出": "输出",
    "方法论": "方法论",
    "框架图谱": "框架图谱",
    "费曼解释": "费曼解释",
    "文章草稿": "文章草稿",
    "方案素材": "方案素材",
    "来源精炼": "来源精炼",
}


def load_config(path: Path) -> dict[str, Any]:
    cfg = json.loads(path.read_text(encoding="utf-8"))
    cfg.setdefault("topic_page_subdirs", dict(DEFAULT_TOPIC_PAGE_SUBDIRS))
    obsidian = cfg.get("integrations", {}).get("obsidian", {})
    taxonomy = obsidian.get("taxonomy")
    clusters: list[dict[str, Any]] = []
    if taxonomy:
        taxonomy_path = Path(taxonomy)
        if not taxonomy_path.is_absolute():
            taxonomy_path = Path(cfg["ai_knowledge_base"]) / taxonomy_path
        data = json.loads(taxonomy_path.read_text(encoding="utf-8"))
        clusters = data.get("clusters", [])
    cfg["_obsidian_clusters"] = clusters
    return cfg


def kb_dir(cfg: dict[str, Any], key: str) -> Path:
    return Path(cfg["ai_knowledge_base"]) / cfg["mapping"][key]


def topic_pages_content_dir(cfg: dict[str, Any]) -> Path:
    subdir = cfg.get("topic_page_subdirs", {}).get("pages")
    root = kb_dir(cfg, "topic_pages")
    return root / subdir if subdir else root


def topic_pages_moc_dir(cfg: dict[str, Any]) -> Path:
    subdir = cfg.get("topic_page_subdirs", {}).get("moc")
    root = kb_dir(cfg, "topic_pages")
    return root / subdir if subdir else root


def vault_rel(path: Path, cfg: dict[str, Any]) -> str:
    return str(path.relative_to(Path(cfg["ai_knowledge_base"])))


def wiki(title: str) -> str:
    return f"[[{title}]]"


def wiki_for_path(path: Path, title: str | None = None) -> str:
    display = (title or path.stem).strip()
    if display and display != path.stem:
        return f"[[{path.stem}|{display}]]"
    return f"[[{path.stem}]]"


def link_key(value: str) -> str:
    return re.sub(r"\s+", "", str(value).strip().split("|", 1)[0].split("#", 1)[0])


def build_link_index(paths: list[Path]) -> dict[str, str]:
    index: dict[str, str] = {}
    for path in paths:
        text = path.read_text(encoding="utf-8", errors="ignore")
        title = file_title(path, text)
        canonical = wiki_for_path(path, title)
        for alias in {path.stem, title, title.replace(" ", "")}:
            key = link_key(alias)
            if key and key not in index:
                index[key] = canonical
    return index


def canonicalize_wiki_item(value: str, link_index: dict[str, str], unlink_unresolved: bool = False) -> str:
    value = str(value).strip().strip('"')
    if value.startswith("[[") and value.endswith("]]"):
        inner = value[2:-2]
        target = inner.split("|", 1)[0]
        display = inner.split("|", 1)[1] if "|" in inner else ""
    else:
        target = value
        display = ""
    canonical = link_index.get(link_key(target))
    if not canonical:
        if unlink_unresolved:
            return display or target
        return wiki(target) if not value.startswith("[[") else value
    if display:
        stem = canonical[2:-2].split("|", 1)[0]
        return f"[[{stem}|{display}]]"
    return canonical


def canonicalize_wikilinks(text: str, link_index: dict[str, str], unlink_unresolved: bool = False) -> str:
    def repl(match: re.Match[str]) -> str:
        return canonicalize_wiki_item(f"[[{match.group(1)}]]", link_index, unlink_unresolved=unlink_unresolved)

    return re.sub(r"\[\[([^\]]+)\]\]", repl, text)


def file_title(path: Path, text: str) -> str:
    match = re.search(r"(?m)^#\s+(.+)$", text)
    return match.group(1).strip() if match else path.stem


def split_frontmatter(text: str) -> tuple[dict[str, Any], str, str | None]:
    leading_title = None
    title_match = re.match(r"^(# .+?)\n\n---\n", text, flags=re.S)
    if title_match:
        leading_title = title_match.group(1)
        text = text[len(leading_title):].lstrip()
    if text.startswith("---\n"):
        end = text.find("\n---", 4)
        if end != -1:
            raw = text[4:end].strip()
            body = text[end + len("\n---"):].lstrip("\n")
            meta = parse_simple_yaml(raw)
            if leading_title and not body.startswith("# "):
                body = leading_title + "\n\n" + body
            return meta, body, leading_title
    return {}, text, leading_title


def parse_simple_yaml(raw: str) -> dict[str, Any]:
    meta: dict[str, Any] = {}
    current = None
    for line in raw.splitlines():
        if not line.strip():
            continue
        if re.match(r"^[A-Za-z0-9_\-]+:\s*", line):
            key, value = line.split(":", 1)
            key = key.strip()
            value = value.strip()
            current = key
            if value == "":
                meta[key] = []
            elif value.lower() in {"true", "false"}:
                meta[key] = value.lower() == "true"
            else:
                meta[key] = value.strip('"')
        elif line.lstrip().startswith("- ") and current:
            if not isinstance(meta.get(current), list):
                meta[current] = []
            meta[current].append(line.strip()[2:].strip('"'))
    return meta


def yaml_value(value: Any) -> list[str]:
    if isinstance(value, bool):
        return ["true" if value else "false"]
    if isinstance(value, int):
        return [str(value)]
    if isinstance(value, list):
        if not value:
            return ["[]"]
        return [""] + [f"  - \"{str(item)}\"" for item in value]
    return [f"\"{str(value)}\""]


def render_yaml(meta: dict[str, Any]) -> str:
    preferred = [
        "stage", "status", "theme_cluster", "source_count", "promotion_score", "fact_check_required",
        "tags", "related_sources", "related_topics", "related_assets", "related_outputs", "moc", "obsidian_links_updated",
    ]
    keys = [k for k in preferred if k in meta] + sorted(k for k in meta if k not in preferred)
    lines = ["---"]
    for key in keys:
        vals = yaml_value(meta[key])
        if len(vals) == 1:
            lines.append(f"{key}: {vals[0]}")
        else:
            lines.append(f"{key}:{vals[0]}")
            lines.extend(vals[1:])
    lines.append("---")
    return "\n".join(lines) + "\n\n"


def infer_cluster(title: str, rel: str, cfg: dict[str, Any]) -> dict[str, Any] | None:
    blob = title + " " + rel
    for cluster in cfg.get("_obsidian_clusters", []):
        if any(k.lower() in blob.lower() for k in cluster["keywords"]):
            return cluster
    return None


def stage_from_path(path: Path, cfg: dict[str, Any]) -> str:
    parts = set(path.parts)
    if cfg["mapping"].get("source_refinements") in parts:
        return "来源精炼"
    if cfg["mapping"]["topic_pages"] in parts:
        return "主题页"
    if cfg["mapping"]["reusable_assets"] in parts:
        if "框架图谱" in parts or "frameworks" in parts:
            return "框架图谱"
        return "方法论"
    if cfg["mapping"]["outputs"] in parts:
        if "费曼解释" in parts or "feynman-explanations" in parts:
            return "费曼解释"
        if "文章草稿" in parts or "article-drafts" in parts:
            return "文章草稿"
        if "方案素材" in parts or "solution-materials" in parts:
            return "方案素材"
        return "输出"
    return "知识文件"


def compact_tags(tags: list[str]) -> list[str]:
    out = []
    for tag in tags:
        tag = str(tag).strip(" #")
        if tag and tag not in out:
            out.append(tag)
    return out[:6]


def collect_files(cfg: dict[str, Any], include_sources: bool = True) -> list[Path]:
    roots = []
    if include_sources:
        roots.append(kb_dir(cfg, "source_refinements"))
    roots += [kb_dir(cfg, "topic_pages"), kb_dir(cfg, "reusable_assets"), kb_dir(cfg, "outputs")]
    files = []
    for root in roots:
        if root.exists():
            files.extend(sorted(root.rglob("*.md")))
    return files


def relation_files(cfg: dict[str, Any]) -> list[Path]:
    roots = [kb_dir(cfg, "topic_pages"), kb_dir(cfg, "reusable_assets"), kb_dir(cfg, "outputs")]
    files = []
    for root in roots:
        if root.exists():
            files.extend(sorted(root.rglob("*.md")))
    return [p for p in files if not is_moc(p)]


def is_moc(path: Path) -> bool:
    return path.name.endswith("-MOC.md")


def source_titles_for_cluster(cfg: dict[str, Any], cluster: dict[str, Any]) -> list[str]:
    if not cluster:
        return []
    index = kb_dir(cfg, "system") / "processed-index.jsonl"
    if not index.exists():
        return []
    titles = []
    for line in index.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        try:
            row = json.loads(line)
        except json.JSONDecodeError:
            continue
        blob = " ".join([row.get("title", ""), " ".join(row.get("topics", []))])
        if any(k.lower() in blob.lower() for k in cluster["keywords"]):
            titles.append(row.get("title") or Path(row.get("source_path", "")).stem)
    return titles[:8]


def as_list(value: Any) -> list[str]:
    if value is None or value == "":
        return []
    empty_markers = {"[]", "null", "none", "暂无"}
    if isinstance(value, list):
        return [str(v) for v in value if str(v).strip() and str(v).strip().lower() not in empty_markers]
    value = str(value).strip()
    return [] if value.lower() in empty_markers else [value]


def clean_wiki_title(value: str) -> str:
    value = str(value).strip().strip('"')
    if value.startswith("[[") and value.endswith("]]"):
        value = value[2:-2]
    return value


def cluster_name_from_meta(meta: dict[str, Any], title: str, rel: str, cfg: dict[str, Any]) -> str | None:
    explicit = meta.get("theme_cluster")
    if explicit and explicit != "unclassified":
        return str(explicit)
    source_theme = meta.get("source_theme")
    if source_theme:
        return clean_wiki_title(str(source_theme))
    inferred = infer_cluster(title, rel, cfg)
    return inferred.get("name") if inferred else None


def source_links_for_cluster_name(cfg: dict[str, Any], cluster_name: str | None, link_index: dict[str, str]) -> list[str]:
    if not cluster_name:
        return []
    aliases = {
        "AI知识管理": ["AI知识管理", "Obsidian", "知识库治理", "LLM Wiki", "Graphify"],
        "Agent工作流": ["Agent工作流", "Skill设计", "自动化系统", "OpenClaw", "Agent Skill", "内容生产"],
        "咨询方法论": ["咨询方法论", "结构化思维", "问题解决", "表达写作", "AI写作"],
        "AI组织转型": ["AI组织转型", "AI Native", "数字化转型", "组织转型"],
        "ToB客户经营": ["ToB客户经营", "ToB增长", "CRM", "客户经营", "经营分析", "销售方法"],
    }
    keys = aliases.get(cluster_name, [cluster_name])
    index = kb_dir(cfg, "system") / "processed-index.jsonl"
    if not index.exists():
        return []
    links = []
    for line in index.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        try:
            row = json.loads(line)
        except json.JSONDecodeError:
            continue
        blob = " ".join([row.get("title", ""), " ".join(row.get("topics", []))])
        if any(k.lower() in blob.lower() for k in keys):
            title = row.get("title") or Path(row.get("source_path", "")).stem
            output_file = row.get("output_file")
            if output_file:
                p = Path(output_file)
                item = wiki_for_path(p, title)
            else:
                item = link_index.get(link_key(title))
            if item:
                links.append(item)
    seen = []
    for item in links:
        if item not in seen:
            seen.append(item)
    return seen[:8]


def build_relations(path: Path, cfg: dict[str, Any], all_titles: dict[Path, str], link_index: dict[str, str], unlink_unresolved: bool = False) -> dict[str, list[str]]:
    text = path.read_text(encoding="utf-8", errors="ignore")
    meta, body, _leading = split_frontmatter(text)
    title = file_title(path, body)
    rel = str(path.relative_to(Path(cfg["ai_knowledge_base"])))
    cluster_name = cluster_name_from_meta(meta, title, rel, cfg)
    relations = {
        "sources": as_list(meta.get("related_sources")),
        "topics": as_list(meta.get("related_topics")),
        "assets": as_list(meta.get("related_assets")),
        "outputs": as_list(meta.get("related_outputs")),
    }
    if not relations["topics"] and meta.get("source_theme"):
        relations["topics"].append(canonicalize_wiki_item(str(meta["source_theme"]), link_index, unlink_unresolved=unlink_unresolved))
    for key in relations:
        relations[key] = [canonicalize_wiki_item(item, link_index, unlink_unresolved=unlink_unresolved) for item in relations[key]]
    for src in source_links_for_cluster_name(cfg, cluster_name, link_index):
        if src not in relations["sources"]:
            relations["sources"].append(src)
    for p, t in all_titles.items():
        if p == path or is_moc(p):
            continue
        other_text = p.read_text(encoding="utf-8", errors="ignore")
        other_meta, other_body, _ = split_frontmatter(other_text)
        other_rel = str(p.relative_to(Path(cfg["ai_knowledge_base"])))
        other_cluster = cluster_name_from_meta(other_meta, file_title(p, other_body), other_rel, cfg)
        if not cluster_name or other_cluster != cluster_name:
            continue
        stage = stage_from_path(p, cfg)
        if stage == "主题页":
            relations["topics"].append(wiki_for_path(p, t))
        elif stage in {"方法论", "框架图谱"}:
            relations["assets"].append(wiki_for_path(p, t))
        else:
            relations["outputs"].append(wiki_for_path(p, t))
    for key in relations:
        seen = []
        for item in relations[key]:
            if item and item not in seen:
                seen.append(item)
        relations[key] = seen[:8]
    return relations


def relation_section(relations: dict[str, list[str]]) -> str:
    labels = [
        ("上游来源", relations["sources"]),
        ("相关主题页", relations["topics"]),
        ("可复用资产", relations["assets"]),
        ("相关输出", relations["outputs"]),
    ]
    parts = ["## 关联知识"]
    for name, items in labels:
        if not items:
            continue
        parts += ["", f"### {name}"]
        parts += [f"- {i}" for i in items]
    if len(parts) == 1:
        parts += ["", "本文件尚未建立明确关联。"]
    return "\n".join(parts).rstrip() + "\n"


def replace_relation_section(body: str, section: str) -> str:
    pattern = r"(?ms)^## 关联知识\n.*?(?=^##\s+|\Z)"
    if re.search(pattern, body):
        return re.sub(pattern, section + "\n", body).rstrip() + "\n"
    return body.rstrip() + "\n\n" + section


def update_file(path: Path, cfg: dict[str, Any], all_titles: dict[Path, str], link_index: dict[str, str], unlink_unresolved: bool = False) -> bool:
    old = path.read_text(encoding="utf-8", errors="ignore")
    meta, body, _leading = split_frontmatter(old)
    title = file_title(path, body)
    rel = str(path.relative_to(Path(cfg["ai_knowledge_base"])))
    cluster = infer_cluster(title, rel, cfg)
    stage = stage_from_path(path, cfg)
    relations = build_relations(path, cfg, all_titles, link_index, unlink_unresolved=unlink_unresolved)
    if stage == "来源精炼":
        relations["sources"] = []
    cluster_name = cluster_name_from_meta(meta, title, rel, cfg)
    cluster_tags = cluster.get("tags", []) if cluster else []
    tags = compact_tags(as_list(meta.get("tags")) + cluster_tags + [STAGE_TAGS.get(stage, stage)] + (["待核查"] if meta.get("fact_check_required") is True else []))
    meta.update({
        "stage": meta.get("stage", stage),
        "theme_cluster": cluster_name or meta.get("theme_cluster", "unclassified"),
        "tags": tags,
        "related_sources": relations["sources"][:6],
        "related_topics": relations["topics"][:6],
        "related_assets": relations["assets"][:6],
        "related_outputs": relations["outputs"][:6],
        "obsidian_links_updated": date.today().isoformat(),
    })
    if cluster and cluster.get("moc"):
        meta["moc"] = wiki(cluster["moc"])
    elif cluster_name and not meta.get("moc"):
        meta["moc"] = wiki(f"{cluster_name}-MOC")
    body = canonicalize_wikilinks(body, link_index, unlink_unresolved=unlink_unresolved)
    body = replace_relation_section(body, relation_section(relations))
    new = render_yaml(meta) + body.lstrip()
    if new != old:
        path.write_text(new, encoding="utf-8")
        return True
    return False


def render_moc(cfg: dict[str, Any], cluster: dict[str, Any], all_titles: dict[Path, str]) -> str:
    groups = {"主题页": [], "可复用资产": [], "输出": []}
    for p, title in all_titles.items():
        rel = str(p.relative_to(Path(cfg["ai_knowledge_base"])))
        text = p.read_text(encoding="utf-8", errors="ignore")
        meta, body, _ = split_frontmatter(text)
        cluster_name = cluster_name_from_meta(meta, file_title(p, body), rel, cfg)
        inferred = infer_cluster(title, rel, cfg)
        inferred_name = inferred.get("name") if inferred else None
        if cluster_name != cluster["name"] and inferred_name != cluster["name"]:
            continue
        stage = stage_from_path(p, cfg)
        if stage == "主题页":
            groups["主题页"].append(wiki_for_path(p, title))
        elif stage in {"方法论", "框架图谱"}:
            groups["可复用资产"].append(wiki_for_path(p, title))
        else:
            groups["输出"].append(wiki_for_path(p, title))
    meta = {
        "stage": "MOC",
        "status": "active",
        "theme_cluster": cluster["name"],
        "tags": compact_tags(cluster["tags"] + ["MOC"]),
        "obsidian_links_updated": date.today().isoformat(),
    }
    body = [f"# {cluster['moc']}", "", "## 主题页"]
    body += [f"- {x}" for x in groups["主题页"]] or ["- 暂无"]
    body += ["", "## 可复用资产"]
    body += [f"- {x}" for x in groups["可复用资产"]] or ["- 暂无"]
    body += ["", "## 输出"]
    body += [f"- {x}" for x in groups["输出"]] or ["- 暂无"]
    body += [
        "",
        "## Dataview",
        "",
        "```dataview",
        f"LIST FROM \"{vault_rel(topic_pages_content_dir(cfg), cfg)}\" OR \"{cfg['mapping']['reusable_assets']}\" OR \"{cfg['mapping']['outputs']}\"",
        f"WHERE theme_cluster = \"{cluster['name']}\"",
        "SORT file.mtime DESC",
        "```",
        "",
    ]
    return render_yaml(meta) + "\n".join(body)


def link(cfg: dict[str, Any], apply: bool, unlink_unresolved: bool = False) -> dict[str, Any]:
    files = collect_files(cfg, include_sources=True)
    link_index = build_link_index(files)
    all_titles = {p: file_title(p, p.read_text(encoding="utf-8", errors="ignore")) for p in relation_files(cfg)}
    changed = []
    if apply:
        for p in files:
            if is_moc(p):
                continue
            if update_file(p, cfg, all_titles, link_index, unlink_unresolved=unlink_unresolved):
                changed.append(str(p))
        moc_root = topic_pages_moc_dir(cfg)
        moc_root.mkdir(parents=True, exist_ok=True)
        for cluster in cfg.get("_obsidian_clusters", []):
            p = moc_root / f"{cluster['moc']}.md"
            content = render_moc(cfg, cluster, all_titles)
            if not p.exists() or p.read_text(encoding="utf-8", errors="ignore") != content:
                p.write_text(content, encoding="utf-8")
                changed.append(str(p))
    return {"files": len(files), "changed": changed, "moc_pages": [str(topic_pages_moc_dir(cfg) / f"{c['moc']}.md") for c in cfg.get("_obsidian_clusters", [])]}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", required=True, type=Path)
    parser.add_argument("--apply", action="store_true")
    parser.add_argument("--unlink-unresolved", action="store_true", help="Convert wikilinks that do not resolve to existing files into plain text.")
    args = parser.parse_args()
    cfg = load_config(args.config)
    print(json.dumps(link(cfg, args.apply, unlink_unresolved=args.unlink_unresolved), ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
