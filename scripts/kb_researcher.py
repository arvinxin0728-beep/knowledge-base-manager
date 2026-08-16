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
    plan_from_legacy_profile, resolve_researcher_plan,
)
from kbm.application.researcher_initializer import finalize_researcher_workspace


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
    emit({"ok": True, "types": [{"id": key, **value} for key, value in sorted(RESEARCHER_TYPES.items())]})
def cmd_capabilities(_args: argparse.Namespace) -> None:
    emit({"ok": True, "capabilities": [{"id": key, **value} for key, value in sorted(CAPABILITIES.items())]})
def resolve_args_plan(args: argparse.Namespace):
    if getattr(args, "researcher_type", None):
        return resolve_researcher_plan(args.researcher_type, enable=args.enable, disable=args.disable)
    return plan_from_legacy_profile(args.profile)
def cmd_plan_init(args: argparse.Namespace) -> None:
    plan = resolve_args_plan(args)
    emit({
        "ok": True,
        "applied": False,
        "researcher": {"id": args.researcher_id, "name": args.name, "domain": args.domain},
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
    source_root = workspace / ("01-视频输入" if layout_profile == "video" else "01-知识输入")
    video_profile_args = []
    if layout_profile == "video":
        video_profile_args = [
            "--ebooks-subdir", "视频", "--articles-subdir", "视频", "--public-accounts-subdir", "视频",
            "--topic-pages-subdir", "主题页", "--moc-subdir", "MOC",
            "--methods-subdir", "方法", "--cases-subdir", "案例", "--expressions-subdir", "表达", "--frameworks-subdir", "框架",
            "--feynman-subdir", "费曼解释", "--article-drafts-subdir", "文章草稿",
            "--solution-materials-subdir", "方案材料", "--reviews-subdir", "复盘",
        ]
    source_args = (
        ["--ebooks", str(source_root / "电子书"), "--articles", str(source_root / "文章"), "--public-accounts", str(source_root / "公众号")]
        if layout_profile == "knowledge" else []
    )
    command = [
        sys.executable, str(ROOT / "scripts" / "kb_manager.py"), "init",
        "--config", str(config), "--ai-knowledge-base", str(workspace),
        "--name", args.name, "--researcher-id", args.researcher_id,
        "--researcher-name", args.name, "--research-domain", args.domain,
        "--system-dir", args.system_dir, "--source-refinements-dir", "10-来源精炼",
        "--topic-pages-dir", "20-主题页", "--reusable-assets-dir", "30-可复用资产",
        "--outputs-dir", "40-输出",
        *source_args, *video_profile_args,
    ]
    if args.apply:
        command.append("--apply")
    result = json.loads(subprocess.check_output(command, text=True))
    if args.apply:
        finalize_researcher_workspace(config, workspace, source_root, plan, args.disable)
        registry = load_registry(args.registry, allow_missing=args.create_registry)
        updated, entry = register(registry, config)
        atomic_write_json(args.registry, updated)
    else:
        entry = {"id": args.researcher_id, "name": args.name, "workspace": str(workspace), "config": str(config), "profile": layout_profile}
    emit({"ok": True, "applied": args.apply, "researcher": entry, "plan": plan.to_dict(), "initialization": result})


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)

    p = sub.add_parser("types")
    p.set_defaults(func=cmd_types)

    p = sub.add_parser("capabilities")
    p.set_defaults(func=cmd_capabilities)

    p = sub.add_parser("registry-init")
    p.add_argument("--registry", required=True, type=Path)
    p.add_argument("--shared-methods", type=Path)
    p.add_argument("--apply", action="store_true")
    p.set_defaults(func=cmd_registry_init)

    p = sub.add_parser("register")
    p.add_argument("--registry", required=True, type=Path)
    p.add_argument("--config", required=True, type=Path)
    p.add_argument("--create-registry", action="store_true")
    p.add_argument("--apply", action="store_true")
    p.set_defaults(func=cmd_register)

    p = sub.add_parser("list")
    p.add_argument("--registry", required=True, type=Path)
    p.set_defaults(func=cmd_list)

    p = sub.add_parser("doctor")
    p.add_argument("--registry", required=True, type=Path)
    p.add_argument("--researcher-id")
    p.set_defaults(func=cmd_doctor)

    p = sub.add_parser("show")
    p.add_argument("--registry", required=True, type=Path)
    p.add_argument("--researcher-id")
    p.set_defaults(func=cmd_show)

    p = sub.add_parser("select")
    p.add_argument("--registry", required=True, type=Path)
    p.add_argument("--researcher-id", required=True)
    p.add_argument("--apply", action="store_true")
    p.set_defaults(func=cmd_select)

    p = sub.add_parser("plan-init")
    p.add_argument("--workspace", required=True, type=Path)
    p.add_argument("--researcher-id", required=True)
    p.add_argument("--name", required=True)
    p.add_argument("--domain", required=True)
    p.add_argument("--type", dest="researcher_type", choices=tuple(sorted(RESEARCHER_TYPES)))
    p.add_argument("--profile", choices=tuple(sorted(LEGACY_PROFILES)), default="knowledge")
    p.add_argument("--enable", action="append", default=[])
    p.add_argument("--disable", action="append", default=[])
    p.set_defaults(func=cmd_plan_init)

    p = sub.add_parser("init")
    p.add_argument("--registry", required=True, type=Path)
    p.add_argument("--workspace", required=True, type=Path)
    p.add_argument("--researcher-id", required=True)
    p.add_argument("--name", required=True)
    p.add_argument("--domain", required=True)
    p.add_argument("--profile", choices=("knowledge", "video"), default="knowledge")
    p.add_argument("--type", dest="researcher_type", choices=tuple(sorted(RESEARCHER_TYPES)))
    p.add_argument("--enable", action="append", default=[])
    p.add_argument("--disable", action="append", default=[])
    p.add_argument("--system-dir", default="00-系统")
    p.add_argument("--create-registry", action="store_true")
    p.add_argument("--apply", action="store_true")
    p.set_defaults(func=cmd_init)
    return parser


def main() -> None:
    args = build_parser().parse_args()
    try:
        args.func(args)
    except (ValueError, OSError, json.JSONDecodeError, subprocess.CalledProcessError) as exc:
        fail(exc)


if __name__ == "__main__":
    main()
