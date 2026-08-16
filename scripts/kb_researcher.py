#!/usr/bin/env python3
"""Manage isolated knowledge-base-manager researcher instances."""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from kbm.application.researcher_registry import (
    atomic_write_json, doctor_entry, empty_registry, load_registry, register,
    registry_errors, resolve_entry, select,
)
from kbm.domain.researcher_types import (
    CAPABILITIES, LEGACY_PROFILES, RESEARCHER_TYPES,
    plan_from_legacy_profile,
)
from kbm.domain.research_design import (
    OUTPUT_OPTIONS, PROCESS_OPTIONS, RESEARCH_PRESETS, SOURCE_OPTIONS,
    plan_from_legacy_type, resolve_research_design,
)
from kbm.application.researcher_initializer import finalize_researcher_workspace
from kbm.interfaces.researcher_cli import build_parser


def emit(value: Any) -> None:
    print(json.dumps(value, ensure_ascii=False, indent=2))


def fail(exc: Exception) -> None:
    emit({"ok": False, "error": str(exc)})
    raise SystemExit(1)


def cmd_registry_init(args: argparse.Namespace) -> None:
    if args.registry.exists():
        raise ValueError("registry_already_exists")
    value = empty_registry(str(args.shared_methods.resolve()) if args.shared_methods else "")
    if args.apply:
        atomic_write_json(args.registry, value)
    emit({"ok": True, "applied": args.apply, "registry": str(args.registry), **value})


def cmd_register(args: argparse.Namespace) -> None:
    registry = load_registry(args.registry, allow_missing=args.create_registry)
    updated, entry = register(registry, args.config)
    if args.apply:
        atomic_write_json(args.registry, updated)
    emit({"ok": True, "applied": args.apply, "registry": str(args.registry), "researcher": entry})


def cmd_list(args: argparse.Namespace) -> None:
    registry = load_registry(args.registry)
    emit({"ok": True, "registry": str(args.registry), "selected_researcher": registry.get("selected_researcher"), "researchers": registry["researchers"]})


def cmd_show(args: argparse.Namespace) -> None:
    registry = load_registry(args.registry)
    emit({"ok": True, "researcher": resolve_entry(registry, args.researcher_id)})


def cmd_select(args: argparse.Namespace) -> None:
    registry = load_registry(args.registry)
    updated = select(registry, args.researcher_id)
    if args.apply:
        atomic_write_json(args.registry, updated)
    emit({"ok": True, "applied": args.apply, "selected_researcher": args.researcher_id})


def cmd_doctor(args: argparse.Namespace) -> None:
    registry = load_registry(args.registry)
    registry_issues = registry_errors(registry)
    entries = [resolve_entry(registry, args.researcher_id)] if args.researcher_id else registry["researchers"]
    results = [doctor_entry(entry) for entry in entries]
    payload = {
        "ok": not registry_issues and all(item.healthy for item in results),
        "registry": str(args.registry),
        "registry_issues": registry_issues,
        "researchers": [{"id": item.researcher_id, "healthy": item.healthy, "checks": item.checks} for item in results],
    }
    emit(payload)
    if not payload["ok"]:
        raise SystemExit(1)


def cmd_types(_args: argparse.Namespace) -> None:
    emit({"ok": True, "deprecated": True, "use": "presets", "types": [{"id": key, **value} for key, value in sorted(RESEARCHER_TYPES.items())]})


def cmd_presets(_args: argparse.Namespace) -> None:
    emit({
        "ok": True,
        "presets": [{"id": key, **value} for key, value in sorted(RESEARCH_PRESETS.items())],
        "dimensions": {
            "sources": sorted(SOURCE_OPTIONS), "process": sorted(PROCESS_OPTIONS),
            "outputs": sorted(OUTPUT_OPTIONS),
        },
    })


def cmd_capabilities(_args: argparse.Namespace) -> None:
    emit({"ok": True, "capabilities": [{"id": key, **value} for key, value in sorted(CAPABILITIES.items())]})


def resolve_args_plan(args: argparse.Namespace):
    design = {
        "theme": args.theme, "questions": args.question,
        "boundaries_in": args.include_boundary, "boundaries_out": args.exclude_boundary,
        "audience": args.audience, "time_horizon": args.time_horizon,
        "sources": args.source, "process": args.process, "outputs": args.output,
        "enable": args.enable, "disable": args.disable,
    }
    if getattr(args, "preset", None):
        return resolve_research_design(preset=args.preset, **design)
    if getattr(args, "researcher_type", None):
        return plan_from_legacy_type(args.researcher_type, **design)
    if any((args.source, args.process, args.output, args.question, args.audience, args.include_boundary, args.exclude_boundary)):
        return resolve_research_design(**design)
    return plan_from_legacy_profile(args.profile, theme=args.theme, enable=args.enable, disable=args.disable)


def cmd_plan_init(args: argparse.Namespace) -> None:
    plan = resolve_args_plan(args)
    emit({
        "ok": True,
        "applied": False,
        "researcher": {"id": args.researcher_id, "name": args.name, "theme": args.theme},
        "workspace": str(args.workspace.expanduser().resolve()),
        "plan": plan.to_dict(),
    })


def cmd_init(args: argparse.Namespace) -> None:
    plan = resolve_args_plan(args)
    layout_profile = plan.layout_profile
    workspace = args.workspace.expanduser().resolve()
    config = workspace / args.system_dir / "kb-config.json"
    if config.exists():
        raise ValueError("researcher_config_already_exists")
    source_root = workspace / "01-知识输入"
    video_profile_args = []
    if layout_profile == "video":
        video_profile_args = [
            "--ebooks-subdir", "视频", "--articles-subdir", "视频", "--public-accounts-subdir", "视频",
            "--topic-pages-subdir", "主题页", "--moc-subdir", "MOC",
            "--methods-subdir", "方法", "--cases-subdir", "案例", "--expressions-subdir", "表达", "--frameworks-subdir", "框架",
            "--feynman-subdir", "费曼解释", "--article-drafts-subdir", "文章草稿",
            "--solution-materials-subdir", "方案材料", "--reviews-subdir", "复盘",
        ]
    source_args = []
    if layout_profile in {"knowledge", "mixed"}:
        if "ebook" in plan.sources:
            source_args.extend(("--ebooks", str(source_root / "电子书")))
        if "article" in plan.sources:
            source_args.extend(("--articles", str(source_root / "文章")))
        if "public-account" in plan.sources:
            source_args.extend(("--public-accounts", str(source_root / "公众号")))
    command = [
        sys.executable, str(ROOT / "scripts" / "kb_manager.py"), "init",
        "--config", str(config), "--ai-knowledge-base", str(workspace),
        "--name", args.name, "--researcher-id", args.researcher_id,
        "--researcher-name", args.name, "--research-domain", args.theme,
        "--system-dir", args.system_dir, "--source-refinements-dir", "10-来源精炼",
        "--topic-pages-dir", "20-主题页", "--reusable-assets-dir", "30-可复用资产",
        "--outputs-dir", "40-输出",
        *source_args, *video_profile_args,
    ]
    if args.apply:
        command.append("--apply")
    result = json.loads(subprocess.check_output(command, text=True))
    if args.apply:
        finalize_researcher_workspace(config, workspace, plan, args.disable)
        registry = load_registry(args.registry, allow_missing=args.create_registry)
        updated, entry = register(registry, config)
        atomic_write_json(args.registry, updated)
    else:
        entry = {"id": args.researcher_id, "name": args.name, "workspace": str(workspace), "config": str(config), "profile": layout_profile}
    emit({"ok": True, "applied": args.apply, "researcher": entry, "plan": plan.to_dict(), "initialization": result})


def main() -> None:
    handlers = {
        "types": cmd_types, "presets": cmd_presets, "capabilities": cmd_capabilities,
        "registry-init": cmd_registry_init, "register": cmd_register, "list": cmd_list,
        "doctor": cmd_doctor, "show": cmd_show, "select": cmd_select,
        "plan-init": cmd_plan_init, "init": cmd_init,
    }
    args = build_parser(handlers).parse_args()
    try:
        args.func(args)
    except (ValueError, OSError, json.JSONDecodeError, subprocess.CalledProcessError) as exc:
        fail(exc)


if __name__ == "__main__":
    main()
