#!/usr/bin/env python3
"""Dependency-free runner for the repository's plain-function regression tests."""

from __future__ import annotations

import importlib.util
import inspect
import sys
import traceback
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
TESTS = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))


def main() -> None:
    passed = 0
    failed = 0
    for path in sorted(TESTS.glob("test_*.py")):
        spec = importlib.util.spec_from_file_location(path.stem, path)
        assert spec and spec.loader
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        for name, function in inspect.getmembers(module, inspect.isfunction):
            if not name.startswith("test_") or function.__module__ != module.__name__:
                continue
            try:
                function()
                passed += 1
            except (Exception, SystemExit):
                failed += 1
                print(f"FAILED {path.name}::{name}", file=sys.stderr)
                traceback.print_exc()
    e2e_path = TESTS / "e2e_new_user.py"
    spec = importlib.util.spec_from_file_location(e2e_path.stem, e2e_path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    try:
        module.test_new_user_portable_lifecycle()
        passed += 1
    except BaseException:
        failed += 1
        print("FAILED e2e_new_user.py::test_new_user_portable_lifecycle", file=sys.stderr)
        traceback.print_exc()
    print(f"passed={passed} failed={failed}")
    if failed:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
