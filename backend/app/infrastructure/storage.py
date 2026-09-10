from __future__ import annotations

import hashlib
import os
import shutil
from pathlib import Path
from tempfile import NamedTemporaryFile

from ..domain.assets import Asset


class LocalAssetStorage:
    """Atomic local filesystem storage keyed by SHA-256 content."""

    _HASH_CHUNK_SIZE = 1024 * 1024

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
                try:
                    handle.write(data)
                    handle.flush()
                    os.fsync(handle.fileno())
                    os.replace(temporary, target)
                except BaseException:
                    temporary.unlink(missing_ok=True)
                    raise
        return digest, str(target), len(data)

    def put_file(self, source: str | Path) -> tuple[str, str, int]:
        """Stream a file into content-addressed storage without loading it into RAM."""
        source_path = Path(source)
        if not source_path.is_file():
            raise FileNotFoundError(source_path)
        digest_state = hashlib.sha256()
        size = 0
        temporary: Path | None = None
        directory: Path | None = None
        try:
            with source_path.open("rb") as source_handle:
                with NamedTemporaryFile(dir=self.root, prefix=".asset-", delete=False) as handle:
                    temporary = Path(handle.name)
                    while True:
                        chunk = source_handle.read(self._HASH_CHUNK_SIZE)
                        if not chunk:
                            break
                        digest_state.update(chunk)
                        size += len(chunk)
                        handle.write(chunk)
                    handle.flush()
                    os.fsync(handle.fileno())
            digest = digest_state.hexdigest()
            directory = self.root / digest[:2]
            directory.mkdir(parents=True, exist_ok=True)
            target = directory / digest
            if not target.exists():
                os.replace(temporary, target)
                temporary = None
            return digest, str(target), size
        finally:
            if temporary is not None:
                temporary.unlink(missing_ok=True)

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
        path = self.root / asset.sha256[:2] / asset.sha256
        if not path.is_file():
            return False
        try:
            if path.stat().st_size != asset.size_bytes:
                return False
            digest = hashlib.sha256()
            with path.open("rb") as handle:
                for chunk in iter(lambda: handle.read(self._HASH_CHUNK_SIZE), b""):
                    digest.update(chunk)
            return digest.hexdigest() == asset.sha256
        except OSError:
            return False
