"""P0: connector secret handling (encrypt at rest, redact on read).

Pure-function tests for ``app.core.secrets``:

- known secret fields are encrypted with the ``enc:v1:`` prefix;
- redaction never reveals values and never raises;
- encrypt -> decrypt round-trips, including legacy plaintext passthrough;
- non-secret fields are untouched.
"""

from app.core import secrets


def test_encrypt_marks_and_decrypt_round_trips():
    config = {"auth": {"type": "basic", "token": "t-123", "api_key": "k-456"}, "name": "x"}
    encrypted = secrets.encrypt_connector_config_secrets(config)
    assert encrypted["auth"]["token"].startswith("enc:v1:")
    assert encrypted["auth"]["api_key"].startswith("enc:v1:")
    assert encrypted["name"] == "x"
    assert encrypted["auth"]["type"] == "basic"
    assert secrets.decrypt_connector_config_secrets(encrypted) == config


def test_redact_hides_all_secret_fields_and_never_raises():
    config = {
        "password": "p",
        "api_key": "k",
        "auth": {"cookie": "c", "client_secret": "s", "access_key": "a", "type": "oauth"},
    }
    redacted = secrets.redact_secrets(config)
    assert redacted["password"] == "<redacted>"
    assert redacted["api_key"] == "<redacted>"
    assert redacted["auth"]["cookie"] == "<redacted>"
    assert redacted["auth"]["client_secret"] == "<redacted>"
    assert redacted["auth"]["access_key"] == "<redacted>"
    assert redacted["auth"]["type"] == "oauth"
    assert secrets.redact_secrets(None) == {}
    assert secrets.redact_secrets("nope") == {}


def test_legacy_plaintext_passthrough():
    config = {"auth": {"token": "plain-token"}}
    assert secrets.decrypt_connector_config_secrets(config) == config
    assert secrets.is_encrypted("plain-token") is False
    assert secrets.is_encrypted(secrets.encrypt_secret("v")) is True
