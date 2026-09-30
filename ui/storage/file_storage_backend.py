"""
Native file-backed key/value storage.

Desktop builds use this backend so Journey persistence does not depend on
Flet's client-side SharedPreferences service. Each key is stored independently
and writes are atomic.
"""

from __future__ import annotations

import asyncio
import os
import sys
import tempfile
from pathlib import Path
from urllib.parse import quote


APP_DATA_DIRNAME = "PokemonBattleCompass"


def default_storage_dir() -> Path:
    """Return the per-user persistent storage directory for native builds."""

    if sys.platform == "win32":
        base = (
            os.environ.get("LOCALAPPDATA")
            or os.environ.get("APPDATA")
        )
        if base:
            return Path(base) / APP_DATA_DIRNAME / "storage"

    if sys.platform == "darwin":
        return (
            Path.home()
            / "Library"
            / "Application Support"
            / APP_DATA_DIRNAME
            / "storage"
        )

    xdg_data_home = os.environ.get("XDG_DATA_HOME")
    if xdg_data_home:
        return Path(xdg_data_home) / APP_DATA_DIRNAME / "storage"

    return (
        Path.home()
        / ".local"
        / "share"
        / APP_DATA_DIRNAME
        / "storage"
    )


class FileStorageBackend:
    """StorageBackend implementation backed by per-key local files."""

    def __init__(self, storage_dir: Path | None = None) -> None:
        self.storage_dir = (
            storage_dir
            if storage_dir is not None
            else default_storage_dir()
        )
        self._lock = asyncio.Lock()

    def _path_for_key(self, key: str) -> Path:
        if not isinstance(key, str) or not key:
            raise ValueError("Storage key must be a non-empty string.")

        # Percent-encoding keeps filenames deterministic and prevents path
        # separators or platform-reserved punctuation from escaping the
        # storage directory.
        filename = f"{quote(key, safe='._-')}.txt"
        return self.storage_dir / filename

    @staticmethod
    def _read_value(path: Path) -> str | None:
        try:
            return path.read_text(encoding="utf-8")
        except FileNotFoundError:
            return None

    def _write_value(self, path: Path, value: str) -> bool:
        self.storage_dir.mkdir(parents=True, exist_ok=True)

        temp_path: Path | None = None
        try:
            with tempfile.NamedTemporaryFile(
                mode="w",
                encoding="utf-8",
                newline="",
                dir=self.storage_dir,
                prefix=".write-",
                suffix=".tmp",
                delete=False,
            ) as temp_file:
                temp_file.write(value)
                temp_file.flush()
                os.fsync(temp_file.fileno())
                temp_path = Path(temp_file.name)

            os.replace(temp_path, path)
            return True
        finally:
            if temp_path is not None and temp_path.exists():
                try:
                    temp_path.unlink()
                except OSError:
                    pass

    @staticmethod
    def _remove_value(path: Path) -> bool:
        try:
            path.unlink()
        except FileNotFoundError:
            pass
        return True

    @staticmethod
    def _contains_value(path: Path) -> bool:
        return path.is_file()

    async def get(self, key: str) -> str | None:
        """Return a stored string value, or None when the key is absent."""

        path = self._path_for_key(key)
        async with self._lock:
            return await asyncio.to_thread(
                self._read_value,
                path,
            )

    async def set(self, key: str, value: str) -> bool:
        """Persist a string value atomically."""

        if not isinstance(value, str):
            raise TypeError("Storage value must be a string.")

        path = self._path_for_key(key)
        async with self._lock:
            return await asyncio.to_thread(
                self._write_value,
                path,
                value,
            )

    async def remove(self, key: str) -> bool:
        """Remove a stored value and report success."""

        path = self._path_for_key(key)
        async with self._lock:
            return await asyncio.to_thread(
                self._remove_value,
                path,
            )

    async def contains(self, key: str) -> bool:
        """Return whether a key currently exists."""

        path = self._path_for_key(key)
        async with self._lock:
            return await asyncio.to_thread(
                self._contains_value,
                path,
            )
