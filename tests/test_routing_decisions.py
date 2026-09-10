"""P1: explainable parser/chunk routing decisions."""

import importlib.util
import sys
from pathlib import Path

REPO = str(Path(__file__).resolve().parents[1])


def _load(name, relpath):
    if name in sys.modules:
        return sys.modules[name]
    spec = importlib.util.spec_from_file_location(name, REPO + relpath)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


routing = _load("ordo_routing_decisions", "/app/parsing/routing_decisions.py")
chunk_routing = _load("ordo_chunk_routing_decisions", "/app/rag/chunking/routing_decisions.py")


def test_parser_decision_explicit_request_has_full_confidence():
    decision = routing.explain_pdf_routing("mineru", {"score": 0.2, "is_scanned": True}, "mineru", {"mineru": True})
    assert decision.selected_parser == "mineru"
    assert decision.confidence == 1.0
    assert decision.candidates[0] == "mineru"
    assert decision.fallback_parser != "mineru"
    assert decision.requires_ocr is True
    assert any("requested" in reason for reason in decision.reasons)


def test_parser_decision_scanned_and_high_quality_branches():
    scanned = routing.explain_pdf_routing("deepdoc", {"score": 0.3, "is_scanned": True}, "auto", {})
    assert scanned.requires_ocr is True
    assert 0.0 <= scanned.confidence <= 1.0
    clean = routing.explain_pdf_routing(
        "docling", {"score": 0.95, "is_scanned": False, "page_count": 12}, "auto", {"docling": True}
    )
    assert clean.confidence > 0.8
    assert any("page_count=12" in reason for reason in clean.reasons)
    trace = clean.to_trace()
    assert trace["schema"] == routing.SCHEMA_VERSION


def test_parser_decision_fallback_never_equals_selected():
    decision = routing.explain_pdf_routing("basic", {"score": 0.6}, None, {})
    assert decision.fallback_parser == "basic"
    assert decision.candidates == ("basic",)


def test_chunk_decision_records_and_warns():
    decision = chunk_routing.explain_chunk_routing(
        "laws_structured",
        detected_document_type="legal",
        confidence=0.62,
        reasons=["clause markers detected"],
        profile="auto",
    )
    assert decision.selected_strategy == "laws_structured"
    assert decision.confidence == 0.62
    assert decision.warnings == ()
    unknown = chunk_routing.explain_chunk_routing("recursive", detected_document_type="unknown")
    assert unknown.warnings != ()
    assert unknown.fallback_strategy == "langchain_recursive"
    assert unknown.to_trace()["schema"] == chunk_routing.SCHEMA_VERSION
