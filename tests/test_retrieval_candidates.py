"""P1: unified retrieval Candidate contracts (stages keep separate scores)."""

import importlib.util
import sys
from pathlib import Path

REPO = str(Path(__file__).resolve().parents[1])


def _load():
    name = "ordo_retrieval_candidates"
    if name in sys.modules:
        return sys.modules[name]
    spec = importlib.util.spec_from_file_location(
        name, REPO + "/app/rag/retrieval/candidates.py"
    )
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


contracts = _load()


def test_legacy_score_maps_to_raw_and_final_without_merging():
    candidate = contracts.candidate_from_legacy_dict(
        {
            "document_id": "d1",
            "chunk_id": "c1",
            "score": 0.7,
            "source_channel": "vector",
            "source_rank": 2,
        }
    )
    assert candidate.candidate_id == "d1:c1"
    assert candidate.raw_score == 0.7
    assert candidate.final_score == 0.7
    assert candidate.fusion_score is None
    assert candidate.rerank_score is None


def test_per_stage_scores_stay_separate_and_explainable():
    candidate = contracts.candidate_from_legacy_dict(
        {
            "candidate_id": "k",
            "score": 0.9,
            "fusion_score": 0.5,
            "rerank_score": 0.8,
            "tenant_id": "t",
            "acl_decision": "allow",
            "index_revision": "r3",
            "trace_id": "trace-1",
        }
    )
    breakdown = candidate.score_breakdown()
    assert (breakdown["fusion_score"], breakdown["rerank_score"], breakdown["final_score"]) == (0.5, 0.8, 0.9)
    assert candidate.acl_decision == "allow"


def test_round_trip_preserves_unknown_evidence():
    legacy = {"document_id": "d", "chunk_id": "c", "score": 0.1, "custom_flag": True}
    back = contracts.candidate_to_legacy_dict(contracts.candidate_from_legacy_dict(legacy))
    assert back["score"] == 0.1
    assert back["metadata"]["legacy:custom_flag"] is True
    assert back["score_breakdown"]["schema"] == contracts.SCHEMA_VERSION


def test_execution_context_defaults_are_typed():
    ctx = contracts.RetrievalExecutionContext()
    assert ctx.schema_version == contracts.SCHEMA_VERSION
    assert ctx.fused_candidates == []
    assert ctx.channel_results == {}


def test_rejects_non_mapping_and_unknown_states():
    import pytest

    with pytest.raises(TypeError):
        contracts.candidate_from_legacy_dict(["not", "a", "dict"])
