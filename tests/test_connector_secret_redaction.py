"""P0: connector secret handling (encrypt at rest, redact on read).

Pure-function tests for ``app.core.secrets``:

- known secret fields are encrypted with the ``enc:v1:`` prefix;
- redaction never reveals values and never raises;
- encrypt -> decrypt round-trips, including legacy plaintext passthrough;
- non-secret fields are untouched.
"""

import importlib.util
import sys
import types
from pathlib import Path

import pytest

REPO = str(Path(__file__).resolve().parents[1])


def _load_secrets_module():
    """Import the real module in full environments, stub-load it in minimal ones.

    The stub path keeps these pure-function tests runnable without the heavy
    backend dependency tree (langchain etc.). In CI the real import succeeds
    and no stubbing happens, so other tests are never affected.
    """
    try:
        from app.core import secrets as real_secrets

        return real_secrets
    except ImportError:
        pass
    for key in [k for k in sys.modules if k == "app" or k.startswith("app.")]:
        sys.modules.pop(key, None)
    app_pkg = types.ModuleType("app")
    app_pkg.__path__ = [REPO + "/app"]
    core_pkg = types.ModuleType("app.core")
    core_pkg.__path__ = [REPO + "/app/core"]
    # Stub the heavy settings object; secrets only reads SECRET_KEY(_FALLBACKS).
    config_stub = types.ModuleType("app.core.config")
    config_stub.settings = types.SimpleNamespace(SECRET_KEY="s" * 32, SECRET_KEY_FALLBACKS="")
    sys.modules["app"] = app_pkg
    sys.modules["app.core"] = core_pkg
    sys.modules["app.core.config"] = config_stub
    spec = importlib.util.spec_from_file_location(
        "app.core.secrets", REPO + "/app/core/secrets.py"
    )
    module = importlib.util.module_from_spec(spec)
    sys.modules["app.core.secrets"] = module
    spec.loader.exec_module(module)
    return module


secrets = _load_secrets_module()


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


def test_rotation_fallback_decrypts_old_key():
    old = secrets.encrypt_secret("rotate-me")
    assert old.startswith("enc:v1:")
