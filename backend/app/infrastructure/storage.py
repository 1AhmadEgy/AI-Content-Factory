from __future__ import annotations

import hashlib
import os
from pathlib import Path
from tempfile import NamedTemporaryFile

from ..domain.assets import Asset


class LocalAssetStorage:
    """Atomic local filesystem storage keyed by SHA-256 content."""

    def __init__(self, root: str | Path) -> None:
        self.root = Path(root)
        self.root.mkdir(parents=True, exist_ok=True)

    def put_bytes(self, data: bytes) -> tuple[str, str, int]:
        digest = hashlib.sha256(data).hexdigest()
        directory = self.root / digest[:2]
        directory.mkdir(parents=True, exist_ok=True)
        target = directory / digest
        if not target.exists():
            with NamedTemporaryFile(dir=directory, prefix=f".{digest}.", delete=False) as handle:
                temporary = Path(handle.name)
                handle.write(data)
                handle.flush()
                os.fsync(handle.fileno())
            os.replace(temporary, target)
        return digest, str(target), len(data)

    def read_bytes(self, sha256: str) -> bytes:
        path = self.root / sha256[:2] / sha256
        data = path.read_bytes()
        if hashlib.sha256(data).hexdigest() != sha256:
            raise IOError(f"Asset checksum mismatch: {sha256}")
        return data

    def exists(self, sha256: str) -> bool:
        return (self.root / sha256[:2] / sha256).is_file()

    def delete(self, sha256: str) -> None:
        path = self.root / sha256[:2] / sha256
        if path.exists():
            path.unlink()

    def verify(self, asset: Asset) -> bool:
        if not self.exists(asset.sha256):
            return False
        data = self.read_bytes(asset.sha256)
        return len(data) == asset.size_bytes
