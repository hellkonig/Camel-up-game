"""Command-line entry point for Camel Up."""

from __future__ import annotations

import runpy


def main() -> int:
    """Run the current CLI game loop."""
    runpy.run_module("main", run_name="__main__")
    return 0
