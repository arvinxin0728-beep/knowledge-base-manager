#!/usr/bin/env python3
"""Enforce the architecture ratchet while the legacy monolith is decomposed."""

from __future__ import annotations

import argparse
import ast
import json
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
CONTRACT = ROOT / "architecture-contract.json"


def source_metrics(path: Path) -> dict[str, int]:
    text = path.read_text(encoding="utf-8")
    result = {"lines": len(text.splitlines())}
    if path.suffix == ".py":
        tree = ast.parse(text, filename=str(path))
        result["symbols"] = sum(
            isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef))
            for node in ast.walk(tree)
        )
    return result


def cli_commands(path: Path) -> list[str]:
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    commands: list[str] = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call) or not isinstance(node.func, ast.Attribute):
            continue
        if node.func.attr != "add_parser" or not node.args:
            continue
        first = node.args[0]
        if isinstance(first, ast.Constant) and isinstance(first.value, str):
            commands.append(first.value)
    return sorted(set(commands))


def script_dependencies(path: Path, known: set[str]) -> list[str]:
    text = path.read_text(encoding="utf-8")
    return sorted(name for name in known if name != path.name and name.removesuffix(".py") in text)


def imported_modules(path: Path) -> list[str]:
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    modules: list[str] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            modules.extend(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            modules.append(node.module)
    return sorted(set(modules))


def check() -> dict[str, Any]:
    contract = json.loads(CONTRACT.read_text(encoding="utf-8"))
    blockers: list[dict[str, Any]] = []
    warnings: list[dict[str, Any]] = []
    metrics: dict[str, Any] = {}

    for relative, budget in contract["ratchet_budgets"].items():
        path = ROOT / relative
        if not path.is_file():
            blockers.append({"check": "required_file", "file": relative, "error": "missing"})
            continue
        measured = source_metrics(path)
        metrics[relative] = measured | {"target_lines": budget["target_lines"]}
        if measured["lines"] > budget["max_lines"]:
            blockers.append({"check": "line_ratchet", "file": relative, "actual": measured["lines"], "max": budget["max_lines"]})
        if "max_symbols" in budget and measured.get("symbols", 0) > budget["max_symbols"]:
            blockers.append({"check": "symbol_ratchet", "file": relative, "actual": measured["symbols"], "max": budget["max_symbols"]})
        if measured["lines"] > budget["target_lines"]:
            warnings.append({"check": "target_debt", "file": relative, "actual": measured["lines"], "target": budget["target_lines"]})

    for relative, expected in contract["legacy_cli_contracts"].items():
        actual = cli_commands(ROOT / relative)
        if sorted(expected) != actual:
            blockers.append({
                "check": "legacy_cli_contract",
                "file": relative,
                "missing": sorted(set(expected) - set(actual)),
                "unexpected": sorted(set(actual) - set(expected)),
            })

    known = set(contract["allowed_script_dependencies"])
    for filename, allowed in contract["allowed_script_dependencies"].items():
        actual = script_dependencies(ROOT / "scripts" / filename, known)
        unexpected = sorted(set(actual) - set(allowed))
        if unexpected:
            blockers.append({"check": "script_dependency", "file": filename, "unexpected": unexpected})

    for relative, forbidden_prefixes in contract.get("module_dependency_rules", {}).items():
        for path in sorted((ROOT / relative).rglob("*.py")):
            for imported in imported_modules(path):
                if any(imported == prefix or imported.startswith(prefix + ".") for prefix in forbidden_prefixes):
                    blockers.append({"check": "module_dependency_direction", "file": str(path.relative_to(ROOT)), "unexpected": imported})

    return {
        "passed": not blockers,
        "architecture_style": contract["architecture_style"],
        "metrics": metrics,
        "blockers": blockers,
        "warnings": warnings,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Check architecture budgets, CLI contracts, and script dependencies")
    parser.add_argument("--strict", action="store_true")
    args = parser.parse_args()
    result = check()
    print(json.dumps(result, ensure_ascii=False, indent=2))
    if args.strict and not result["passed"]:
        raise SystemExit(2)


if __name__ == "__main__":
    main()
