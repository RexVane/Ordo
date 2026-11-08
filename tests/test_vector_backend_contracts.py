"""Contracts for the supported vector backends.

These tests protect against a regression where placeholder backends
(qdrant/pgvector) silently accepted writes and lost all vectors on restart.
"""

from types import SimpleNamespace

import pytest

from app.core import config_validation
from app.core.vector_backends import (
    EPHEMERAL_VECTOR_BACKENDS,
    SUPPORTED_VECTOR_BACKENDS,
    validate_vector_backend,
    vector_store_persistence,
)
from app.storage.vector import factory as factory_module


def test_supported_backends_are_explicit() -> None:
    assert SUPPORTED_VECTOR_BACKENDS == {"milvus", "memory", "faiss", "chroma"}
    assert EPHEMERAL_VECTOR_BACKENDS == {"memory"}


def test_normalize_and_validate_backend() -> None:
    assert validate_vector_backend(" MILVUS ") == "milvus"
    assert validate_vector_backend("chroma") == "chroma"


@pytest.mark.parametrize("backend", ["qdrant", "pgvector", "bogus"])
def test_unknown_backend_is_rejected(backend: str) -> None:
    with pytest.raises(ValueError, match="Unsupported VECTOR_BACKEND"):
        validate_vector_backend(backend)


def test_persistence_metadata() -> None:
    assert vector_store_persistence("memory") == "ephemeral"
    assert vector_store_persistence("milvus") == "persistent"
    assert vector_store_persistence("faiss") == "persistent"


@pytest.mark.parametrize("backend", ["qdrant", "pgvector"])
def test_factory_rejects_placeholder_backends(backend: str) -> None:
    with pytest.raises(ValueError, match="Unsupported VECTOR_BACKEND"):
        factory_module.get_vector_store(backend=backend)


def test_region_map_cannot_bypass_validation(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        factory_module,
        "_load_vector_region_backends",
        lambda: {"cn": "qdrant"},
    )
    with pytest.raises(ValueError, match="Unsupported VECTOR_BACKEND"):
        factory_module._resolve_vector_backend(region="cn")


def test_region_map_cannot_select_memory_in_production(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(factory_module, "is_production_env", lambda: True)
    monkeypatch.setattr(
        factory_module,
        "_load_vector_region_backends",
        lambda: {"cn": "memory"},
    )
    with pytest.raises(ValueError, match="ephemeral and is not allowed in production"):
        factory_module._resolve_vector_backend(region="cn")


def test_production_rejects_memory_backend(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(config_validation, "is_production_env", lambda: True)
    with pytest.raises(ValueError, match="VECTOR_BACKEND=memory is not allowed in production"):
        config_validation.validate_vector_write_and_table_catalog(SimpleNamespace(VECTOR_BACKEND="memory"))


def test_memory_store_is_marked_ephemeral(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(factory_module.settings, "VECTOR_BACKEND", "memory", raising=False)
    store = factory_module.MemoryVectorStore()
    assert store.persistence == "ephemeral"


def test_factory_singleton_uses_backend_persistence(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(factory_module.settings, "VECTOR_BACKEND", "memory", raising=False)
    factory_module.reset_vector_store_singletons()
    store = factory_module.get_vector_store()
    assert store.persistence == "ephemeral"
    assert factory_module.get_vector_store() is store
    factory_module.reset_vector_store_singletons()
