"""Unified retrieval contracts (P1 core-architecture scaffolding).

The hybrid retrieval pipeline grew stage by stage; each stage historically
passed around plain dicts with a single overloaded ``score`` key. This module
defines the typed contracts the pipeline converges on:

- :class:`Candidate`: one retrieval candidate with **per-stage scores kept
  separate** (raw / normalized / fusion / rerank / final) plus provenance
  (channel, ranks, ACL decision, index/embedding revisions, trace id).
- :class:`RetrievalExecutionContext`: typed slots for every pipeline stage,
  replacing ad-hoc ``state`` dict keys for new code.
- :func:`candidate_from_legacy_dict` / :func:`candidate_to_legacy_dict`:
  lossless adapters so existing dict-based stages interoperate without a
  flag-day rewrite (explicit compatibility layer per project policy).

Stdlib-only and import-light: no app-internal imports, unit-testable anywhere.
``SCHEMA_VERSION`` must be bumped whenever fields change incompatibly.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any

SCHEMA_VERSION = "ordo.retrieval.candidate.v1"


@dataclass(frozen=True)
class Candidate:
    """One retrieval candidate with separated per-stage scores and provenance."""

    candidate_id: str
    tenant_id: str = ""
    dataset_id: str = ""
    document_id: str = ""
    document_version_id: str = ""
    chunk_id: str = ""
    embedding_space_hash: str = ""
    source_channel: str = ""
    source_rank: int = 0
    raw_score: float = 0.0
    normalized_score: float | None = None
    fusion_score: float | None = None
    rerank_score: float | None = None
    final_score: float = 0.0
    matched_terms: tuple[str, ...] = ()
    metadata: dict[str, Any] = field(default_factory=dict)
    acl_decision: str = "unknown"
    index_revision: str = ""
    trace_id: str = ""

    def score_breakdown(self) -> dict[str, Any]:
        """Explainable per-stage scores (never overwrites across stages)."""
        return {
            "schema": SCHEMA_VERSION,
            "raw_score": self.raw_score,
            "normalized_score": self.normalized_score,
            "fusion_score": self.fusion_score,
            "rerank_score": self.rerank_score,
            "final_score": self.final_score,
            "source_channel": self.source_channel,
            "source_rank": self.source_rank,
        }


def candidate_from_legacy_dict(raw: dict[str, Any]) -> Candidate:
    """Adapt a legacy stage dict into a typed Candidate (lossless for known keys)."""
    if not isinstance(raw, dict):
        raise TypeError("candidate payload must be a mapping")
    data = dict(raw)
    legacy_score = data.pop("score", None)
    matched = data.pop("matched_terms", ())
    metadata = data.pop("metadata", {})
    known = {f for f in Candidate.__dataclass_fields__}
    cleaned = {key: data[key] for key in known.intersection(data) if key != "candidate_id"}
    candidate_id = str(
        data.get("candidate_id")
        or data.get("id")
        or f"{data.get('document_id', '')}:{data.get('chunk_id', '')}"
    )
    candidate = Candidate(
        candidate_id=candidate_id,
        tenant_id=str(cleaned.pop("tenant_id", "") or ""),
        dataset_id=str(cleaned.pop("dataset_id", "") or ""),
        document_id=str(cleaned.pop("document_id", "") or ""),
        document_version_id=str(cleaned.pop("document_version_id", "") or ""),
        chunk_id=str(cleaned.pop("chunk_id", "") or ""),
        embedding_space_hash=str(cleaned.pop("embedding_space_hash", "") or ""),
        source_channel=str(cleaned.pop("source_channel", "") or ""),
        source_rank=int(cleaned.pop("source_rank", 0) or 0),
        raw_score=float(cleaned.pop("raw_score", legacy_score if legacy_score is not None else 0.0) or 0.0),
        final_score=float(cleaned.pop("final_score", legacy_score if legacy_score is not None else 0.0) or 0.0),
        matched_terms=tuple(str(term) for term in (matched or ())),
        metadata=dict(metadata) if isinstance(metadata, dict) else {},
        acl_decision=str(cleaned.pop("acl_decision", "unknown") or "unknown"),
        index_revision=str(cleaned.pop("index_revision", "") or ""),
        trace_id=str(cleaned.pop("trace_id", "") or ""),
    )
    # Carry optional per-stage scores when present.
    for stage_key in ("normalized_score", "fusion_score", "rerank_score"):
        if stage_key in data and data[stage_key] is not None:
            object.__setattr__(candidate, stage_key, float(data[stage_key]))
    # Preserve unknown keys inside metadata instead of dropping evidence.
    for key, value in data.items():
        if key not in known and key not in ("id", "score"):
            candidate.metadata.setdefault(f"legacy:{key}", value)
    return candidate


def candidate_to_legacy_dict(candidate: Candidate) -> dict[str, Any]:
    """Adapt a typed Candidate back to the legacy stage-dict shape."""
    payload = asdict(candidate)
    payload["matched_terms"] = list(payload["matched_terms"])
    # Legacy readers expect a single `score`: expose final_score, keep the
    # full breakdown alongside so no stage information is lost.
    payload["score"] = candidate.final_score
    payload["score_breakdown"] = candidate.score_breakdown()
    return payload


@dataclass
class RetrievalExecutionContext:
    """Typed slots for every retrieval pipeline stage (replaces ad-hoc keys)."""

    schema_version: str = SCHEMA_VERSION
    request: dict[str, Any] = field(default_factory=dict)
    scope: dict[str, Any] = field(default_factory=dict)
    plan: dict[str, Any] = field(default_factory=dict)
    channel_results: dict[str, list[Candidate]] = field(default_factory=dict)
    fused_candidates: list[Candidate] = field(default_factory=list)
    reranked_candidates: list[Candidate] = field(default_factory=list)
    evidence: list[dict[str, Any]] = field(default_factory=list)
    diagnostics: dict[str, Any] = field(default_factory=dict)
