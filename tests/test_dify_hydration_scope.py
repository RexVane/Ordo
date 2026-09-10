"""P0: Dify chunk-hydration dataset scoping.

``_load_chunk_content_map`` must not become a tenant-wide chunk oracle:
when the caller passes ``dataset_ids``, chunks outside that scope are
excluded even if their ids are cited. Without scope it keeps the legacy
tenant-only behavior (backward compatible).
"""

from sqlalchemy import create_engine
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.ext.compiler import compiles
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.api.v1.integrations_dify import _load_chunk_content_map
from app.core.database import Base
from app.models.dataset import Dataset
from app.models.document import Document, DocumentChunk
from app.models.tenant import Tenant


@compiles(JSONB, "sqlite")
def _jsonb_as_json(element, compiler, **kwargs):
    from sqlalchemy import JSON

    return compiler.process(JSON(), **kwargs)


def _build_session():
    engine = create_engine(
        "sqlite+pysqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(
        engine,
        tables=[Tenant.__table__, Dataset.__table__, Document.__table__, DocumentChunk.__table__],
    )
    return sessionmaker(bind=engine)()


def _seed(db):
    tenant = Tenant(name="t-scope")
    db.add(tenant)
    db.flush()
    ds_a = Dataset(tenant_id=tenant.id, name="ds-a")
    ds_b = Dataset(tenant_id=tenant.id, name="ds-b")
    db.add_all([ds_a, ds_b])
    db.flush()
    doc_a = Document(
        tenant_id=tenant.id,
        dataset_id=ds_a.id,
        filename="a.txt",
        file_type="txt",
        file_size=10,
        file_path="/tmp/a.txt",
    )
    doc_b = Document(
        tenant_id=tenant.id,
        dataset_id=ds_b.id,
        filename="b.txt",
        file_type="txt",
        file_size=10,
        file_path="/tmp/b.txt",
    )
    db.add_all([doc_a, doc_b])
    db.flush()
    chunk_a = DocumentChunk(tenant_id=tenant.id, document_id=doc_a.id, chunk_index=0, content="alpha")
    chunk_b = DocumentChunk(tenant_id=tenant.id, document_id=doc_b.id, chunk_index=0, content="beta")
    db.add_all([chunk_a, chunk_b])
    db.commit()
    return tenant, ds_a, ds_b, chunk_a, chunk_b


def test_hydration_excludes_out_of_scope_chunks():
    db = _build_session()
    try:
        tenant, ds_a, _ds_b, chunk_a, chunk_b = _seed(db)
        citations = [{"chunk_id": str(chunk_a.id)}, {"chunk_id": str(chunk_b.id)}]
        scoped = _load_chunk_content_map(
            db=db, tenant_id=tenant.id, citations=citations, dataset_ids=[ds_a.id]
        )
        assert set(scoped) == {str(chunk_a.id)}
        assert scoped[str(chunk_a.id)] == "alpha"
    finally:
        db.close()


def test_hydration_without_scope_keeps_legacy_behavior():
    db = _build_session()
    try:
        tenant, _ds_a, _ds_b, chunk_a, chunk_b = _seed(db)
        citations = [{"chunk_id": str(chunk_a.id)}, {"chunk_id": str(chunk_b.id)}]
        full = _load_chunk_content_map(db=db, tenant_id=tenant.id, citations=citations)
        assert set(full) == {str(chunk_a.id), str(chunk_b.id)}
    finally:
        db.close()


def test_hydration_skips_unknown_chunk_ids():
    db = _build_session()
    try:
        tenant, ds_a, _ds_b, chunk_a, _chunk_b = _seed(db)
        citations = [
            {"chunk_id": str(chunk_a.id)},
            {"chunk_id": "00000000-0000-0000-0000-000000000000"},
            {"chunk_id": "not-a-uuid"},
            {},
        ]
        scoped = _load_chunk_content_map(
            db=db, tenant_id=tenant.id, citations=citations, dataset_ids=[ds_a.id]
        )
        assert set(scoped) == {str(chunk_a.id)}
    finally:
        db.close()
