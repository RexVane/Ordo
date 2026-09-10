"""File-content safety checks for uploads and URL ingest (P0).

Stdlib-only, no app imports: safe to unit-test anywhere.

- :func:`verify_file_signature`: magic-bytes check that the stored bytes match
  the claimed extension (closes extension-spoofing).
- :func:`check_office_zip_limits`: zip-bomb guard for OOXML-style formats by
  reading the central directory only (no extraction).

Both return a human-safe rejection reason, or ``None`` when the file passes
(or the format has no fingerprint rule yet — extension allowlist still gates).
"""

from __future__ import annotations

import zipfile
from pathlib import Path

# Extension -> accepted magic kinds. Unknown extensions are not rejected here
# (the extension allowlist is enforced separately at the API layer).
_ZIP_OFFICE_EXTS = frozenset(
    {
        ".docx",
        ".docm",
        ".xlsx",
        ".xlsm",
        ".pptx",
        ".pptm",
        ".odt",
        ".ods",
        ".odp",
        ".epub",
    }
)
_OLE_OFFICE_EXTS = frozenset({".doc", ".xls", ".ppt", ".msg"})
_PDF_EXTS = frozenset({".pdf"})
_PNG_EXTS = frozenset({".png"})
_JPEG_EXTS = frozenset({".jpg", ".jpeg"})
_GIF_EXTS = frozenset({".gif"})


def sniff_kind(header: bytes) -> str:
    """Classify leading bytes into a coarse kind label."""
    if header[:4] == b"%PDF":
        return "pdf"
    if header[:4] == b"PK\x03\x04" or header[:4] == b"PK\x05\x06" or header[:4] == b"PK\x07\x08":
        return "zip"
    if header[:8] == b"\x89PNG\r\n\x1a\n":
        return "png"
    if header[:3] == b"\xff\xd8\xff":
        return "jpeg"
    if header[:6] in (b"GIF87a", b"GIF89a"):
        return "gif"
    if header[:8] == b"\xd0\xcf\x11\xe0\xa1\xb1\x1a\xe1":
        return "ole"
    return "unknown"


def expected_kind(file_ext: str) -> str | None:
    """Return the required magic kind for an extension, or None if unmapped."""
    ext = (file_ext or "").strip().lower()
    if not ext.startswith("."):
        ext = f".{ext}" if ext else ""
    if ext in _PDF_EXTS:
        return "pdf"
    if ext in _ZIP_OFFICE_EXTS:
        return "zip"
    if ext in _OLE_OFFICE_EXTS:
        return "ole"
    if ext in _PNG_EXTS:
        return "png"
    if ext in _JPEG_EXTS:
        return "jpeg"
    if ext in _GIF_EXTS:
        return "gif"
    return None


def verify_file_signature(path: str | Path, file_ext: str, *, head_bytes: int = 32) -> str | None:
    """Return a rejection reason when bytes contradict the extension, else None."""
    required = expected_kind(file_ext)
    try:
        with open(path, "rb") as handle:
            header = handle.read(head_bytes)
    except OSError:
        return "unreadable upload file"
    if not header:
        return "empty file"
    actual = sniff_kind(header)
    if required is not None:
        if actual == required:
            return None
        return f"file content does not match extension '{file_ext}'"
    # Unmapped (text-ish) extensions: only reject clear binary spoofs, e.g. an
    # xlsx renamed to .csv. Plain/UTF-16 text sniffs as "unknown" and passes.
    if actual != "unknown":
        return f"binary content does not match extension '{file_ext}'"
    return None


def check_office_zip_limits(
    path: str | Path,
    *,
    max_files: int = 2000,
    max_total_uncompressed_bytes: int = 500_000_000,
) -> str | None:
    """Zip-bomb guard for OOXML-style files (central directory only)."""
    try:
        with zipfile.ZipFile(path) as archive:
            members = archive.infolist()
    except zipfile.BadZipFile:
        return "unreadable office document container"
    except OSError:
        return "unreadable upload file"
    if len(members) > max(1, int(max_files or 0)):
        return f"office document has too many entries ({len(members)})"
    total = 0
    for member in members:
        total += max(0, int(getattr(member, "file_size", 0) or 0))
        if total > max_total_uncompressed_bytes:
            return "office document uncompressed size exceeds the allowed limit"
    return None


def screen_saved_upload(
    path: str | Path,
    file_ext: str,
    *,
    max_zip_files: int = 2000,
    max_zip_total_uncompressed_bytes: int = 500_000_000,
) -> str | None:
    """Run all content screens for an already-saved upload file."""
    reason = verify_file_signature(path, file_ext)
    if reason is not None:
        return reason
    if expected_kind(file_ext) == "zip":
        return check_office_zip_limits(
            path,
            max_files=max_zip_files,
            max_total_uncompressed_bytes=max_zip_total_uncompressed_bytes,
        )
    return None
