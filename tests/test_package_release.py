#!/usr/bin/env python3
from __future__ import annotations

import tempfile
from pathlib import Path

from kbm.application.package_release import package_lint, refresh_source_hash
from kbm import __version__


README = """# 面向产出的研究型知识管理系统
核心模型 安装方式 第一次使用 质量边界 README 维护规则 原文库
source_libraries 跨平台使用 脚本模式 v0.7.7 package-lint --strict
"""


def test_release_validation_and_hash_refresh_are_application_scoped() -> None:
    with tempfile.TemporaryDirectory() as raw:
        root = Path(raw)
        for name in ("LICENSE", "CHANGELOG.md", "SECURITY.md", "INSTALL.zh-CN.md", "ARCHITECTURE.md"):
            (root / name).write_text(name, encoding="utf-8")
        (root / "README.md").write_text(README, encoding="utf-8")
        (root / "SKILL.md").write_text("---\nname: example\ndescription: test\n---\n", encoding="utf-8")
        refresh_source_hash(root)
        assert package_lint(root, release_version="v0.7.7")["passed"] is True
        (root / "SKILL.md").write_text("changed", encoding="utf-8")
        result = package_lint(root, release_version="v0.7.7")
        assert result["passed"] is False
        assert any(item["issue"] == "readme_older_than_skill_sources" for item in result["issues"])


def test_package_version_is_v080() -> None:
    assert __version__ == "0.8.0"


def test_v080_release_requires_ci_and_version_alignment() -> None:
    with tempfile.TemporaryDirectory() as raw:
        root = Path(raw)
        for name in ("LICENSE", "CHANGELOG.md", "SECURITY.md", "INSTALL.zh-CN.md", "ARCHITECTURE.md"):
            (root / name).write_text(name, encoding="utf-8")
        (root / "README.md").write_text(README.replace("v0.7.7", "v0.8.0"), encoding="utf-8")
        (root / "SKILL.md").write_text("---\nname: example\ndescription: test\n---\n", encoding="utf-8")
        refresh_source_hash(root)
        result = package_lint(root, release_version="v0.8.0")
        assert result["passed"] is False
        assert {item["file"] for item in result["issues"]} >= {
            ".github/workflows/ci.yml", "kbm/__init__.py", "CHANGELOG.md"
        }


def test_v080_release_rejects_privileged_ci() -> None:
    with tempfile.TemporaryDirectory() as raw:
        root = Path(raw)
        for name in ("LICENSE", "SECURITY.md", "INSTALL.zh-CN.md", "ARCHITECTURE.md"):
            (root / name).write_text(name, encoding="utf-8")
        (root / "README.md").write_text(README.replace("v0.7.7", "v0.8.0"), encoding="utf-8")
        (root / "CHANGELOG.md").write_text("## [0.8.0]\n", encoding="utf-8")
        (root / "SKILL.md").write_text("---\nname: example\ndescription: test\n---\n", encoding="utf-8")
        (root / "kbm").mkdir()
        (root / "kbm" / "__init__.py").write_text('__version__ = "0.8.0"\n', encoding="utf-8")
        workflow = root / ".github" / "workflows" / "ci.yml"
        workflow.parent.mkdir(parents=True)
        workflow.write_text(
            "on: pull_request_target\npermissions:\n  contents: write\nsecret: ${{ secrets.PRIVATE }}\n",
            encoding="utf-8",
        )
        refresh_source_hash(root)
        result = package_lint(root, release_version="v0.8.0")
        assert {item["issue"] for item in result["issues"]} >= {
            "unsafe_pull_request_target", "ci_permissions_not_read_only", "ci_must_not_read_secrets"
        }


if __name__ == "__main__":
    test_release_validation_and_hash_refresh_are_application_scoped()
    print("ok")
