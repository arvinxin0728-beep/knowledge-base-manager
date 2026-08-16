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


def test_research_design_composition_release_acceptance_matrix() -> None:
    with tempfile.TemporaryDirectory() as raw:
        root = Path(raw)
        registry = root / "researchers.json"
        run("registry-init", "--registry", str(registry), "--apply")
        cases = (
            ("knowledge", "general-knowledge", [], [], []),
            ("mixed-content", "content-publication", ["video"], [], []),
            ("industry-decision", "industry-intelligence", [], [], ["decision-memo"]),
            ("role-learning", "learning", ["article"], ["role-enablement"], ["operations-sop"]),
        )
        configs = []
        for researcher_id, preset, sources, processes, outputs in cases:
            args = [
                "init", "--registry", str(registry), "--workspace", str(root / researcher_id),
                "--researcher-id", researcher_id, "--name", researcher_id.title(),
                "--theme", f"synthetic-{researcher_id}", "--preset", preset,
            ]
            for value in sources:
                args.extend(("--source", value))
            for value in processes:
                args.extend(("--process", value))
            for value in outputs:
                args.extend(("--output", value))
            run(*args, "--apply")
            config_path = root / researcher_id / "00-系统" / "kb-config.json"
            config = json.loads(config_path.read_text(encoding="utf-8"))
            configs.append(config)
            assert "type" not in config["researcher"]
            assert config["research_design"]["preset"] == preset
            assert config["resolved_manifest"]["execution_plan"]
        registry_data = json.loads(registry.read_text(encoding="utf-8"))
        assert len({item["workspace"] for item in registry_data["researchers"]}) == 4
        assert len({item["config"] for item in registry_data["researchers"]}) == 4
        mixed = configs[1]
        assert mixed["resolved_manifest"]["layout_profile"] == "mixed"
        assert {item["id"] for item in mixed["resolved_manifest"]["unavailable"]} == {"source.video"}
        role_learning = configs[3]
        assert {"ebook", "article"} <= set(role_learning["research_design"]["sources"])
        assert "role-enablement" in role_learning["research_design"]["process"]
        assert "output.operations-sop" in role_learning["capabilities"]["enabled"]
        serialized = json.dumps(configs, ensure_ascii=False)
        assert all(term not in serialized for term in ("enterprise-secret-term", "real-node-id", "plaintext-secret"))


if __name__ == "__main__":
    test_research_design_composition_release_acceptance_matrix()
    print("ok")
