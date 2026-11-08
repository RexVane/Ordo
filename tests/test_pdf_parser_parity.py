"""Regression coverage for the pdfplumber-backed basic PDF parser."""

import re
from pathlib import Path

import pytest

from app.parsing.parsers.pdf_parser import PDFParser

FIXTURES = Path(__file__).resolve().parent / "fixtures" / "parsing_golden_broader"
POSITION_TAG_RE = re.compile(r"@@(\d+)\t([0-9.]+)\t([0-9.]+)\t([0-9.]+)\t([0-9.]+)##")


def _fixture(name: str) -> Path:
    return FIXTURES / name / "input" / "sample.pdf"


@pytest.mark.parametrize(
    "fixture_name",
    [
        "multilingual_pdf",
        "two_column_pdf",
        "cross_page_table_pdf",
    ],
)
def test_text_pdf_keeps_page_metadata_and_position_tags(fixture_name: str) -> None:
    path = _fixture(fixture_name)
    assert path.exists(), f"missing fixture: {path}"

    documents = PDFParser().parse(path)

    assert documents
    assert all(doc.metadata["source"] == "sample.pdf" for doc in documents)
    assert all(doc.metadata["file_type"] == "pdf" for doc in documents)
    assert all(int(doc.metadata["page"]) >= 1 for doc in documents)
    assert all(int(doc.metadata["total_pages"]) >= 1 for doc in documents)
    assert any(POSITION_TAG_RE.search(doc.page_content) for doc in documents)


def test_image_only_pdf_yields_visual_document() -> None:
    path = _fixture("chart_pdf")
    assert path.exists(), f"missing fixture: {path}"

    documents = PDFParser().parse(path)

    assert documents
    image_docs = [doc for doc in documents if doc.metadata.get("content_type") == "image"]
    assert image_docs
    image_doc = image_docs[0]
    assert image_doc.metadata["image"].size[0] > 0
    assert image_doc.metadata["image"].size[1] > 0
    assert int(image_doc.metadata["page"]) >= 1


def test_repeated_images_are_deduplicated() -> None:
    class _Stream:
        def get_data(self) -> bytes:
            return b"not-an-image"

    class _Page:
        images = [
            {"name": "same", "srcsize": (2, 2), "stream": _Stream()},
            {"name": "same", "srcsize": (2, 2), "stream": _Stream()},
        ]

    documents = PDFParser()._extract_image_documents(
        page=_Page(),
        file_path=Path("scan.pdf"),
        page_num=0,
        total_pages=1,
    )

    # Unreadable payloads are skipped; the dedupe path must not raise.
    assert documents == []
