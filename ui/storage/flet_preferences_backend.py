"""
Flet SharedPreferences storage backend.

This is the current desktop implementation of StorageBackend. A PWA/browser
backend can implement the same interface without changing Journey semantics
or application state.
"""

from __future__ import annotations

import asyncio
from datetime import datetime

import flet as ft


def _debug_log(message: str) -> None:
    """Print timestamped SharedPreferences diagnostics."""

    timestamp = datetime.now().strftime("%H:%M:%S.%f")[:-3]
    print(f"[{timestamp}] {message}", flush=True)


class FletPreferencesBackend:
    """StorageBackend implementation backed by Flet SharedPreferences."""

    def __init__(self, page: ft.Page) -> None:
        self.page = page
        self.preferences = self._get_or_create_preferences()

    def _get_or_create_preferences(self) -> ft.SharedPreferences:
        """Reuse the page's SharedPreferences service or register one."""

        for service in self.page.services:
            if isinstance(service, ft.SharedPreferences):
                _debug_log(
                    f"PREFS reusing SharedPreferences service id={id(service)}"
                )
                return service

        preferences = ft.SharedPreferences()
        self.page.services.append(preferences)
        self.page.update()
        _debug_log(
            f"PREFS registered SharedPreferences service id={id(preferences)}"
        )
        return preferences

    @staticmethod
    def _is_invoke_timeout(error: RuntimeError) -> bool:
        """Return whether Flet timed out waiting for a service listener."""

        message = str(error)

        return (
            "TimeoutException" in message
            and "Timeout waiting for invoke method listener" in message
        )

    async def _invoke_with_retry(self, operation, *, label: str):
        """Retry Flet invoke-listener timeouts while logging each attempt."""

        retry_delays = (0.35, 0.75, 1.25)

        for attempt, delay in enumerate(retry_delays, start=1):
            _debug_log(
                f"PREFS {label} attempt {attempt} start "
                f"service_id={id(self.preferences)}"
            )
            try:
                result = await operation()
            except RuntimeError as error:
                _debug_log(
                    f"PREFS {label} attempt {attempt} FAILED: "
                    f"{type(error).__name__}: {error}"
                )
                if not self._is_invoke_timeout(error):
                    raise

                _debug_log(
                    f"PREFS {label} retrying after {delay:.2f}s"
                )
                await asyncio.sleep(delay)
                continue

            _debug_log(
                f"PREFS {label} attempt {attempt} succeeded"
            )
            return result

        final_attempt = len(retry_delays) + 1
        _debug_log(
            f"PREFS {label} attempt {final_attempt} start "
            f"service_id={id(self.preferences)}"
        )
        try:
            result = await operation()
        except Exception as error:
            _debug_log(
                f"PREFS {label} attempt {final_attempt} FAILED: "
                f"{type(error).__name__}: {error}"
            )
            raise

        _debug_log(
            f"PREFS {label} attempt {final_attempt} succeeded"
        )
        return result

    async def get(self, key: str) -> str | None:
        """Return a stored string value, or None when absent."""

        value = await self._invoke_with_retry(
            lambda: self.preferences.get(key),
            label=f"get key={key!r}",
        )

        if value is None or isinstance(value, str):
            return value

        # StorageBackend intentionally exposes only string values. Returning
        # the unexpected value unchanged would weaken the shared contract.
        return None

    async def set(self, key: str, value: str) -> bool:
        """Persist a string value."""

        return await self._invoke_with_retry(
            lambda: self.preferences.set(key, value),
            label=f"set key={key!r}",
        )

    async def remove(self, key: str) -> bool:
        """Remove a stored value."""

        return await self._invoke_with_retry(
            lambda: self.preferences.remove(key),
            label=f"remove key={key!r}",
        )

    async def contains(self, key: str) -> bool:
        """Return whether a key exists."""

        return await self._invoke_with_retry(
            lambda: self.preferences.contains_key(key),
            label=f"contains key={key!r}",
        )
