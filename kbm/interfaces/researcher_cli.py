"""Argument parser for the researcher control plane."""

from __future__ import annotations

import argparse
from pathlib import Path
from typing import Callable

from kbm.domain.research_design import (
    LEGACY_PROFILES, OUTPUT_OPTIONS, PROCESS_OPTIONS, RESEARCH_PRESETS, SOURCE_OPTIONS,
)
from kbm.domain.researcher_types import RESEARCHER_TYPES


def _design_arguments(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--researcher-id", required=True)
    parser.add_argument("--name", required=True)
    parser.add_argument("--theme", "--domain", dest="theme", required=True)
    group = parser.add_mutually_exclusive_group()
    group.add_argument("--preset", choices=tuple(sorted(RESEARCH_PRESETS)))
    group.add_argument("--type", dest="researcher_type", choices=tuple(sorted(RESEARCHER_TYPES)))
    parser.add_argument("--profile", choices=tuple(sorted(LEGACY_PROFILES)), default="knowledge")
    parser.add_argument("--source", action="append", choices=tuple(sorted(SOURCE_OPTIONS)), default=[])
    parser.add_argument("--process", action="append", choices=tuple(sorted(PROCESS_OPTIONS)), default=[])
    parser.add_argument("--output", action="append", choices=tuple(sorted(OUTPUT_OPTIONS)), default=[])
    for name in ("question", "audience", "include-boundary", "exclude-boundary", "enable", "disable"):
        parser.add_argument(f"--{name}", action="append", default=[])
    parser.add_argument("--time-horizon", default="continuous")


def build_parser(handlers: dict[str, Callable]) -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Manage isolated researcher instances.")
    sub = parser.add_subparsers(dest="command", required=True)
    item = sub.add_parser("types")
    item.set_defaults(func=handlers["types"])
    item = sub.add_parser("presets")
    item.set_defaults(func=handlers["presets"])
    item = sub.add_parser("capabilities")
    item.set_defaults(func=handlers["capabilities"])
    item = sub.add_parser("registry-init")
    item.add_argument("--registry", required=True, type=Path)
    item.add_argument("--shared-methods", type=Path)
    item.add_argument("--apply", action="store_true")
    item.set_defaults(func=handlers["registry-init"])
    item = sub.add_parser("register")
    item.add_argument("--registry", required=True, type=Path)
    item.add_argument("--config", required=True, type=Path)
    item.add_argument("--create-registry", action="store_true")
    item.add_argument("--apply", action="store_true")
    item.set_defaults(func=handlers["register"])
    item = sub.add_parser("list")
    item.add_argument("--registry", required=True, type=Path)
    item.set_defaults(func=handlers["list"])
    item = sub.add_parser("doctor")
    item.add_argument("--registry", required=True, type=Path)
    item.add_argument("--researcher-id")
    item.set_defaults(func=handlers["doctor"])
    item = sub.add_parser("show")
    item.add_argument("--registry", required=True, type=Path)
    item.add_argument("--researcher-id")
    item.set_defaults(func=handlers["show"])
    item = sub.add_parser("select")
    item.add_argument("--registry", required=True, type=Path)
    item.add_argument("--researcher-id", required=True)
    item.add_argument("--apply", action="store_true")
    item.set_defaults(func=handlers["select"])
    item = sub.add_parser("plan-init")
    item.add_argument("--workspace", required=True, type=Path)
    _design_arguments(item)
    item.set_defaults(func=handlers["plan-init"])
    item = sub.add_parser("init")
    item.add_argument("--registry", required=True, type=Path)
    item.add_argument("--workspace", required=True, type=Path)
    _design_arguments(item)
    item.add_argument("--system-dir", default="00-系统")
    item.add_argument("--create-registry", action="store_true")
    item.add_argument("--apply", action="store_true")
    item.set_defaults(func=handlers["init"])
    return parser
