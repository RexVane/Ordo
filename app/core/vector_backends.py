"""Vector backend capability metadata.

This module is intentionally dependency-light: it is imported by settings
validation, health checks, and the vector-store factory without importing any
vector database client.
"""

from typing import Final

SUPPORTED_VECTOR_BACKENDS: Final[frozenset[str]] = frozenset(
    {
        "milvus",
        "memory",
        "faiss",
        "chroma",
    }
)

# Backends whose vectors live only in process memory. They are useful for
# tests and throwaway local runs, but must not be mistaken for durable storage.
EPHEMERAL_VECTOR_BACKENDS: Final[frozenset[str]] = frozenset({"memory"})


def normalize_vector_backend(value: object, *, default: str = "milvus") -> str:
    """Return a lower-case backend name, falling back to ``default``."""
    raw = str(value or "").strip().lower()
    return raw or default


def validate_vector_backend(value: object) -> str:
    """Validate a backend name and return its normalized form.

    Raises:
        ValueError: when the backend is unknown or only a placeholder.
    """
    backend = normalize_vector_backend(value)
    if backend not in SUPPORTED_VECTOR_BACKENDS:
        supported = ", ".join(sorted(SUPPORTED_VECTOR_BACKENDS))
        raise ValueError(f"Unsupported VECTOR_BACKEND '{backend}'. Supported backends: {supported}")
    return backend


def vector_store_persistence(value: object) -> str:
    """Return ``persistent`` or ``ephemeral`` for a backend name."""
    backend = normalize_vector_backend(value)
    return "ephemeral" if backend in EPHEMERAL_VECTOR_BACKENDS else "persistent"


__all__ = [
    "EPHEMERAL_VECTOR_BACKENDS",
    "SUPPORTED_VECTOR_BACKENDS",
    "normalize_vector_backend",
    "validate_vector_backend",
    "vector_store_persistence",
]
