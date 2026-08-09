"""Release-package validation, independent of knowledge processing."""

from __future__ import annotations

import hashlib
from pathlib import Path
from typing import Any


REQUIRED_RELEASE_FILES = ("LICENSE", "CHANGELOG.md", "SECURITY.md", "INSTALL.zh-CN.md", "ARCHITECTURE.md")
REQUIRED_README_TERMS = (
    "面向产出的研究型知识管理系统", "核心模型", "安装方式", "第一次使用",
    "质量边界", "README 维护规则", "原文库", "source_libraries",
    "跨平台使用", "脚本模式", "v0.6.0", "package-lint --strict",
)


def tracked_package_files(skill_root: Path) -> list[Path]:
    files = sorted((path for path in skill_root.rglob("*") if path.is_file()), key=str)
    return [
        path for path in files
        if path.name != "README.md"
        and path.suffix.lower() in {".md", ".json", ".yaml", ".yml", ".py", ".rb"}
        and not str(path.relative_to(skill_root)).startswith("tests/")
        and "__pycache__" not in path.parts
    ]


def source_content_hash(tracked: list[Path]) -> str:
    digest = hashlib.sha256()
    for path in sorted(tracked, key=str):
        digest.update(path.read_bytes())
    return digest.hexdigest()


def package_lint(skill_root: Path, *, release_version: str = "v0.7.4") -> dict[str, Any]:
    issues: list[dict[str, str]] = []
    files = sorted((path for path in skill_root.rglob("*") if path.is_file()), key=str)
    for relative in REQUIRED_RELEASE_FILES:
        if not (skill_root / relative).exists():
            issues.append({"file": relative, "issue": "missing_release_file"})
    readme = skill_root / "README.md"
    if not readme.exists():
        issues.append({"file": "README.md", "issue": "missing_chinese_readme"})
    else:
        readme_text = readme.read_text(encoding="utf-8", errors="ignore")
        for term in (*REQUIRED_README_TERMS[:-2], release_version, REQUIRED_README_TERMS[-1]):
            if term not in readme_text:
                issues.append({"file": "README.md", "issue": "readme_missing_required_section", "term": term})
        tracked = tracked_package_files(skill_root)
        if tracked:
            current_hash = source_content_hash(tracked)
            source_hash = skill_root / ".source_hash"
            reference_hash = source_hash.read_text(encoding="utf-8").strip() if source_hash.exists() else current_hash
            if current_hash and reference_hash and current_hash != reference_hash:
                issues.append({
                    "file": "README.md",
                    "issue": "readme_older_than_skill_sources",
                    "newest_source": "source files changed since README was last verified",
                })
    for path in files:
        relative = str(path.relative_to(skill_root))
        if ".bak" in path.name or path.suffix in {".tmp", ".orig"}:
            issues.append({"file": relative, "issue": "temporary_or_backup_file"})
        if relative.startswith("references/8xx"):
            issues.append({"file": relative, "issue": "user_profile_must_not_live_in_default_references"})
        if "__pycache__" in path.parts:
            issues.append({"file": relative, "issue": "python_cache_file"})
        if path.suffix.lower() in {".md", ".json", ".yaml", ".yml", ".py", ".rb"}:
            text = path.read_text(encoding="utf-8", errors="ignore")
            if relative.startswith("tests/fixtures/") and "/Users/" in text:
                issues.append({"file": relative, "issue": "fixture_contains_absolute_user_path"})
            if relative == "SKILL.md" and "Current 8XX implementation" in text:
                issues.append({"file": relative, "issue": "main_skill_contains_user_specific_mapping"})
    return {"passed": not issues, "files_scanned": len(files), "issue_count": len(issues), "issues": issues}


def refresh_source_hash(skill_root: Path) -> str:
    value = source_content_hash(tracked_package_files(skill_root))
    (skill_root / ".source_hash").write_text(value, encoding="utf-8")
    return value
