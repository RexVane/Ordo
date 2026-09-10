"""P0: initial-admin bootstrap password policy.

Regression tests for the fail-closed weak-password refusal:

- well-known weak passwords (e.g. ``admin123456``) are rejected both by the
  startup settings validator and by the bootstrap service helper;
- passwords equal to the admin username/email are rejected;
- strong passwords still pass.

These tests deliberately avoid importing ``Settings`` (which pulls heavy
optional dependencies) and exercise ``app.core.config_validation`` directly
with a stub settings object, so they also run in minimal environments.
"""

from types import SimpleNamespace

import pytest

from app.core.config_validation import (
    _validate_initial_admin_password,
    reject_weak_bootstrap_password,
    validate_initial_admin_bootstrap,
    weak_bootstrap_password_reason,
)

STRONG_PASSWORD = "correct-horse-battery-staple-99"


def _stub_settings(password_min_length=8):
    return SimpleNamespace(PASSWORD_MIN_LENGTH=password_min_length)


@pytest.mark.parametrize(
    "password",
    [
        "admin123456",
        "Admin123456",
        "  admin123456  ",
        "ADMIN",
        "password",
        "Password123",
        "qwerty",
        "qwerty123",
        "letmein",
        "welcome123",
        "changeme",
        "12345678",
        "00000000",
        "test123",
        "demo123",
        "ordo",
        "Ordo123456",
        "root",
    ],
)
def test_well_known_weak_passwords_are_rejected(password):
    assert weak_bootstrap_password_reason(password) is not None
    with pytest.raises(ValueError, match="well-known weak password"):
        reject_weak_bootstrap_password(password)


def test_strong_password_is_accepted():
    assert weak_bootstrap_password_reason(STRONG_PASSWORD) is None
    reject_weak_bootstrap_password(STRONG_PASSWORD)  # must not raise


def test_empty_password_has_no_weak_reason():
    # Empty means "bootstrap not configured"; length/presence checks own that path.
    assert weak_bootstrap_password_reason("") is None
    assert weak_bootstrap_password_reason(None) is None


@pytest.mark.parametrize(
    ("password", "username", "email"),
    [
        ("owner", "owner", "owner@example.com"),
        ("OWNER", "owner", "owner@example.com"),
        ("owner@example.com", "owner", "owner@example.com"),
    ],
)
def test_password_equal_to_identity_is_rejected(password, username, email):
    assert weak_bootstrap_password_reason(password, username=username, email=email) is not None
    with pytest.raises(ValueError, match="must not equal the admin username or email"):
        reject_weak_bootstrap_password(password, username=username, email=email)


def test_settings_validator_rejects_weak_bootstrap_password():
    settings = _stub_settings()
    with pytest.raises(ValueError, match="well-known weak password"):
        _validate_initial_admin_password(
            settings, "admin123456", username="owner", email="owner@example.com"
        )


def test_settings_validator_accepts_strong_bootstrap_password():
    settings = _stub_settings()
    _validate_initial_admin_password(
        settings, STRONG_PASSWORD, username="owner", email="owner@example.com"
    )  # must not raise


def test_settings_validator_still_enforces_min_length():
    settings = _stub_settings(password_min_length=12)
    with pytest.raises(ValueError, match="at least 12 characters"):
        _validate_initial_admin_password(
            settings, "short-99", username="owner", email="owner@example.com"
        )


def test_bootstrap_entrypoint_rejects_weak_password_end_to_end():
    settings = SimpleNamespace(
        INITIAL_ADMIN_EMAIL="owner@example.com",
        INITIAL_ADMIN_USERNAME="owner",
        INITIAL_ADMIN_PASSWORD="admin123456",
        INITIAL_ADMIN_PASSWORD_FILE="",
        PASSWORD_MIN_LENGTH=8,
    )
    with pytest.raises(ValueError, match="well-known weak password"):
        validate_initial_admin_bootstrap(settings)


def test_bootstrap_entrypoint_accepts_strong_password():
    settings = SimpleNamespace(
        INITIAL_ADMIN_EMAIL="owner@example.com",
        INITIAL_ADMIN_USERNAME="owner",
        INITIAL_ADMIN_PASSWORD=STRONG_PASSWORD,
        INITIAL_ADMIN_PASSWORD_FILE="",
        PASSWORD_MIN_LENGTH=8,
    )
    validate_initial_admin_bootstrap(settings)  # must not raise
    assert settings.INITIAL_ADMIN_EMAIL == "owner@example.com"
    assert settings.INITIAL_ADMIN_USERNAME == "owner"
