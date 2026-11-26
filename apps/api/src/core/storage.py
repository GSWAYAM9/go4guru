"""Private local object archive abstraction matching S3-compatible immutable key semantics."""

from __future__ import annotations

import re
from pathlib import Path

_SAFE_KEY_RE = re.compile(r"^[A-Za-z0-9._/-]+$")


class LocalPrivateStorage:
    """Stores immutable uploaded originals outside webroot with path-traversal protection."""

    def __init__(self, base_dir: str | Path) -> None:
        self.root = Path(base_dir).resolve()
        self.root.mkdir(parents=True, exist_ok=True)

    def _resolve_key(self, storage_key: str) -> Path:
        if (
            not storage_key
            or ".." in storage_key
            or storage_key.startswith("/")
            or not _SAFE_KEY_RE.match(storage_key)
        ):
            raise ValueError("Invalid object storage key.")
        target = (self.root / storage_key).resolve()
        if not target.is_relative_to(self.root):
            raise ValueError("Storage path escape detected.")
        return target

    def put_immutable_bytes(self, storage_key: str, data: bytes) -> str:
        """Persist raw bytes immutably; never overwrite an existing immutable key."""
        target = self._resolve_key(storage_key)
        target.parent.mkdir(parents=True, exist_ok=True)
        if not target.exists():
            target.write_bytes(data)
        return storage_key

    def read_bytes(self, storage_key: str) -> bytes:
        """Read archived bytes safely."""
        target = self._resolve_key(storage_key)
        return target.read_bytes()
