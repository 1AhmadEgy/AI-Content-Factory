from __future__ import annotations

import argparse
from pathlib import Path


FORBIDDEN_NAMES = {
    "mock_adapter.py",
    "mock_worker.py",
    "fake_adapter.py",
    "fake_provider.py",
}

FORBIDDEN_TOKENS = (
    "MockAdapter(",
    "FakeProvider(",
    "fake_success",
    "synthetic_request_id",
    "timer_based_completion",
)

EXCLUDED_PARTS = {"tests", "docs", "scripts", ".git", "build", "dist", "__pycache__"}


def iter_production_files(root: Path):
    for path in root.rglob("*"):
        if not path.is_file():
            continue
        if any(part in EXCLUDED_PARTS for part in path.parts):
            continue
        if path.suffix.lower() not in {".py", ".kt", ".kts", ".java", ".gradle", ".yml", ".yaml"}:
            continue
        yield path


def scan(root: Path) -> list[str]:
    violations: list[str] = []
    for path in iter_production_files(root):
        if path.name.lower() in FORBIDDEN_NAMES:
            violations.append(f"forbidden production file: {path}")
            continue
        try:
            text = path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            continue
        for line_no, line in enumerate(text.splitlines(), start=1):
            for token in FORBIDDEN_TOKENS:
                if token in line:
                    violations.append(f"{path}:{line_no}: forbidden production token {token!r}")
    return violations


def main() -> int:
    parser = argparse.ArgumentParser(description="Reject fake/synthetic production implementations.")
    parser.add_argument("root", nargs="?", default=".")
    args = parser.parse_args()
    violations = scan(Path(args.root).resolve())
    if violations:
        print("Production guard FAILED")
        print("\n".join(violations))
        return 1
    print("Production guard: OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
