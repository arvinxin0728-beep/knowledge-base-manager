#!/usr/bin/env python3
from __future__ import annotations

import json
import subprocess
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
CHECK = ROOT / "scripts" / "architecture_check.py"


def test_architecture_contract() -> None:
    result = json.loads(subprocess.check_output(["python3", str(CHECK), "--strict"], text=True))
    assert result["passed"] is True
    assert result["architecture_style"] == "modular_monolith"
    assert "scripts/kb_manager.py" in result["metrics"]
    assert (ROOT / "kbm" / "domain" / "researcher.py").is_file()
    assert (ROOT / "kbm" / "platform" / "config.py").is_file()


if __name__ == "__main__":
    test_architecture_contract()
    print("ok")
