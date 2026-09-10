"""Explicit document processing state machine (P0 lifecycle).

Centralizes the legal ``Document.status`` transitions so background workers,
retries, cancels and deletes cannot silently move a document into an
impossible state (e.g. resurrecting a ``deleting`` document back to
``processing``).

Rules:
- transitions are idempotent (``X -> X`` always allowed);
- ``deleting`` is a sink: once entered, only ``deleting`` is legal until the
  row is removed (cleanup failures stay ``deleting`` for operator replay);
- terminal states (``completed``/``failed``/``cancelled``) may only move to
  ``processing`` (retry/re-ingest) or ``deleting``;
- unknown current states raise instead of guessing (fail-closed).

Stdlib-only and DB-free: operates on any object with attribute access, so it
is unit-testable without the backend dependency tree.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

PENDING = "pending"
PROCESSING = "processing"
COMPLETED = "completed"
FAILED = "failed"
QUARANTINED = "quarantined"
CANCELLED = "cancelled"
DELETING = "deleting"

DOCUMENT_STATUSES = frozenset(
    {PENDING, PROCESSING, COMPLETED, FAILED, QUARANTINED, CANCELLED, DELETING}
)

TERMINAL_STATUSES = frozenset({COMPLETED, FAILED, CANCELLED})

ALLOWED_TRANSITIONS: dict[str, frozenset[str]] = {
    PENDING: frozenset({PENDING, PROCESSING, CANCELLED, DELETING, QUARANTINED}),
    PROCESSING: frozenset({PROCESSING, COMPLETED, FAILED, CANCELLED, DELETING, QUARANTINED}),
    QUARANTINED: frozenset({QUARANTINED, PROCESSING, DELETING, CANCELLED}),
    COMPLETED: frozenset({COMPLETED, PROCESSING, DELETING}),
    FAILED: frozenset({FAILED, PROCESSING, DELETING, CANCELLED}),
    CANCELLED: frozenset({CANCELLED, PROCESSING, DELETING}),
    DELETING: frozenset({DELETING}),
}


class IllegalDocumentStatusTransition(ValueError):
    """Raised when a document status transition violates the state machine."""


def normalize_status(value: Any) -> str:
    return str(value or "").strip().lower()


def is_legal_transition(from_status: Any, to_status: Any) -> bool:
    src = normalize_status(from_status)
    dst = normalize_status(to_status)
    if src not in DOCUMENT_STATUSES or dst not in DOCUMENT_STATUSES:
        return False
    return dst in ALLOWED_TRANSITIONS[src]


@dataclass
class StatusTransition:
    from_status: str
    to_status: str
    stage: str | None = None


def transition_document_status(
    document: Any,
    to_status: str,
    *,
    stage: str | None = None,
    error_code: str | None = None,
    error_message: str | None = None,
) -> StatusTransition:
    """Move ``document.status`` to ``to_status`` after validating the edge.

    Also stamps ``current_stage`` (and ``failed_stage`` when entering
    ``failed``). Does not commit; callers own the transaction. Raises
    :class:`IllegalDocumentStatusTransition` on illegal or unknown states.
    """
    src = normalize_status(getattr(document, "status", None))
    dst = normalize_status(to_status)
    if src not in DOCUMENT_STATUSES:
        raise IllegalDocumentStatusTransition(f"unknown current document status: {src!r}")
    if dst not in DOCUMENT_STATUSES:
        raise IllegalDocumentStatusTransition(f"unknown target document status: {dst!r}")
    if dst not in ALLOWED_TRANSITIONS[src]:
        raise IllegalDocumentStatusTransition(
            f"illegal document status transition: {src!r} -> {dst!r}"
        )
    document.status = dst
    if stage is not None:
        document.current_stage = stage
    if dst == FAILED:
        document.failed_stage = stage
        if error_code is not None:
            document.error_code = error_code
        if error_message is not None:
            document.error_message = error_message
    return StatusTransition(from_status=src, to_status=dst, stage=stage)
