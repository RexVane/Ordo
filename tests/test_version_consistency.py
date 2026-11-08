"""Keep public version markers in sync (app, web, Helm, README, release notes)."""

import importlib.util
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "release" / "check_versions.py"


def _load_release_check():
    spec = importlib.util.spec_from_file_location("ordo_release_check_versions", SCRIPT)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_public_version_markers_match() -> None:
    module = _load_release_check()
    versions = module.collect_versions()
    expected = versions["app/__init__.py"]
    mismatches = {name: value for name, value in versions.items() if value != expected}
    assert mismatches == {}


def test_release_check_cli_passes() -> None:
    module = _load_release_check()
    assert module.main(["--quiet"]) == 0
