"""Materialize a resolved researcher plan into a workspace configuration."""

from __future__ import annotations

import json
from datetime import date
from pathlib import Path
from typing import Iterable

from kbm.application.researcher_registry import atomic_write_json
from kbm.domain.research_design import ResearchDesignPlan


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
    plan: ResearchDesignPlan,
    disabled: Iterable[str] = (),
) -> dict:
    raw = json.loads(config.read_text(encoding="utf-8"))
    if plan.layout_profile in {"video", "mixed"}:
        video_root = workspace / "01-视频输入"
        for relative in VIDEO_DIRECTORIES:
            (workspace / relative).mkdir(parents=True, exist_ok=True)
        raw["source_libraries"].update({
            "videos": str(video_root / "本地视频"), "video_links": str(video_root / "链接队列"),
            "transcripts": str(video_root / "字幕"),
        })
        raw.setdefault("source_adapters", {})["video"] = {"enabled": False, "status": "adapter_not_installed"}
        raw.setdefault("source_refinement_subdirs", {})["videos"] = "视频"
        raw["mapping"]["media_assets"] = "50-素材库"
        if plan.layout_profile == "video":
            raw["profile"] = "video"
            raw["source_refinement_subdirs"] = {"videos": "视频"}
            raw["topic_page_subdirs"] = {"pages": "主题页", "moc": "MOC"}
            raw["reusable_asset_subdirs"] = {"methods": "方法", "cases": "案例", "expressions": "表达", "frameworks": "框架"}
            raw["output_subdirs"] = {"feynman": "费曼解释", "article_drafts": "文章草稿", "solution_materials": "方案材料", "reviews": "复盘"}
    raw["research_design"] = plan.design_dict()
    if plan.legacy_type:
        raw["researcher"]["type"] = plan.legacy_type
        raw["researcher"]["type_deprecated"] = True
    else:
        raw["researcher"].pop("type", None)
        raw["researcher"].pop("type_deprecated", None)
    raw["capabilities"] = {"enabled": list(plan.capabilities), "disabled": list(disabled)}
    raw["governance"] = {"policy": plan.governance_policy}
    raw["resolved_manifest"] = {
        "schema_version": 1, "research_design_version": 2,
        "capability_catalog_version": 2, "resolved_at": date.today().isoformat(),
        "layout_profile": plan.layout_profile,
        "unavailable": list(plan.unavailable),
        "execution_plan": [
            {
                "sequence": step["sequence"], "id": step["id"],
                "status": step["status"], "entrypoint": step["entrypoint"],
            }
            for step in plan.execution_steps
        ],
    }
    if plan.legacy_type:
        raw["resolved_manifest"]["legacy_type_alias"] = plan.legacy_type
    atomic_write_json(config, raw)
    return raw
