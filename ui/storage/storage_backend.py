"""
Framework-independent key/value storage contract.

Application and Journey persistence code depend on this interface rather
than on a platform-specific storage implementation.
"""

from __future__ import annotations

from typing import Protocol


class StorageBackend(Protocol):
    """Minimal asynchronous key/value storage used by persistent app data."""

    async def get(self, key: str) -> str | None:
        """Return a stored string value, or None when the key is absent."""
        ...

    async def set(self, key: str, value: str) -> bool:
        """Persist a string value and report whether the write succeeded."""
        ...

    async def remove(self, key: str) -> bool:
        """Remove a stored value and report whether the operation succeeded."""
        ...

    async def contains(self, key: str) -> bool:
        """Return whether a key currently exists."""
        ...