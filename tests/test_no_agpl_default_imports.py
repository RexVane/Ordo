"""The default distribution must not require AGPL-licensed PyMuPDF."""

import ast
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
APP_DIR = ROOT / "app"


def _top_level_imports(path: Path) -> set[str]:
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    modules: set[str] = set()
    for node in tree.body:
        if isinstance(node, ast.Import):
            modules.update(alias.name.split(".")[0] for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            modules.add(node.module.split(".")[0])
    return modules


def test_base_requirements_do_not_include_pymupdf() -> None:
    lines = [
        line.strip().lower()
        for line in (ROOT / "requirements.txt").read_text(encoding="utf-8").splitlines()
        if line.strip() and not line.lstrip().startswith("#")
    ]
    assert all("pymupdf" not in line and "fitz" not in line for line in lines)


def test_no_module_level_fitz_imports() -> None:
    offenders = []
    for path in APP_DIR.rglob("*.py"):
        if "fitz" in _top_level_imports(path):
            offenders.append(str(path.relative_to(ROOT)))
    assert offenders == []


def test_basic_pdf_parser_uses_pdfplumber() -> None:
    text = (APP_DIR / "parsing" / "parsers" / "pdf_parser.py").read_text(encoding="utf-8")
    assert "import pdfplumber" in text
    assert "import fitz" not in text
