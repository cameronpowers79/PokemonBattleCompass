"""
Flet SharedPreferences storage backend.

This is the current desktop implementation of StorageBackend. A PWA/browser
backend can implement the same interface without changing Journey semantics
or application state.
"""

from __future__ import annotations

import flet as ft


class FletPreferencesBackend:
    """StorageBackend implementation backed by Flet SharedPreferences."""

    def __init__(self, page: ft.Page) -> None:
        self.page = page
        self.preferences = self._get_or_create_preferences()

    def _get_or_create_preferences(self) -> ft.SharedPreferences:
        """Reuse the page's SharedPreferences service or register one."""

        for service in self.page.services:
            if isinstance(service, ft.SharedPreferences):
                return service

        preferences = ft.SharedPreferences()
        self.page.services.append(preferences)
        self.page.update()
        return preferences

    async def get(self, key: str) -> str | None:
        """Return a stored string value, or None when absent."""

        value = await self.preferences.get(key)
        if value is None or isinstance(value, str):
            return value

        # StorageBackend intentionally exposes only string values. Returning
        # the unexpected value unchanged would weaken the shared contract.
        return None

    async def set(self, key: str, value: str) -> bool:
        """Persist a string value."""

        return await self.preferences.set(key, value)

    async def remove(self, key: str) -> bool:
        """Remove a stored value."""

        return await self.preferences.remove(key)

    async def contains(self, key: str) -> bool:
        """Return whether a key exists."""

        return await self.preferences.contains_key(key)