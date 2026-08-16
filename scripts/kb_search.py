#!/usr/bin/env python3
"""Build and query a device-local citation-first knowledge index."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from kbm.application.retrieval import LAYERS, query, rebuild, status
from kbm.platform.config import load_config, require_valid_config


def parser() -> argparse.ArgumentParser:
    root = argparse.ArgumentParser(description="Index and search durable knowledge artifacts.")
    root.add_argument("--config", required=True, type=Path)
    sub = root.add_subparsers(dest="command", required=True)
    item = sub.add_parser("rebuild")
    item.add_argument("--layer", action="append", choices=tuple(LAYERS), default=[])
    item.add_argument("--apply", action="store_true")
    item = sub.add_parser("query")
    item.add_argument("--query", required=True); item.add_argument("--limit", type=int)
    item.add_argument("--layer", action="append", choices=tuple(LAYERS), default=[])
    sub.add_parser("status")
    return root


def main() -> None:
    args = parser().parse_args()
    try:
        cfg = load_config(args.config)
        require_valid_config(cfg)
        if args.command == "rebuild":
            result = rebuild(cfg, layers=args.layer, apply=args.apply)
        elif args.command == "query":
            result = query(cfg, args.query, limit=args.limit or int(cfg["retrieval"]["default_limit"]), layers=args.layer)
        else:
            result = status(cfg)
        print(json.dumps({"ok": True, **result}, ensure_ascii=False, indent=2))
    except (ValueError, OSError, json.JSONDecodeError) as exc:
        print(json.dumps({"ok": False, "error": str(exc)}, ensure_ascii=False, indent=2))
        raise SystemExit(1)


if __name__ == "__main__":
    main()
