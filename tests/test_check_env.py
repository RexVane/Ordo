"""PR4: env-file checker (typo/deprecated/secret-gap detection).

Pure-function tests for ``scripts/check_env.py`` (stdlib only).
"""

import importlib.util
import sys
from pathlib import Path

import pytest

REPO = str(Path(__file__).resolve().parents[1])


def _load_checker():
    spec = importlib.util.spec_from_file_location(
        "ordo_check_env", REPO + "/scripts/check_env.py"
    )
    module = importlib.util.module_from_spec(spec)
    sys.modules["ordo_check_env"] = module
    spec.loader.exec_module(module)
    return module


checker = _load_checker()


def test_parse_env_keys_skips_comments_and_handles_export():
    text = "# comment\nFOO=1\nexport BAR = two\n\nMALFORMED\nBAZ=' quoted '\n"
    assert checker.parse_env_keys(text) == {"FOO": "1", "BAR": "two", "BAZ": "quoted"}


def test_unknown_detection_flags_typos():
    report = checker.check_env(
        {"SECRET_KEY": "x" * 32, "LLM_MODLE": "oops", "PORT": "8000"},
        {"SECRET_KEY", "LLM_MODEL", "PORT"},
    )
    assert report.unknown == ["LLM_MODLE"]
    assert report.has_errors is True


def test_deprecated_mapping_warns_with_successor():
    report = checker.check_env(
        {"SECRET_KEY": "x" * 32, "BISHENG_UNSTRUCTURED_ENABLED": "true"},
        {"SECRET_KEY", "BISHENG_UNSTRUCTURED_ENABLED"},
    )
    assert report.deprecated == [("BISHENG_UNSTRUCTURED_ENABLED", "ETL4LLM_ENABLED")]
    assert report.has_errors is True


def test_secret_and_admin_gaps():
    report = checker.check_env({}, set())
    assert report.missing_secret_key is True
    assert report.llm_key_empty is True
    assert report.partial_admin_bootstrap is False

    partial = checker.check_env(
        {"SECRET_KEY": "x" * 32, "INITIAL_ADMIN_EMAIL": "a@b.c"},
        {"SECRET_KEY", "INITIAL_ADMIN_EMAIL"},
    )
    assert partial.partial_admin_bootstrap is True
    assert partial.has_errors is False

    complete = checker.check_env(
        {
            "SECRET_KEY": "x" * 32,
            "INITIAL_ADMIN_EMAIL": "a@b.c",
            "INITIAL_ADMIN_USERNAME": "owner",
            "INITIAL_ADMIN_PASSWORD": "strong-password-99",
        },
        {
            "SECRET_KEY",
            "INITIAL_ADMIN_EMAIL",
            "INITIAL_ADMIN_USERNAME",
            "INITIAL_ADMIN_PASSWORD",
        },
    )
    assert complete.partial_admin_bootstrap is False


def test_clean_env_passes():
    report = checker.check_env(
        {"SECRET_KEY": "x" * 32, "LLM_API_KEY": "k"}, {"SECRET_KEY", "LLM_API_KEY"}
    )
    assert report.has_errors is False
    assert "OK" in checker.render(report)
