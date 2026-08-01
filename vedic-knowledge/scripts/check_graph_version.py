#!/usr/bin/env python3
"""CLI: exit 1 if GRAPH_VERSION mismatches graph.json metadata."""
from __future__ import annotations

import os
import sys

from vedic_knowledge import GraphVersionMismatchError, check_graph_version, read_graph_metadata


def main() -> int:
    meta = read_graph_metadata()
    print(f"graph path   : {meta.get('path')}")
    print(f"graph version: {meta.get('version')}")
    print(f"GRAPH_VERSION: {os.environ.get('GRAPH_VERSION')!r}")
    try:
        result = check_graph_version(strict=bool(os.environ.get("GRAPH_VERSION")))
    except GraphVersionMismatchError as exc:
        print(f"FAIL: {exc}", file=sys.stderr)
        return 1
    print(f"result: {result.get('message')}")
    return 0 if result.get("ok") else 1


if __name__ == "__main__":
    raise SystemExit(main())
