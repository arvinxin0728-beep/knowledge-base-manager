"""Portable configuration loading and validation."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from kbm.domain.researcher import researcher_from_config


DEFAULT_MAPPING = {"system": "00-system", "source_refinements": "10-source-refinements", "topic_pages": "20-topic-pages", "reusable_assets": "30-reusable-assets", "outputs": "40-outputs"}
DEFAULT_SOURCE_SUBDIRS = {"ebooks": "ebooks", "articles": "articles", "public_accounts": "public-accounts"}
DEFAULT_TOPIC_PAGE_SUBDIRS = {"pages": "pages", "moc": "moc"}
DEFAULT_OUTPUT_SUBDIRS = {"feynman": "feynman-explanations", "article_drafts": "article-drafts", "solution_materials": "solution-materials", "reviews": "reviews"}
DEFAULT_REUSABLE_ASSET_SUBDIRS = {"methods": "methods", "cases": "cases", "expressions": "expressions", "frameworks": "frameworks"}


def deep_defaults(value: dict[str, Any], defaults: dict[str, Any]) -> dict[str, Any]:
    out = dict(value)
    for key, default in defaults.items():
        if key not in out:
            out[key] = default
        elif isinstance(out[key], dict) and isinstance(default, dict):
            out[key] = deep_defaults(out[key], default)
    return out


def config_defaults() -> dict[str, Any]:
    return {
        "version": 1,
        "language": "zh-CN",
        "source_libraries": {},
        "mapping": dict(DEFAULT_MAPPING),
        "source_refinement_subdirs": dict(DEFAULT_SOURCE_SUBDIRS),
        "topic_page_subdirs": dict(DEFAULT_TOPIC_PAGE_SUBDIRS),
        "reusable_asset_subdirs": dict(DEFAULT_REUSABLE_ASSET_SUBDIRS),
        "output_subdirs": dict(DEFAULT_OUTPUT_SUBDIRS),
        "promotion_rules": {"min_sources_for_topic": 3, "allow_user_requested_topic": True, "fact_check_before_public_output": True},
        "integrations": {"obsidian": {"enabled": False}},
        "pipeline": {"chunk_size": 5000, "default_batch_size": 10, "max_attempts": 3, "lease_minutes": 120, "runtime_storage": "legacy", "artifact_retention_days": 7},
        "quality": {
            "template_patterns": [
                r"任务定义\s*->\s*工具/Skill 封装\s*->\s*权限与数据接入\s*->\s*自动执行\s*->\s*复盘迭代",
                r"材料倾向于把 AI 能力包装为可执行流程或可复用 Skill",
                r"解决如何把一个具体任务拆成 Agent、工具、权限、输入输出和执行链路的问题",
                r"材料将问题拆解、结构表达或模型复用作为核心",
                r"可作为 Agent/Skill 场景库案例",
                r"文章的结构线索集中在",
            ],
            "boilerplate_topics": ["Agent工作流", "Skill设计", "自动化系统", "内容生产", "表达写作", "AI写作"],
            "batch_model_repeat_threshold": 0.3,
        },
    }


def load_config(path: Path) -> dict[str, Any]:
    raw = json.loads(path.read_text(encoding="utf-8"))
    cfg = deep_defaults(raw, config_defaults())
    if "researcher" not in raw:
        cfg["researcher"] = researcher_from_config(cfg).to_config()
    return cfg


def validate_config(cfg: dict[str, Any]) -> list[dict[str, str]]:
    errors: list[dict[str, str]] = []
    if cfg.get("version") != 1:
        errors.append({"field": "version", "error": "unsupported_version"})
    base_raw = cfg.get("ai_knowledge_base")
    if not isinstance(base_raw, str) or not base_raw.strip():
        errors.append({"field": "ai_knowledge_base", "error": "required_absolute_path"})
    elif not Path(base_raw).expanduser().is_absolute():
        errors.append({"field": "ai_knowledge_base", "error": "must_be_absolute"})
    for key in DEFAULT_MAPPING:
        value = cfg.get("mapping", {}).get(key)
        if not isinstance(value, str) or not value.strip():
            errors.append({"field": f"mapping.{key}", "error": "required_relative_path"})
        elif Path(value).is_absolute() or ".." in Path(value).parts:
            errors.append({"field": f"mapping.{key}", "error": "must_stay_inside_ai_knowledge_base"})
    for key, value in cfg.get("source_libraries", {}).items():
        if value and not Path(value).expanduser().is_absolute():
            errors.append({"field": f"source_libraries.{key}", "error": "must_be_absolute"})
    pipeline = cfg.get("pipeline", {})
    if pipeline.get("runtime_storage") not in {"local", "legacy"}:
        errors.append({"field": "pipeline.runtime_storage", "error": "must_be_local_or_legacy"})
    retention = pipeline.get("artifact_retention_days")
    if not isinstance(retention, int) or retention < 0:
        errors.append({"field": "pipeline.artifact_retention_days", "error": "must_be_non_negative_integer"})
    namespace = pipeline.get("runtime_namespace")
    if namespace is not None and (not isinstance(namespace, str) or not namespace.strip()):
        errors.append({"field": "pipeline.runtime_namespace", "error": "must_be_non_empty_string"})
    raw_researcher = cfg.get("researcher")
    if raw_researcher is not None and not isinstance(raw_researcher, dict):
        errors.append({"field": "researcher", "error": "must_be_object"})
    else:
        errors.extend(researcher_from_config(cfg).validation_errors())
        if isinstance(raw_researcher, dict) and not isinstance(raw_researcher.get("shared_methods", []), list):
            errors.append({"field": "researcher.shared_methods", "error": "must_be_array"})
    return errors


def require_valid_config(cfg: dict[str, Any]) -> None:
    errors = validate_config(cfg)
    if errors:
        raise SystemExit(json.dumps({"valid": False, "errors": errors}, ensure_ascii=False, indent=2))


def write_config(path: Path, cfg: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(cfg, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
