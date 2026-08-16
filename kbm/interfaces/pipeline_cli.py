"""Argument parser for the recoverable source-processing pipeline."""

from __future__ import annotations

import argparse
from pathlib import Path


def build_parser(version: str) -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Recoverable knowledge-source processing pipeline")
    parser.add_argument("--config", required=True, type=Path)
    parser.add_argument("--version", action="version", version=version)
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("init"); sub.add_parser("discover")
    item = sub.add_parser("prepare"); item.add_argument("--limit", type=int); item.add_argument("--max-attempts", type=int); item.add_argument("--source-type")
    item = sub.add_parser("extract"); item.add_argument("--limit", type=int); item.add_argument("--max-attempts", type=int); item.add_argument("--source-type")
    item = sub.add_parser("claim"); item.add_argument("--worker", required=True); item.add_argument("--limit", type=int); item.add_argument("--lease-minutes", type=int); item.add_argument("--source-type")
    item = sub.add_parser("submit"); item.add_argument("--job-id", required=True); item.add_argument("--lease-token", required=True); item.add_argument("--refinement", type=Path); item.add_argument("--metadata", type=Path); item.add_argument("--model-run-id")
    item = sub.add_parser("commit"); item.add_argument("--job-id", required=True)
    item = sub.add_parser("commit-ready"); item.add_argument("--limit", type=int, default=100)
    item = sub.add_parser("fail"); item.add_argument("--job-id", required=True); item.add_argument("--lease-token", required=True); item.add_argument("--error", required=True)
    item = sub.add_parser("adopt-existing"); item.add_argument("--job-id", required=True); item.add_argument("--existing-file", required=True, type=Path)
    item = sub.add_parser("retry"); item.add_argument("--limit", type=int, default=10)
    item = sub.add_parser("cleanup"); item.add_argument("--retention-days", type=int); item.add_argument("--apply", action="store_true")
    item = sub.add_parser("migrate-runtime"); item.add_argument("--apply", action="store_true")
    item = sub.add_parser("retire-legacy-runtime"); item.add_argument("--apply", action="store_true")
    sub.add_parser("storage-status"); sub.add_parser("status")
    return parser
