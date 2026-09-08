"""
Flet SharedPreferences storage backend.

This is the current desktop implementation of StorageBackend. A PWA/browser
backend can implement the same interface without changing Journey semantics
or application state.
"""

from __future__ import annotations

import asyncio

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

    @staticmethod
    def _is_invoke_timeout(error: RuntimeError) -> bool:
        """Return whether Flet timed out waiting for a service listener."""

        message = str(error)

        return (
            "TimeoutException" in message
            and "Timeout waiting for invoke method listener" in message
        )

    async def _invoke_with_retry(self, operation):
        """Retry Flet invoke-listener timeouts while the service becomes ready."""

        retry_delays = (0.35, 0.75, 1.25)

        for attempt, delay in enumerate(retry_delays, start=1):
            try:
                return await operation()
            except RuntimeError as error:
                if not self._is_invoke_timeout(error):
                    raise

                # A newly-created/reconnected Flet session can briefly have the
                # SharedPreferences service registered on the Python side before
                # its client-side invoke-method listener is ready.
                await asyncio.sleep(delay)

        # Final attempt: let any remaining error propagate normally so startup
        # still fails visibly if SharedPreferences truly never becomes ready.
        return await operation()

    async def get(self, key: str) -> str | None:
        """Return a stored string value, or None when absent."""

        value = await self._invoke_with_retry(
            lambda: self.preferences.get(key)
        )

        if value is None or isinstance(value, str):
            return value

        # StorageBackend intentionally exposes only string values. Returning
        # the unexpected value unchanged would weaken the shared contract.
        return None

    async def set(self, key: str, value: str) -> bool:
        """Persist a string value."""

        return await self._invoke_with_retry(
            lambda: self.preferences.set(key, value)
        )

    async def remove(self, key: str) -> bool:
        """Remove a stored value."""

        return await self._invoke_with_retry(
            lambda: self.preferences.remove(key)
        )

    async def contains(self, key: str) -> bool:
        """Return whether a key exists."""

        return await self._invoke_with_retry(
            lambda: self.preferences.contains_key(key)
        )