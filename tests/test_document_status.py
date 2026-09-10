"""P0: document status state machine (legal transitions + stamping).

Stdlib-only tests for ``app.services.document_status``.
"""

import importlib.util
import sys
from pathlib import Path
from types import SimpleNamespace

REPO = str(Path(__file__).resolve().parents[1])


def _load():
    name = "ordo_document_status"
    if name in sys.modules:
        return sys.modules[name]
    spec = importlib.util.spec_from_file_location(name, REPO + "/app/services/document_status.py")
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


ds = _load()


def _doc(status):
    return SimpleNamespace(
        status=status, current_stage=None, failed_stage=None, error_code=None, error_message=None
    )


def test_self_transitions_are_idempotent():
    for status in sorted(ds.DOCUMENT_STATUSES):
        doc = _doc(status)
        transition = ds.transition_document_status(doc, status)
        assert doc.status == status
        assert transition.from_status == transition.to_status == status


def test_happy_path_flow():
    doc = _doc("pending")
    ds.transition_document_status(doc, "processing", stage="parsing")
    assert (doc.status, doc.current_stage) == ("processing", "parsing")
    ds.transition_document_status(doc, "completed", stage="completed")
    assert doc.status == "completed"


def test_retry_and_delete_from_terminal_states():
    for terminal in ("completed", "failed", "cancelled"):
        assert ds.is_legal_transition(terminal, "processing") is True
        assert ds.is_legal_transition(terminal, "deleting") is True
        assert ds.is_legal_transition(terminal, "pending") is False


def test_deleting_is_a_sink():
    for target in ("pending", "processing", "completed", "failed", "cancelled", "quarantined"):
        assert ds.is_legal_transition("deleting", target) is False
    assert ds.is_legal_transition("deleting", "deleting") is True


def test_illegal_edges_raise():
    import pytest

    with pytest.raises(ds.IllegalDocumentStatusTransition):
        ds.transition_document_status(_doc("completed"), "pending")
    with pytest.raises(ds.IllegalDocumentStatusTransition):
        ds.transition_document_status(_doc("deleting"), "processing")
    with pytest.raises(ds.IllegalDocumentStatusTransition):
        ds.transition_document_status(_doc("bogus-state"), "pending")
    with pytest.raises(ds.IllegalDocumentStatusTransition):
        ds.transition_document_status(_doc("pending"), "bogus-state")


def test_failure_stamps_error_context():
    doc = _doc("processing")
    ds.transition_document_status(
        doc, "failed", stage="embedding", error_code="E_EMB", error_message="boom"
    )
    assert doc.failed_stage == "embedding"
    assert doc.error_code == "E_EMB"
    assert doc.error_message == "boom"
