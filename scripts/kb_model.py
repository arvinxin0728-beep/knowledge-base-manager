#!/usr/bin/env python3
"""Record and resume model work performed for pipeline refinement jobs."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from kbm.application.model_runs import (
    complete_run, connect_model_ledger, fail_run, list_runs, start_run, summary,
)
from kbm.platform.config import load_config, require_valid_config


def parser() -> argparse.ArgumentParser:
    root = argparse.ArgumentParser(description="Manage transactional model runs.")
    root.add_argument("--config", required=True, type=Path)
    sub = root.add_subparsers(dest="command", required=True)
    item = sub.add_parser("start")
    item.add_argument("--job-id", required=True); item.add_argument("--lease-token", required=True)
    item.add_argument("--provider", default="unspecified"); item.add_argument("--model", required=True)
    item.add_argument("--prompt-version", required=True); item.add_argument("--prompt-sha256")
    item = sub.add_parser("complete")
    item.add_argument("--run-id", required=True); item.add_argument("--output", required=True, type=Path)
    item.add_argument("--metadata", required=True, type=Path); item.add_argument("--input-tokens", type=int)
    item.add_argument("--output-tokens", type=int); item.add_argument("--duration-ms", type=int)
    item = sub.add_parser("fail")
    item.add_argument("--run-id", required=True); item.add_argument("--error-code", required=True)
    item.add_argument("--error-detail", default="")
    item = sub.add_parser("list")
    item.add_argument("--job-id"); item.add_argument("--limit", type=int, default=50)
    sub.add_parser("status")
    return root


def main() -> None:
    args = parser().parse_args()
    try:
        cfg = load_config(args.config)
        require_valid_config(cfg)
        with connect_model_ledger(cfg) as db:
            if args.command == "start":
                result = start_run(db, job_id=args.job_id, lease_token=args.lease_token, provider=args.provider, model=args.model, prompt_version=args.prompt_version, prompt_sha256=args.prompt_sha256)
            elif args.command == "complete":
                result = complete_run(cfg, db, run_id=args.run_id, output=args.output, metadata=args.metadata, input_tokens=args.input_tokens, output_tokens=args.output_tokens, duration_ms=args.duration_ms)
            elif args.command == "fail":
                result = fail_run(db, run_id=args.run_id, error_code=args.error_code, error_detail=args.error_detail)
            elif args.command == "list":
                result = {"runs": list_runs(db, job_id=args.job_id, limit=args.limit)}
            else:
                result = summary(db)
        print(json.dumps({"ok": True, **result}, ensure_ascii=False, indent=2))
    except (ValueError, OSError, json.JSONDecodeError) as exc:
        print(json.dumps({"ok": False, "error": str(exc)}, ensure_ascii=False, indent=2))
        raise SystemExit(1)


if __name__ == "__main__":
    main()
