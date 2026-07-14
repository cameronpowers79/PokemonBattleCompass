"""
Persistent Journey storage.

Stores player-owned Journey data in Flet SharedPreferences rather than
writing into bundled application reference files.
"""

from __future__ import annotations

import json
from copy import deepcopy
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Literal

import flet as ft


JOURNEY_STORAGE_KEY = "pokemon_battle_compass.journey.v1"
JOURNEY_SCHEMA_VERSION = 1

VALID_STARTERS = {
    "Grookey",
    "Scorbunny",
    "Sobble",
}

JourneyLoadStatus = Literal[
    "missing",
    "valid",
    "invalid",
]


@dataclass(frozen=True)
class JourneyLoadResult:
    """Result of attempting to load the locally saved Journey."""

    status: JourneyLoadStatus
    journey: dict | None = None
    error: str | None = None


def _utc_timestamp() -> str:
    """Return the current UTC time in ISO-8601 format."""

    return datetime.now(timezone.utc).isoformat()


def _get_preferences(
    page: ft.Page,
) -> ft.SharedPreferences:
    """
    Return the SharedPreferences service registered to this page.

    The service must be created during the active Flet session and added
    to the page before its methods can be invoked.
    """

    for service in page.services:
        if isinstance(service, ft.SharedPreferences):
            return service

    preferences = ft.SharedPreferences()
    page.services.append(preferences)
    page.update()

    return preferences


def create_journey(
    *,
    starter: str,
    team: list[dict] | None = None,
) -> dict:
    """Create a new versioned Journey record."""

    if starter not in VALID_STARTERS:
        raise ValueError(
            f"Unsupported starter: {starter}"
        )

    timestamp = _utc_timestamp()

    return {
        "schema_version": JOURNEY_SCHEMA_VERSION,
        "starter": starter,
        "team": deepcopy(team or []),
        "created_at": timestamp,
        "updated_at": timestamp,
    }


def _validate_journey(
    journey: object,
) -> str | None:
    """Return an error message when Journey data is invalid."""

    if not isinstance(journey, dict):
        return "Stored Journey data is not an object."

    if (
        journey.get("schema_version")
        != JOURNEY_SCHEMA_VERSION
    ):
        return (
            "Stored Journey uses an unsupported "
            "schema version."
        )

    starter = journey.get("starter")

    if not isinstance(starter, str):
        return (
            "Stored Journey starter is missing "
            "or invalid."
        )

    if starter not in VALID_STARTERS:
        return (
            "Stored Journey starter is unsupported: "
            f"{starter}"
        )

    team = journey.get("team")

    if not isinstance(team, list):
        return "Stored Journey team is not a list."

    if not all(
        isinstance(pokemon, dict)
        for pokemon in team
    ):
        return (
            "Stored Journey contains an invalid "
            "team record."
        )

    created_at = journey.get("created_at")
    updated_at = journey.get("updated_at")

    if not isinstance(created_at, str):
        return (
            "Stored Journey creation date is invalid."
        )

    if not isinstance(updated_at, str):
        return (
            "Stored Journey update date is invalid."
        )

    return None


async def load_journey(
    page: ft.Page,
) -> JourneyLoadResult:
    """Load and validate the locally saved Journey."""

    preferences = _get_preferences(page)

    stored_value = await preferences.get(
        JOURNEY_STORAGE_KEY
    )

    if stored_value is None:
        return JourneyLoadResult(
            status="missing",
        )

    if not isinstance(stored_value, str):
        return JourneyLoadResult(
            status="invalid",
            error=(
                "Stored Journey data is not "
                "valid JSON text."
            ),
        )

    try:
        journey = json.loads(stored_value)
    except json.JSONDecodeError as error:
        return JourneyLoadResult(
            status="invalid",
            error=(
                "Stored Journey JSON could not be read: "
                f"{error}"
            ),
        )

    validation_error = _validate_journey(
        journey
    )

    if validation_error:
        return JourneyLoadResult(
            status="invalid",
            error=validation_error,
        )

    return JourneyLoadResult(
        status="valid",
        journey=journey,
    )


async def save_journey(
    page: ft.Page,
    journey: dict,
) -> bool:
    """Save a valid Journey to persistent local storage."""

    preferences = _get_preferences(page)
    journey_to_save = deepcopy(journey)

    journey_to_save["schema_version"] = (
        JOURNEY_SCHEMA_VERSION
    )
    journey_to_save["updated_at"] = (
        _utc_timestamp()
    )

    if not journey_to_save.get("created_at"):
        journey_to_save["created_at"] = (
            journey_to_save["updated_at"]
        )

    validation_error = _validate_journey(
        journey_to_save
    )

    if validation_error:
        raise ValueError(validation_error)

    serialized_journey = json.dumps(
        journey_to_save,
        ensure_ascii=False,
        separators=(",", ":"),
    )

    save_succeeded = await preferences.set(
        JOURNEY_STORAGE_KEY,
        serialized_journey,
    )

    if save_succeeded:
        journey.clear()
        journey.update(journey_to_save)

    return save_succeeded


async def clear_journey(
    page: ft.Page,
) -> bool:
    """Remove the locally saved Journey."""

    preferences = _get_preferences(page)

    journey_exists = await preferences.contains_key(
        JOURNEY_STORAGE_KEY
    )

    if not journey_exists:
        return True

    return await preferences.remove(
        JOURNEY_STORAGE_KEY
    )