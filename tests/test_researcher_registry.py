#!/usr/bin/env python3
from __future__ import annotations

import json
import os
import subprocess
import tempfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
CLI = ROOT / "scripts" / "kb_researcher.py"


def run(*args: str) -> dict:
    return json.loads(subprocess.check_output(["python3", str(CLI), *args], text=True))


def test_registry_init_register_select_and_doctor() -> None:
    with tempfile.TemporaryDirectory() as raw:
        root = Path(raw)
        registry = root / "registry" / "researchers.json"
        runtime = root / "runtime"
        previous = os.environ.get("KBM_RUNTIME_ROOT")
        os.environ["KBM_RUNTIME_ROOT"] = str(runtime)
        try:
            run("registry-init", "--registry", str(registry), "--apply")
            for researcher_id in ("knowledge-researcher", "video-researcher"):
                profile = "video" if researcher_id.startswith("video") else "knowledge"
                run(
                    "init", "--registry", str(registry), "--workspace", str(root / researcher_id),
                    "--researcher-id", researcher_id, "--name", researcher_id,
                    "--domain", f"{profile} research", "--profile", profile, "--apply",
                )
            listed = run("list", "--registry", str(registry))
            assert [item["id"] for item in listed["researchers"]] == ["knowledge-researcher", "video-researcher"]
            run("select", "--registry", str(registry), "--researcher-id", "video-researcher", "--apply")
            assert run("show", "--registry", str(registry))["researcher"]["id"] == "video-researcher"
            assert run("doctor", "--registry", str(registry))["ok"] is True
            video_cfg = json.loads((root / "video-researcher" / "00-系统" / "kb-config.json").read_text(encoding="utf-8"))
            assert video_cfg["source_adapters"]["video"]["enabled"] is False
            assert video_cfg["mapping"]["media_assets"] == "50-素材库"
            assert video_cfg["source_refinement_subdirs"] == {"videos": "视频"}
            assert (root / "video-researcher" / "50-素材库" / "关键帧").is_dir()
        finally:
            if previous is None:
                os.environ.pop("KBM_RUNTIME_ROOT", None)
            else:
                os.environ["KBM_RUNTIME_ROOT"] = previous


def test_registry_rejects_shared_workspace_and_duplicate_identity() -> None:
    with tempfile.TemporaryDirectory() as raw:
        root = Path(raw)
        registry = root / "researchers.json"
        run("registry-init", "--registry", str(registry), "--apply")
        run(
            "init", "--registry", str(registry), "--workspace", str(root / "one"),
            "--researcher-id", "one", "--name", "One", "--domain", "one", "--apply",
        )
        config = root / "two.json"
        existing = json.loads((root / "one" / "00-系统" / "kb-config.json").read_text(encoding="utf-8"))
        existing["researcher"]["id"] = "two"
        existing["researcher"]["name"] = "Two"
        config.write_text(json.dumps(existing), encoding="utf-8")
        failed = subprocess.run(
            ["python3", str(CLI), "register", "--registry", str(registry), "--config", str(config), "--apply"],
            text=True, capture_output=True,
        )
        assert failed.returncode != 0
        assert "workspace_already_registered" in failed.stdout


if __name__ == "__main__":
    test_registry_init_register_select_and_doctor()
    test_registry_rejects_shared_workspace_and_duplicate_identity()
    print("ok")
