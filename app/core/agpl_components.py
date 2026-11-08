"""Optional AGPL-licensed components.

PyMuPDF is dual-licensed under AGPL-3.0 and a commercial license. It is not
installed by the default Ordo image; deployments that explicitly accept the
AGPL obligations can install ``requirements-agpl.txt``.

Importing this module is safe: the actual ``fitz`` import happens only when an
optional feature is used.
"""

from typing import Any

_PYMUPDF_MODULE: Any | None = None


def load_pymupdf() -> Any:
    """Return the ``fitz`` module or raise a license-aware error."""
    global _PYMUPDF_MODULE
    if _PYMUPDF_MODULE is not None:
        return _PYMUPDF_MODULE
    try:
        import fitz  # type: ignore[import-not-found]
    except Exception as exc:  # noqa: BLE001
        raise RuntimeError(
            "This feature requires PyMuPDF, which is an optional AGPL-3.0 component. "
            "Install requirements-agpl.txt and enable the AGPL extra only if you accept "
            "the AGPL-3.0 obligations."
        ) from exc
    _PYMUPDF_MODULE = fitz
    return fitz


class _LazyPyMuPDF:
    """Attribute proxy that keeps ``fitz`` optional at import time."""

    def __getattr__(self, name: str) -> Any:
        return getattr(load_pymupdf(), name)


def lazy_pymupdf() -> Any:
    """Return a proxy compatible with ``import fitz`` usage."""
    return _LazyPyMuPDF()


__all__ = ["lazy_pymupdf", "load_pymupdf"]
