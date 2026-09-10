"""P0: upload content screens (magic bytes + office zip-bomb guard).

Stdlib-only tests for ``app.api.utils.file_safety``.
"""

import importlib.util
import sys
import zipfile
from pathlib import Path

REPO = str(Path(__file__).resolve().parents[1])


def _load():
    name = "ordo_file_safety"
    if name in sys.modules:
        return sys.modules[name]
    spec = importlib.util.spec_from_file_location(name, REPO + "/app/api/utils/file_safety.py")
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


fs = _load()


def _write(tmp_path, name: str, data: bytes) -> str:
    path = tmp_path / name
    path.write_bytes(data)
    return str(path)


def test_pdf_signature_ok_and_spoof_rejected(tmp_path):
    assert fs.verify_file_signature(_write(tmp_path, "a.pdf", b"%PDF-1.7 rest"), ".pdf") is None
    reason = fs.verify_file_signature(_write(tmp_path, "b.pdf", b"MZ\x90\x00evil"), ".pdf")
    assert reason is not None and ".pdf" in reason


def test_office_zip_ok_and_spoof_rejected(tmp_path):
    zpath = str(tmp_path / "a.docx")
    with zipfile.ZipFile(zpath, "w") as archive:
        archive.writestr("[Content_Types].xml", "<t/>")
    assert fs.verify_file_signature(zpath, ".docx") is None
    assert fs.verify_file_signature(zpath, ".pdf") is not None
    # xlsx bytes with a .csv extension must not pass as text.
    assert fs.verify_file_signature(zpath, ".csv") is not None


def test_text_and_images(tmp_path):
    assert fs.verify_file_signature(_write(tmp_path, "a.txt", "hello 世界\n".encode()), ".txt") is None
    assert fs.verify_file_signature(_write(tmp_path, "b.txt", "hi".encode("utf-16")), ".txt") is None
    assert fs.verify_file_signature(_write(tmp_path, "c.md", b"# title\n"), ".md") is None
    assert fs.verify_file_signature(_write(tmp_path, "a.png", b"\x89PNG\r\n\x1a\nrest"), ".png") is None
    assert fs.verify_file_signature(_write(tmp_path, "b.png", b"%PDF-1.4"), ".png") is not None
    assert fs.verify_file_signature(_write(tmp_path, "e.txt", b""), ".txt") is not None


def test_office_zip_limits(tmp_path):
    zpath = str(tmp_path / "bomb.docx")
    with zipfile.ZipFile(zpath, "w") as archive:
        for i in range(5):
            archive.writestr(f"f{i}.xml", "<t/>")
    assert fs.check_office_zip_limits(zpath) is None
    assert fs.check_office_zip_limits(zpath, max_files=3) is not None

    big = str(tmp_path / "big.xlsx")
    with zipfile.ZipFile(big, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        archive.writestr("sheet.xml", "x" * 10000)
    assert fs.check_office_zip_limits(big, max_total_uncompressed_bytes=100) is not None

    broken = _write(tmp_path, "broken.docx", b"PK\x03\x04 truncated")
    assert fs.check_office_zip_limits(broken) is not None


def test_screen_saved_upload_combines_checks(tmp_path):
    zpath = str(tmp_path / "a.docx")
    with zipfile.ZipFile(zpath, "w") as archive:
        archive.writestr("[Content_Types].xml", "<t/>")
    assert fs.screen_saved_upload(zpath, ".docx") is None
    # max_zip_files=0 clamps to 1 entry minimum; single-entry file still passes.
    assert fs.screen_saved_upload(zpath, ".docx", max_zip_files=0) is None
    spoof = _write(tmp_path, "s.pdf", b"plain text, not a pdf")
    assert fs.screen_saved_upload(spoof, ".pdf") is not None
