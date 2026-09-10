"""Explainable chunk-routing decisions (P1 chunking scaffolding).

:func:`explain_chunk_routing` records **why** a chunking strategy was chosen
for one document: the selected strategy, detector confidence, detected
document type, reasons, fallback and profile. It takes the already-made
selection as input, so it cannot diverge from the actual router.

Stdlib-only, no app imports.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

SCHEMA_VERSION = "ordo.chunking.routing_decision.v1"


@dataclass(frozen=True)
class ChunkRoutingDecision:
    """Why a chunking strategy was selected for one document."""

    schema_version: str = SCHEMA_VERSION
    selected_strategy: str = ""
    confidence: float = 0.0
    detected_document_type: str = "unknown"
    reasons: tuple[str, ...] = ()
    fallback_strategy: str = "langchain_recursive"
    profile: str = "auto"
    warnings: tuple[str, ...] = ()

    def to_trace(self) -> dict[str, Any]:
        return {
            "schema": self.schema_version,
            "selected_strategy": self.selected_strategy,
            "confidence": self.confidence,
            "detected_document_type": self.detected_document_type,
            "reasons": list(self.reasons),
            "fallback_strategy": self.fallback_strategy,
            "profile": self.profile,
            "warnings": list(self.warnings),
        }


def _clamp_confidence(value: float) -> float:
    return max(0.0, min(1.0, float(value or 0.0)))


def explain_chunk_routing(
    selected_strategy: str,
    *,
    detected_document_type: str = "unknown",
    confidence: float = 0.0,
    reasons: list[str] | tuple[str, ...] = (),
    fallback_strategy: str = "langchain_recursive",
    profile: str = "auto",
    warnings: list[str] | tuple[str, ...] = (),
) -> ChunkRoutingDecision:
    """Build an explainable record for an already-made chunking choice."""
    selected = str(selected_strategy or "").strip().lower() or "langchain_recursive"
    warns = list(warnings)
    if str(detected_document_type or "").strip().lower() in {"unknown", ""}:
        warns.append("low detector confidence: using fallback-compatible strategy")
    return ChunkRoutingDecision(
        selected_strategy=selected,
        confidence=_clamp_confidence(confidence),
        detected_document_type=str(detected_document_type or "unknown").strip().lower() or "unknown",
        reasons=tuple(str(r) for r in (reasons or ())),
        fallback_strategy=str(fallback_strategy or "langchain_recursive").strip().lower(),
        profile=str(profile or "auto").strip().lower(),
        warnings=tuple(str(w) for w in warns),
    )
