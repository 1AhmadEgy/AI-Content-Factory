from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.production_guard import scan


def test_repository_has_no_forbidden_production_implementations() -> None:
    assert scan(ROOT) == []
