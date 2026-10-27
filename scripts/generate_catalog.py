"""Regenerate docs/catalog.md and the failure table in README.md from the registry.

Run it after adding or changing a failure:

    python scripts/generate_catalog.py

Use --check to fail without writing anything when the files are out of date. CI does this.
"""

import argparse
import sys
from collections.abc import Sequence
from pathlib import Path

from agent_failure_lab.catalog import catalog_page, catalog_table, splice
from agent_failure_lab.registry import build_registry

# The README is also the PyPI description, where relative links do not resolve.
README_LINK_BASE = "https://github.com/hasnatahmadai164/agent-failure-lab/blob/main/"


def build_outputs(root: Path) -> dict[Path, str]:
    scenarios = build_registry().scenarios()
    readme = root / "README.md"
    return {
        root / "docs" / "catalog.md": catalog_page(scenarios),
        readme: splice(
            readme.read_text(encoding="utf-8"),
            catalog_table(scenarios, prefix=README_LINK_BASE),
        ),
    }


def main(argv: Sequence[str] | None = None, *, root: Path | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0] if __doc__ else None)
    parser.add_argument("--check", action="store_true", help="exit 1 if a file is out of date")
    args = parser.parse_args(argv)

    root = root or Path(__file__).resolve().parents[1]
    outputs = build_outputs(root)
    stale = [
        path
        for path, content in outputs.items()
        if not path.exists() or path.read_text(encoding="utf-8") != content
    ]
    if args.check:
        for path in stale:
            print(f"out of date: {path.relative_to(root)}")
        if stale:
            print("Run: python scripts/generate_catalog.py")
        return 1 if stale else 0

    for path in stale:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(outputs[path], encoding="utf-8", newline="\n")
        print(f"updated {path.relative_to(root)}")
    if not stale:
        print("already up to date")
    return 0


if __name__ == "__main__":
    sys.exit(main())
