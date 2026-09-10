"""P0: login failure lockout (fail-closed brute-force protection).

Endpoint-level regression tests using the same sqlite + TestClient harness as
``test_auth_local_account_flow.py``:

- N consecutive wrong passwords lock the account (correct password then 403);
- a successful login before the threshold resets the counter;
- an expired lock no longer blocks login;
- unknown identifiers still return 401 without side effects.
"""

from uuid import uuid4

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

import app.api.v1.auth as auth_module
from app.core.config import settings
from app.core.database import Base
from app.models.tenant import Tenant, TenantMember
from app.models.user import User
from app.services.user_service import UserService

PASSWORD = "correct-horse-battery-staple"


def _patch_auth_settings(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(settings, "AUTH_MODE", "jwt", raising=False)
    monkeypatch.setattr(settings, "ALGORITHM", "HS256", raising=False)
    monkeypatch.setattr(settings, "SECRET_KEY", "k" * 40, raising=False)
    monkeypatch.setattr(settings, "SECRET_KEY_FALLBACKS", "", raising=False)
    monkeypatch.setattr(settings, "JWT_ISSUER", "", raising=False)
    monkeypatch.setattr(settings, "JWT_AUDIENCE", "", raising=False)
    monkeypatch.setattr(settings, "JWT_TENANT_CLAIM", "tenant_id", raising=False)
    monkeypatch.setattr(settings, "JWT_ENFORCE_TENANT_HEADER_MATCH", False, raising=False)
    monkeypatch.setattr(settings, "JWT_GROUPS_SYNC_ENABLED", False, raising=False)
    monkeypatch.setattr(settings, "JWT_TENANT_MEMBER_AUTO_PROVISION_ENABLED", False, raising=False)
    monkeypatch.setattr(settings, "DEFAULT_TENANT_ID", str(uuid4()), raising=False)
    monkeypatch.setattr(settings, "INITIAL_REGISTRATION_TOKEN", "", raising=False)


def _build_client():
    engine = create_engine(
        "sqlite+pysqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine, tables=[User.__table__, Tenant.__table__, TenantMember.__table__])
    test_session = sessionmaker(bind=engine)

    def _get_test_db():
        db = test_session()
        try:
            yield db
        finally:
            db.close()

    app = FastAPI()
    app.include_router(auth_module.router, prefix="/auth")
    app.dependency_overrides[auth_module.get_db] = _get_test_db
    return test_session, app


def _register(client: TestClient, email="owner@example.com", username="owner"):
    response = client.post(
        "/auth/register",
        json={"email": email, "username": username, "password": PASSWORD},
    )
    assert response.status_code == 201, response.text


def _login(client: TestClient, identifier, password):
    return client.post("/auth/login", json={"identifier": identifier, "password": password})


def test_consecutive_failures_lock_the_account(monkeypatch: pytest.MonkeyPatch) -> None:
    _patch_auth_settings(monkeypatch)
    monkeypatch.setattr(settings, "LOGIN_MAX_FAILED_ATTEMPTS", 3, raising=False)
    monkeypatch.setattr(settings, "LOGIN_LOCKOUT_MINUTES", 15, raising=False)
    test_session, app = _build_client()

    with TestClient(app) as client:
        _register(client)
        for _ in range(3):
            failed = _login(client, "owner", "wrong-password")
            assert failed.status_code == 401, failed.text

        locked = _login(client, "owner", PASSWORD)
        assert locked.status_code == 403, locked.text
        assert "locked" in locked.json()["detail"].lower()

        db = test_session()
        try:
            user = UserService.get_by_username(db, "owner")
            assert user.failed_login_attempts == 3
            assert user.locked_until is not None
        finally:
            db.close()


def test_success_before_threshold_resets_counter(monkeypatch: pytest.MonkeyPatch) -> None:
    _patch_auth_settings(monkeypatch)
    monkeypatch.setattr(settings, "LOGIN_MAX_FAILED_ATTEMPTS", 3, raising=False)
    test_session, app = _build_client()

    with TestClient(app) as client:
        _register(client)
        assert _login(client, "owner", "wrong-password").status_code == 401
        assert _login(client, "owner", "wrong-password").status_code == 401
        ok = _login(client, "owner", PASSWORD)
        assert ok.status_code == 200, ok.text

        db = test_session()
        try:
            user = UserService.get_by_username(db, "owner")
            assert user.failed_login_attempts == 0
            assert user.locked_until is None
        finally:
            db.close()


def test_expired_lock_no_longer_blocks(monkeypatch: pytest.MonkeyPatch) -> None:
    from datetime import datetime, timedelta, timezone

    _patch_auth_settings(monkeypatch)
    monkeypatch.setattr(settings, "LOGIN_MAX_FAILED_ATTEMPTS", 1, raising=False)
    test_session, app = _build_client()

    with TestClient(app) as client:
        _register(client)
        assert _login(client, "owner", "wrong-password").status_code == 401
        assert _login(client, "owner", PASSWORD).status_code == 403

        db = test_session()
        try:
            user = UserService.get_by_username(db, "owner")
            user.locked_until = datetime.now(timezone.utc) - timedelta(seconds=1)
            db.add(user)
            db.commit()
        finally:
            db.close()

        ok = _login(client, "owner", PASSWORD)
        assert ok.status_code == 200, ok.text


def test_unknown_identifier_stays_401_without_lockout(monkeypatch: pytest.MonkeyPatch) -> None:
    _patch_auth_settings(monkeypatch)
    monkeypatch.setattr(settings, "LOGIN_MAX_FAILED_ATTEMPTS", 2, raising=False)
    _, app = _build_client()

    with TestClient(app) as client:
        for _ in range(4):
            response = _login(client, "ghost", "wrong-password")
            assert response.status_code == 401, response.text
            assert "locked" not in response.json()["detail"].lower()


def test_lockout_defaults_are_sane() -> None:
    max_attempts, lockout_minutes = UserService._lockout_limits()
    assert max_attempts >= 1
    assert lockout_minutes >= 1
