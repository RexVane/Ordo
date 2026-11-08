"""
PDF parser based on pdfplumber / pypdfium2.

The default distribution must not depend on PyMuPDF (AGPL-3.0). pdfplumber
already provides text extraction, coordinates, embedded images, and page
rendering (through its pypdfium2 dependency), so the basic parser can stay
dependency-light and Apache-2.0 compatible.
"""

from io import BytesIO
from pathlib import Path
from typing import Any

import pdfplumber
from langchain_core.documents import Document
from PIL import Image as PILImage

from app.core.constants import NON_CRITICAL_EXCEPTION_LOG_MESSAGE
from app.parsing.enrich.image_understanding import decode_image_codes, infer_visual_kind_from_pixels
from app.rag.core.logging import get_logger


class PDFParser:
    """PDF document parser backed by pdfplumber."""

    def _position_tagged_text(self, *, page: Any, page_num: int) -> str:
        blocks: list[str] = []
        for line in page.extract_text_lines(return_chars=False) or []:
            try:
                text = str(line.get("text") or "").strip()
                if not text:
                    continue
                x0 = float(line.get("x0") or 0.0)
                x1 = float(line.get("x1") or 0.0)
                top = float(line.get("top") or 0.0)
                bottom = float(line.get("bottom") or 0.0)
            except Exception:
                get_logger(__name__).debug(NON_CRITICAL_EXCEPTION_LOG_MESSAGE, exc_info=True)
                continue
            blocks.append(f"{text}@@{int(page_num) + 1}\t{x0:.1f}\t{x1:.1f}\t{top:.1f}\t{bottom:.1f}##")
        return "\n\n".join(blocks).strip()

    def _extract_table_signature(self, text: str) -> tuple[str, list[str]] | None:
        lines = [line.strip() for line in str(text or "").splitlines() if line.strip()]
        for index in range(len(lines) - 1):
            header = lines[index]
            separator = lines[index + 1]
            if "|" not in header or "|" not in separator:
                continue
            separator_cells = [cell.strip() for cell in separator.strip().strip("|").split("|")]
            if not separator_cells or not all(
                cell and set(cell) <= {"-", ":", " "} and cell.count("-") >= 3
                for cell in separator_cells
            ):
                continue
            columns = [cell.strip() for cell in header.strip().strip("|").split("|") if cell.strip()]
            if not columns:
                continue
            return header.strip(), columns
        return None

    def _classify_text_page(self, text: str) -> dict[str, Any]:
        table_signature = self._extract_table_signature(text)
        if table_signature is not None:
            header, columns = table_signature
            return {
                "doc_type_kwd": "table",
                "content_type": "table",
                "table_header_present": True,
                "table_header_text": header,
                "table_columns": columns,
            }
        return {}

    def _extract_image_payload(self, *, image_info: dict[str, Any]) -> bytes | None:
        try:
            stream = image_info.get("stream")
            if stream is None:
                return None
            payload = stream.get_data()
        except Exception:
            get_logger(__name__).debug(NON_CRITICAL_EXCEPTION_LOG_MESSAGE, exc_info=True)
            return None
        if not isinstance(payload, (bytes, bytearray)) or not payload:
            return None
        return bytes(payload)

    def _load_rgb_image(self, image_bytes: bytes):  # noqa: ANN001
        try:
            with PILImage.open(BytesIO(image_bytes)) as raw_image:
                return raw_image.convert("RGB")
        except Exception:
            get_logger(__name__).debug(NON_CRITICAL_EXCEPTION_LOG_MESSAGE, exc_info=True)
            return None

    def _decode_image_details(self, image) -> tuple[str, str, list[str]]:  # noqa: ANN001
        code_info = decode_image_codes(image)
        visual_kind = str(code_info.get("visual_kind") or "").strip().lower() if isinstance(code_info, dict) else ""
        if not visual_kind:
            visual_kind = str(infer_visual_kind_from_pixels(image) or "").strip().lower()

        code_text = str(code_info.get("text") or "").strip() if isinstance(code_info, dict) else ""
        code_values: list[str] = []
        if isinstance(code_info, dict):
            raw_values = code_info.get("values")
            if isinstance(raw_values, list):
                code_values = [str(item).strip() for item in raw_values if str(item).strip()]

        return visual_kind, code_text, code_values

    def _build_image_document(
        self,
        *,
        file_path: Path,
        page_num: int,
        total_pages: int,
        image,
        image_index: int,
        visual_kind: str,
        code_text: str,
        code_values: list[str],
    ) -> Document:
        metadata = {
            "source": str(file_path.name),
            "page": page_num + 1,
            "total_pages": total_pages,
            "file_type": "pdf",
            "doc_type_kwd": "image",
            "content_type": "image",
            "image": image,
            "image_index": image_index,
        }
        if visual_kind:
            metadata["visual_kind"] = visual_kind
        if code_text:
            metadata["image_code_text"] = code_text
        if code_values:
            metadata["image_code_values"] = code_values

        page_content = code_text or (f"{visual_kind} image" if visual_kind else "")
        return Document(page_content=page_content, metadata=metadata)

    def _extract_image_documents(self, *, page: Any, file_path: Path, page_num: int, total_pages: int) -> list[Document]:
        documents: list[Document] = []
        seen_images: set[tuple[str, tuple[int, int] | None]] = set()
        try:
            images = list(page.images or [])
        except Exception:
            get_logger(__name__).debug(NON_CRITICAL_EXCEPTION_LOG_MESSAGE, exc_info=True)
            images = []
        for image_index, image_info in enumerate(images):
            name = str(image_info.get("name") or "").strip()
            srcsize = image_info.get("srcsize")
            srcsize_key = tuple(srcsize) if isinstance(srcsize, (tuple, list)) and len(srcsize) == 2 else None
            dedupe_key = (name, srcsize_key)
            if dedupe_key in seen_images:
                continue
            seen_images.add(dedupe_key)

            image_bytes = self._extract_image_payload(image_info=image_info)
            if image_bytes is None:
                continue
            image = self._load_rgb_image(image_bytes)
            if image is None:
                continue

            visual_kind, code_text, code_values = self._decode_image_details(image)
            documents.append(
                self._build_image_document(
                    file_path=file_path,
                    page_num=page_num,
                    total_pages=total_pages,
                    image=image,
                    image_index=image_index,
                    visual_kind=visual_kind,
                    code_text=code_text,
                    code_values=code_values,
                )
            )

        if documents:
            return documents

        # Some image-only PDFs use filters that pdfplumber cannot decode into a
        # standalone image. Render the page instead so the visual content is not
        # silently dropped.
        try:
            rendered = page.to_image(resolution=150).original
        except Exception:
            get_logger(__name__).debug(NON_CRITICAL_EXCEPTION_LOG_MESSAGE, exc_info=True)
            return documents
        if not isinstance(rendered, PILImage.Image):
            return documents
        image = rendered.convert("RGB")
        visual_kind, code_text, code_values = self._decode_image_details(image)
        documents.append(
            self._build_image_document(
                file_path=file_path,
                page_num=page_num,
                total_pages=total_pages,
                image=image,
                image_index=0,
                visual_kind=visual_kind,
                code_text=code_text,
                code_values=code_values,
            )
        )
        return documents

    def parse(self, file_path: Path) -> list[Document]:
        """Parse a PDF into a list of LangChain Documents."""
        path = Path(file_path)
        documents: list[Document] = []
        previous_table_signature: tuple[str, list[str]] | None = None

        with pdfplumber.open(path) as pdf:
            total_pages = len(pdf.pages)
            for page_num, page in enumerate(pdf.pages):
                text = page.extract_text() or ""
                tagged_text = self._position_tagged_text(page=page, page_num=page_num)

                # Image-only pages still carry valuable visual content.
                if not text.strip():
                    documents.extend(
                        self._extract_image_documents(
                            page=page,
                            file_path=path,
                            page_num=page_num,
                            total_pages=total_pages,
                        )
                    )
                    continue

                metadata = {
                    "source": str(path.name),
                    "page": page_num + 1,
                    "total_pages": total_pages,
                    "file_type": "pdf",
                }
                metadata.update(self._classify_text_page(text))
                current_signature = None
                if str(metadata.get("doc_type_kwd") or "").strip().lower() == "table":
                    header_text = str(metadata.get("table_header_text") or "").strip()
                    table_columns = list(metadata.get("table_columns") or [])
                    current_signature = (header_text, table_columns)
                    if previous_table_signature == current_signature and documents:
                        metadata["table_continued"] = True
                        prev_meta = documents[-1].metadata if isinstance(documents[-1].metadata, dict) else None
                        if isinstance(prev_meta, dict):
                            prev_meta["table_truncated"] = True
                            prev_meta["truncated"] = True
                previous_table_signature = current_signature

                documents.append(
                    Document(
                        page_content=tagged_text or text,
                        metadata=metadata,
                    )
                )

        return documents
