#!/usr/bin/env python3
from __future__ import annotations

import json
import subprocess
import tempfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
CLI = ROOT / "scripts" / "kb_researcher.py"


def run(*args: str) -> dict:
    return json.loads(subprocess.check_output(["python3", str(CLI), *args], text=True))


def test_four_researcher_release_acceptance_matrix() -> None:
    with tempfile.TemporaryDirectory() as raw:
        root = Path(raw)
        registry = root / "researchers.json"
        run("registry-init", "--registry", str(registry), "--apply")
        cases = (
            ("knowledge", "knowledge-researcher", []),
            ("video", "content-researcher", ["source.video", "source.transcript", "asset.media-clip"]),
            ("industry", "industry-researcher", []),
            ("enablement", "enablement-researcher", []),
        )
        configs = []
        for researcher_id, researcher_type, capabilities in cases:
            args = [
                "init", "--registry", str(registry), "--workspace", str(root / researcher_id),
                "--researcher-id", researcher_id, "--name", researcher_id.title(),
                "--domain", f"synthetic-{researcher_id}", "--type", researcher_type,
            ]
            for capability in capabilities:
                args.extend(("--enable", capability))
            run(*args, "--apply")
            config_path = root / researcher_id / "00-系统" / "kb-config.json"
            config = json.loads(config_path.read_text(encoding="utf-8"))
            configs.append(config)
            assert config["researcher"]["type"] == researcher_type
            assert config["resolved_manifest"]["execution_plan"]
        registry_data = json.loads(registry.read_text(encoding="utf-8"))
        assert len({item["workspace"] for item in registry_data["researchers"]}) == 4
        assert len({item["config"] for item in registry_data["researchers"]}) == 4
        video = configs[1]
        assert {item["id"] for item in video["resolved_manifest"]["unavailable"]} == {
            "source.video", "asset.media-clip"
        }
        enablement = configs[3]
        assert "output.operations-sop" in enablement["capabilities"]["enabled"]
        serialized = json.dumps(configs, ensure_ascii=False)
        assert all(term not in serialized for term in ("enterprise-secret-term", "real-node-id", "plaintext-secret"))


if __name__ == "__main__":
    test_four_researcher_release_acceptance_matrix()
    print("ok")
