"""Materialize a resolved researcher plan into a workspace configuration."""

from __future__ import annotations

import json
from datetime import date
from pathlib import Path
from typing import Iterable

from kbm.application.researcher_registry import atomic_write_json
from kbm.domain.researcher_types import ResearcherPlan


VIDEO_DIRECTORIES = (
    "01-视频输入/本地视频", "01-视频输入/链接队列", "01-视频输入/字幕",
    "10-来源精炼/视频", "20-主题页/主题页", "20-主题页/MOC",
    "30-可复用资产/方法", "30-可复用资产/案例", "30-可复用资产/表达", "30-可复用资产/框架",
    "40-输出/费曼解释", "40-输出/文章草稿", "40-输出/方案材料", "40-输出/复盘",
    "50-素材库/关键帧", "50-素材库/转录文本",
)


def finalize_researcher_workspace(
    config: Path,
    workspace: Path,
    source_root: Path,
    plan: ResearcherPlan,
    disabled: Iterable[str] = (),
) -> dict:
    raw = json.loads(config.read_text(encoding="utf-8"))
    if plan.layout_profile == "video":
        for relative in VIDEO_DIRECTORIES:
            (workspace / relative).mkdir(parents=True, exist_ok=True)
        raw.update({
            "profile": "video",
            "source_libraries": {
                "videos": str(source_root / "本地视频"),
                "video_links": str(source_root / "链接队列"),
                "transcripts": str(source_root / "字幕"),
            },
            "source_adapters": {"video": {"enabled": False, "status": "adapter_not_installed"}},
            "source_refinement_subdirs": {"videos": "视频"},
            "topic_page_subdirs": {"pages": "主题页", "moc": "MOC"},
            "reusable_asset_subdirs": {"methods": "方法", "cases": "案例", "expressions": "表达", "frameworks": "框架"},
            "output_subdirs": {"feynman": "费曼解释", "article_drafts": "文章草稿", "solution_materials": "方案材料", "reviews": "复盘"},
        })
        raw["mapping"]["media_assets"] = "50-素材库"
    raw["researcher"]["type"] = plan.researcher_type
    raw["capabilities"] = {"enabled": list(plan.capabilities), "disabled": list(disabled)}
    raw["governance"] = {"policy": plan.governance_policy}
    raw["resolved_manifest"] = {
        "schema_version": 1, "researcher_type_version": 1,
        "capability_catalog_version": 2, "resolved_at": date.today().isoformat(),
        "unavailable": list(plan.unavailable),
        "execution_plan": [
            {
                "sequence": step["sequence"], "id": step["id"],
                "status": step["status"], "entrypoint": step["entrypoint"],
            }
            for step in plan.execution_steps
        ],
    }
    atomic_write_json(config, raw)
    return raw
