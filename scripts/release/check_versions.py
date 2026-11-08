#!/usr/bin/env python
"""Check that all public version markers agree.

The app version is the source of truth. Release tags, the web package, the
Helm chart, the README badge, and the latest release note must all match it.

Usage:
    python scripts/release/check_versions.py
    python scripts/release/check_versions.py --version 1.0.2
"""

import argparse
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SEMVER_RE = re.compile(r"^\d+\.\d+\.\d+(?:[-+][0-9A-Za-z.-]+)?$")


def _read(rel_path: str) -> str:
    return (ROOT / rel_path).read_text(encoding="utf-8")


def _app_version() -> str:
    match = re.search(r'^__version__\s*=\s*"([^"]+)"', _read("app/__init__.py"), re.MULTILINE)
    if not match:
        raise ValueError("Could not find __version__ in app/__init__.py")
    return match.group(1).strip()


def _web_version() -> str:
    return str(json.loads(_read("web/package.json"))["version"]).strip()


def _chart_app_version() -> str:
    match = re.search(r'^appVersion:\s*"([^"]+)"', _read("deploy/helm/ordo/Chart.yaml"), re.MULTILINE)
    if not match:
        raise ValueError("Could not find appVersion in deploy/helm/ordo/Chart.yaml")
    return match.group(1).strip()


def _release_note_version() -> str:
    versions = []
    for path in (ROOT / "docs/releases").glob("v*.md"):
        candidate = path.stem.removeprefix("v")
        if SEMVER_RE.match(candidate):
            versions.append((tuple(int(part) for part in candidate.split(".")[:3]), candidate))
    if not versions:
        raise ValueError("No docs/releases/v*.md release notes found")
    return max(versions)[1]


def _readme_badges() -> dict[str, str]:
    out: dict[str, str] = {}
    for rel_path in ("README.md", "README_EN.md"):
        text = _read(rel_path)
        match = re.search(r"release-v(\d+\.\d+\.\d+)", text)
        if not match:
            raise ValueError(f"Could not find release badge in {rel_path}")
        out[rel_path] = match.group(1)
    return out


def collect_versions() -> dict[str, str]:
    versions = {
        "app/__init__.py": _app_version(),
        "web/package.json": _web_version(),
        "deploy/helm/ordo/Chart.yaml": _chart_app_version(),
        "docs/releases (latest)": _release_note_version(),
    }
    versions.update(_readme_badges())
    return versions


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--version", help="Require this exact version")
    parser.add_argument("--quiet", action="store_true")
    args = parser.parse_args(argv)

    versions = collect_versions()
    expected = (args.version or versions["app/__init__.py"]).strip()
    if not SEMVER_RE.match(expected):
        print(f"Invalid version: {expected}", file=sys.stderr)
        return 2

    mismatches = {name: value for name, value in versions.items() if value != expected}
    if not args.quiet:
        for name, value in versions.items():
            marker = "OK " if value == expected else "BAD"
            print(f"[{marker}] {name}: {value} (expected {expected})")

    if mismatches:
        print(f"Version mismatch: {', '.join(sorted(mismatches))}", file=sys.stderr)
        return 1

    if not args.quiet:
        print(f"All version markers match {expected}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
