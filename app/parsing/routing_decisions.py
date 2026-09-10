"""Explainable parser-routing decisions (P1 parsing scaffolding).

:func:`explain_pdf_routing` derives candidates, confidence, reasons and a
fallback from the **already-chosen** backend plus the same quality signals
the router used — it never re-implements selection rules, so it cannot drift
from :func:`app.parsing.routing.choose_pdf_backend`.

Stdlib-only, no app imports.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

SCHEMA_VERSION = "ordo.parsing.routing_decision.v1"


@dataclass(frozen=True)
class ParserRoutingDecision:
    """Why a parser backend was selected for one document."""

    schema_version: str = SCHEMA_VERSION
    selected_parser: str = ""
    candidates: tuple[str, ...] = ()
    confidence: float = 0.0
    reasons: tuple[str, ...] = ()
    fallback_parser: str = ""
    estimated_cost: str = "unknown"
    timeout_sec: int = 0
    requires_ocr: bool = False
    requires_gpu: bool = False

    def to_trace(self) -> dict[str, Any]:
        return {
            "schema": self.schema_version,
            "selected_parser": self.selected_parser,
            "candidates": list(self.candidates),
            "confidence": self.confidence,
            "reasons": list(self.reasons),
            "fallback_parser": self.fallback_parser,
            "estimated_cost": self.estimated_cost,
            "requires_ocr": self.requires_ocr,
            "requires_gpu": self.requires_gpu,
        }


_HEAVY_OCR_BACKENDS = frozenset({"mineru", "deepseek_ocr", "qianfan_ocr", "olmocr", "paddlevl", "marker"})
_GPU_BACKENDS = frozenset({"docling-gpu", "mineru", "olmocr", "paddlevl", "magicpdf"})


def _clamp_confidence(value: float) -> float:
    return max(0.0, min(1.0, float(value or 0.0)))


def explain_pdf_routing(
    selected: str,
    quality: dict[str, Any] | None,
    requested: str | None,
    availability: dict[str, bool] | None,
) -> ParserRoutingDecision:
    """Build an explainable decision for an already-routed PDF backend."""
    quality = dict(quality or {})
    availability = dict(availability or {})
    selected_norm = str(selected or "").strip().lower() or "auto"
    requested_norm = str(requested or "").strip().lower()

    score = float(quality.get("score", 0.0) or 0.0)
    is_scanned = bool(quality.get("is_scanned", False))
    page_count = quality.get("page_count")

    reasons: list[str] = []
    if requested_norm and requested_norm != "auto":
        reasons.append(f"explicitly requested backend: {requested_norm}")
        confidence = 1.0
    elif is_scanned:
        reasons.append("scan detected: OCR-capable backend preferred")
        confidence = 0.55 + 0.3 * score
    elif score >= 0.8:
        reasons.append(f"high text quality (score={score:.2f}): structure-preserving backend preferred")
        confidence = 0.6 + 0.35 * score
    elif score <= 0.5:
        reasons.append(f"low text quality (score={score:.2f}): OCR/robust backend preferred")
        confidence = 0.5 + 0.3 * (1.0 - score)
    else:
        reasons.append(f"mid text quality (score={score:.2f}): balanced backend preferred")
        confidence = 0.6
    if page_count:
        reasons.append(f"page_count={page_count}")

    available = [name for name, ok in availability.items() if ok]
    candidates = tuple([selected_norm] + [name for name in available if name != selected_norm])
    fallback = next((name for name in available if name != selected_norm), "basic")
    if fallback == selected_norm:
        fallback = "basic"

    return ParserRoutingDecision(
        selected_parser=selected_norm,
        candidates=candidates,
        confidence=_clamp_confidence(confidence),
        reasons=tuple(reasons),
        fallback_parser=fallback,
        estimated_cost="high" if selected_norm in _HEAVY_OCR_BACKENDS else "standard",
        requires_ocr=is_scanned or selected_norm in _HEAVY_OCR_BACKENDS,
        requires_gpu=selected_norm in _GPU_BACKENDS,
    )
