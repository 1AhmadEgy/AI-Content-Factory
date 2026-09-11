import importlib

import pytest


@pytest.mark.parametrize(
    "missing", ["AICF_API_TOKEN", "AICF_DATABASE_URL"],
)
def test_production_configuration_fails_closed(monkeypatch, missing):
    monkeypatch.setenv("AICF_ENV", "production")
    monkeypatch.setenv("AICF_API_TOKEN", "strong-test-token")
    monkeypatch.setenv("AICF_DATABASE_URL", "postgresql://factory:factory@localhost/factory")
    monkeypatch.delenv(missing, raising=False)

    import backend.app.main as main
    importlib.reload(main)

    errors = main._production_configuration_errors()
    assert missing + "_REQUIRED" in errors
    assert "POSTGRES_RUNTIME_NOT_IMPLEMENTED" in errors


def test_development_configuration_does_not_require_production_database(monkeypatch):
    monkeypatch.setenv("AICF_ENV", "development")
    monkeypatch.delenv("AICF_API_TOKEN", raising=False)
    monkeypatch.delenv("AICF_DATABASE_URL", raising=False)

    import backend.app.main as main
    importlib.reload(main)

    assert main._production_configuration_errors() == []
