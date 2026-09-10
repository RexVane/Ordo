#!/usr/bin/env python3
"""Structured `.env` checks for Ordo (PR4: config profiles + schema guardrails).

Compares a concrete env file against `.env.example` (the single source of
truth for known variable names) and reports:

- ERROR: unknown variables (usually typos that would silently do nothing,
  because Settings uses ``extra="ignore"`` with case-sensitive parsing);
- ERROR: deprecated variables with a known successor;
- ERROR: empty SECRET_KEY (startup refuses JWT auth without it);
- WARN:  empty LLM_API_KEY (boots, but model calls are unavailable);
- WARN:  partial INITIAL_ADMIN_* bootstrap identity.

Pure functions are unit-tested in ``tests/test_check_env.py`` (no deps).
Exit code is 1 when any ERROR is present, else 0.

Usage:
    python scripts/check_env.py [--env-file .env] [--example .env.example]
"""

from __future__ import annotations

import argparse
import re
import sys
from dataclasses import dataclass, field
from pathlib import Path

_KEY_RE = re.compile(r"^\s*(?:export\s+)?([A-Za-z_][A-Za-z0-9_]*)\s*=")

# Verified renames (config.py validation_alias entries). Warn, do not fail boot.
DEPRECATED_VARS: dict[str, str] = {
    "BISHENG_UNSTRUCTURED_ENABLED": "ETL4LLM_ENABLED",
    "BISHENG_UNSTRUCTURED_API_URL": "ETL4LLM_API_URL",
    "BISHENG_UNSTRUCTURED_TIMEOUT_SEC": "ETL4LLM_TIMEOUT_SEC",
    "BISHENG_UNSTRUCTURED_MODE": "ETL4LLM_MODE",
    "BISHENG_UNSTRUCTURED_FORCE_OCR": "ETL4LLM_FORCE_OCR",
    "BISHENG_UNSTRUCTURED_ENABLE_FORMULA": "ETL4LLM_ENABLE_FORMULA",
    "BISHENG_UNSTRUCTURED_EXTRACT_IMAGES": "ETL4LLM_EXTRACT_IMAGES",
}

# Never treat a *value* as a finding; only names are inspected, so secrets are
# never printed by this script.
SECRET_LIKE_KEYS = ("SECRET", "PASSWORD", "API_KEY", "TOKEN")


@dataclass
class EnvReport:
    unknown: list[str] = field(default_factory=list)
    deprecated: list[tuple[str, str]] = field(default_factory=list)
    missing_secret_key: bool = False
    llm_key_empty: bool = False
    partial_admin_bootstrap: bool = False

    @property
    def has_errors(self) -> bool:
        return bool(self.unknown or self.deprecated or self.missing_secret_key)


def parse_env_keys(text: str) -> dict[str, str]:
    """Parse KEY=value pairs from env-file text (no interpolation, no export)."""
    values: dict[str, str] = {}
    for raw_line in text.splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        match = _KEY_RE.match(raw_line)
        if not match:
            continue
        key = match.group(1)
        value = raw_line.split("=", 1)[1].strip().strip("'\"").strip()
        values[key] = value
    return values


def find_unknown(keys: set[str], known: set[str]) -> list[str]:
    return sorted(key for key in keys if key not in known)


def find_deprecated(keys: set[str]) -> list[tuple[str, str]]:
    return sorted((key, DEPRECATED_VARS[key]) for key in keys if key in DEPRECATED_VARS)


def check_env(env_values: dict[str, str], known_keys: set[str]) -> EnvReport:
    report = EnvReport()
    report.unknown = find_unknown(set(env_values), known_keys)
    report.deprecated = find_deprecated(set(env_values))
    report.missing_secret_key = not (env_values.get("SECRET_KEY") or "").strip()
    report.llm_key_empty = not (env_values.get("LLM_API_KEY") or "").strip()
    admin_parts = [
        (env_values.get("INITIAL_ADMIN_EMAIL") or "").strip(),
        (env_values.get("INITIAL_ADMIN_USERNAME") or "").strip(),
        (env_values.get("INITIAL_ADMIN_PASSWORD") or "").strip(),
        (env_values.get("INITIAL_ADMIN_PASSWORD_FILE") or "").strip(),
    ]
    email, username, password, password_file = admin_parts
    filled = sum(1 for part in admin_parts if part)
    sources = int(bool(password)) + int(bool(password_file))
    complete = bool(email) and bool(username) and sources == 1
    report.partial_admin_bootstrap = 0 < filled and not complete
    return report


def _maskable(key: str) -> bool:
    upper = key.upper()
    return any(token in upper for token in SECRET_LIKE_KEYS)


def render(report: EnvReport) -> str:
    lines: list[str] = []
    if report.unknown:
        lines.append("[ERROR] unknown variables (possible typos, silently ignored):")
        lines.extend(f"  - {key}" for key in report.unknown)
    if report.deprecated:
        lines.append("[ERROR] deprecated variables (rename to the successor):")
        lines.extend(f"  - {old} -> {new}" for old, new in report.deprecated)
    if report.missing_secret_key:
        lines.append("[ERROR] SECRET_KEY is empty (run `make init` or set a >=32-char value).")
    if report.llm_key_empty:
        lines.append("[WARN] LLM_API_KEY is empty (boots, but model calls are unavailable).")
    if report.partial_admin_bootstrap:
        lines.append(
            "[WARN] INITIAL_ADMIN_* is partially filled "
            "(needs EMAIL + USERNAME + exactly one password source)."
        )
    if not lines:
        lines.append("[check-env] OK: no unknown/deprecated variables, secrets present.")
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Check an Ordo .env file for typos and gaps.")
    parser.add_argument("--env-file", default=".env")
    parser.add_argument("--example", default=".env.example")
    args = parser.parse_args(argv)

    repo_root = Path(__file__).resolve().parents[1]
    env_path = Path(args.env_file)
    if not env_path.is_absolute():
        env_path = repo_root / env_path
    example_path = Path(args.example)
    if not example_path.is_absolute():
        example_path = repo_root / example_path

    if not env_path.is_file():
        print(f"[check-env] missing env file: {env_path} (run `make init` first)")
        return 2
    if not example_path.is_file():
        print(f"[check-env] missing example file: {example_path}")
        return 2

    env_values = parse_env_keys(env_path.read_text(encoding="utf-8"))
    known_keys = set(parse_env_keys(example_path.read_text(encoding="utf-8")))
    # Legacy aliases are still honored by Settings; do not flag them as typos.
    known_keys.update(DEPRECATED_VARS)
    known_keys.update(DEPRECATED_VARS.values())
    # Compose-only mechanics that intentionally never reach Settings.
    known_keys.update({"COMPOSE_PROJECT_NAME"})

    report = check_env(env_values, known_keys)
    print(render(report))
    return 1 if report.has_errors else 0


if __name__ == "__main__":
    raise SystemExit(main())
