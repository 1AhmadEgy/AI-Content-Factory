from pathlib import Path

from scripts.production_guard import scan


def test_repository_has_no_forbidden_production_implementations() -> None:
    root = Path(__file__).resolve().parents[2]
    assert scan(root) == []
