"""
Persistent Journey storage.

Stores player-owned Journey data in Flet SharedPreferences rather than
writing into bundled application reference files. Also provides portable,
versioned Journey export and import validation.
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

JOURNEY_EXPORT_FORMAT = "pokemon-battle-compass-journey"
JOURNEY_EXPORT_FORMAT_VERSION = 1

VALID_ACTIVE_VIEWS = {
    "battle_compass",
    "my_team",
    "my_journey",
    "about",
}

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

JourneyImportStatus = Literal[
    "valid",
    "invalid",
]


@dataclass(frozen=True)
class JourneyLoadResult:
    """Result of attempting to load the locally saved Journey."""

    status: JourneyLoadStatus
    journey: dict | None = None
    error: str | None = None


@dataclass(frozen=True)
class JourneyImportResult:
    """Result of validating a portable Journey export."""

    status: JourneyImportStatus
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
        "box": [],
        "active_view": "battle_compass",
        "battle_compass_selection": {
            "trainer": None,
            "battle": None,
            "opponent": None,
        },
        "my_journey": {
            "earned_badges": 0,
            "checklist_initialized": False,
            "item_objectives": [],
            "pokemon_objectives": [],
        },
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

    box = journey.get("box", [])

    if not isinstance(box, list):
        return "Stored Journey box is not a list."

    if not all(
        isinstance(pokemon, dict)
        for pokemon in box
    ):
        return (
            "Stored Journey contains an invalid "
            "boxed Pokémon record."
        )

    active_view = journey.get("active_view")

    if active_view is not None:
        if (
            not isinstance(active_view, str)
            or active_view not in VALID_ACTIVE_VIEWS
        ):
            return "Stored Journey active view is invalid."

    my_journey = journey.get("my_journey")

    if my_journey is not None:
        if not isinstance(my_journey, dict):
            return "Stored My Journey data is invalid."

        earned_badges = my_journey.get("earned_badges", 0)
        if (
            not isinstance(earned_badges, int)
            or isinstance(earned_badges, bool)
            or not 0 <= earned_badges <= 8
        ):
            return "Stored My Journey badge progress is invalid."

        checklist_initialized = my_journey.get(
            "checklist_initialized",
            False,
        )
        if not isinstance(checklist_initialized, bool):
            return (
                "Stored My Journey checklist initialization "
                "state is invalid."
            )

        for field_name in (
            "item_objectives",
            "pokemon_objectives",
        ):
            field_value = my_journey.get(field_name, [])
            if not isinstance(field_value, list):
                return (
                    "Stored My Journey "
                    f"{field_name} is invalid."
                )

    battle_compass_selection = journey.get(
        "battle_compass_selection"
    )

    if battle_compass_selection is not None:
        if not isinstance(
            battle_compass_selection,
            dict,
        ):
            return (
                "Stored Battle Compass selection "
                "is invalid."
            )

        for field_name in (
            "trainer",
            "battle",
            "opponent",
        ):
            field_value = battle_compass_selection.get(
                field_name
            )

            if (
                field_value is not None
                and not isinstance(
                    field_value,
                    str,
                )
            ):
                return (
                    "Stored Battle Compass "
                    f"{field_name} is invalid."
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


def create_journey_export(
    journey: dict,
    *,
    app_version: str,
) -> dict:
    """
    Create a portable export containing the complete Journey.

    Unknown Journey fields are preserved so future player-owned features,
    including My Journey, are automatically included.
    """

    journey_to_export = deepcopy(journey)

    validation_error = _validate_journey(
        journey_to_export
    )

    if validation_error:
        raise ValueError(validation_error)

    return {
        "file_format": JOURNEY_EXPORT_FORMAT,
        "file_format_version": (
            JOURNEY_EXPORT_FORMAT_VERSION
        ),
        "app_version": app_version,
        "exported_at": _utc_timestamp(),
        "journey": journey_to_export,
    }


def serialize_journey_export(
    journey: dict,
    *,
    app_version: str,
) -> str:
    """Serialize a Journey as formatted portable JSON."""

    export_record = create_journey_export(
        journey,
        app_version=app_version,
    )

    return json.dumps(
        export_record,
        ensure_ascii=False,
        indent=2,
    )


def parse_journey_export(
    serialized_export: str,
) -> JourneyImportResult:
    """
    Parse and validate a portable Journey export.

    This function never modifies local storage or active application state.
    """

    try:
        export_record = json.loads(
            serialized_export
        )
    except json.JSONDecodeError as error:
        return JourneyImportResult(
            status="invalid",
            error=(
                "The selected file does not contain "
                f"valid JSON: {error}"
            ),
        )

    if not isinstance(export_record, dict):
        return JourneyImportResult(
            status="invalid",
            error=(
                "The selected file is not a valid "
                "Pokémon Battle Compass Journey."
            ),
        )

    if (
        export_record.get("file_format")
        != JOURNEY_EXPORT_FORMAT
    ):
        return JourneyImportResult(
            status="invalid",
            error=(
                "The selected file is not a Pokémon "
                "Battle Compass Journey export."
            ),
        )

    if (
        export_record.get("file_format_version")
               != JOURNEY_EXPORT_FORMAT_VERSION
    ):
        return JourneyImportResult(
            status="invalid",
            error=(
                "This Journey export uses an unsupported "
                "file-format version."
            ),
        )

    journey = export_record.get("journey")

    validation_error = _validate_journey(
        journey
    )

    if validation_error:
        return JourneyImportResult(
            status="invalid",
            error=validation_error,
        )

    return JourneyImportResult(
        status="valid",
        journey=deepcopy(journey),
    )


def journey_export_filename() -> str:
    """Return the default filename for a Journey export."""

    date_stamp = datetime.now().strftime(
        "%Y-%m-%d"
    )

    return (
        "Pokemon Battle Compass Journey "
        f"- {date_stamp}.json"
    )


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