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
from typing import Callable, Literal

from ui.storage.storage_backend import StorageBackend


JOURNEY_STORAGE_KEY = "pokemon_battle_compass.journey.v1"
JOURNEY_BACKUP_STORAGE_KEY = "pokemon_battle_compass.journey.backup.v1"
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
    recovered_from_backup: bool = False


@dataclass(frozen=True)
class JourneyImportResult:
    """Result of validating a portable Journey export."""

    status: JourneyImportStatus
    journey: dict | None = None
    error: str | None = None


def _utc_timestamp() -> str:
    """Return the current UTC time in ISO-8601 format."""

    return datetime.now(timezone.utc).isoformat()


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


def _migrate_journey_to_current(
    journey: object,
) -> tuple[dict | None, str | None]:
    """
    Return Journey data upgraded to the current schema version.

    Version 1 is currently the only released schema, so there are no
    historical migration steps yet. The migration pipeline is intentionally
    in place before a future schema bump so load/import behavior does not need
    to be redesigned when version 2 is introduced.
    """

    if not isinstance(journey, dict):
        return None, "Stored Journey data is not an object."

    schema_version = journey.get("schema_version")

    if (
        not isinstance(schema_version, int)
        or isinstance(schema_version, bool)
    ):
        return (
            None,
            "Stored Journey schema version is missing or invalid.",
        )

    if schema_version > JOURNEY_SCHEMA_VERSION:
        return (
            None,
            (
                "Stored Journey uses a newer schema version "
                f"({schema_version}) than this version of Pokémon "
                "Battle Compass supports."
            ),
        )

    migrated_journey = deepcopy(journey)
    current_version = schema_version

    while current_version < JOURNEY_SCHEMA_VERSION:
        migration = JOURNEY_MIGRATIONS.get(current_version)
        if migration is None:
            return (
                None,
                (
                    "Stored Journey uses an older schema version "
                    f"({current_version}) that cannot be migrated by "
                    "this version of Pokémon Battle Compass."
                ),
            )

        try:
            migrated_journey = migration(migrated_journey)
        except (TypeError, ValueError, KeyError) as error:
            return (
                None,
                (
                    "Stored Journey could not be migrated from "
                    f"schema version {current_version}: {error}"
                ),
            )

        next_version = migrated_journey.get("schema_version")
        if (
            not isinstance(next_version, int)
            or isinstance(next_version, bool)
            or next_version <= current_version
        ):
            return (
                None,
                (
                    "Stored Journey migration did not advance "
                    "to a newer schema version."
                ),
            )

        current_version = next_version

    if current_version != JOURNEY_SCHEMA_VERSION:
        return (
            None,
            "Stored Journey could not be migrated to the current schema.",
        )

    return migrated_journey, None


# Maps a Journey schema version to the function that upgrades that version
# to its immediate successor. Version 1 is the first released schema, so the
# registry is intentionally empty until a future schema version is introduced.
JOURNEY_MIGRATIONS: dict[int, Callable[[dict], dict]] = {}


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

    migrated_journey, migration_error = (
        _migrate_journey_to_current(journey)
    )

    if migration_error or migrated_journey is None:
        return JourneyImportResult(
            status="invalid",
            error=(
                migration_error
                or "The Journey could not be migrated."
            ),
        )

    validation_error = _validate_journey(
        migrated_journey
    )

    if validation_error:
        return JourneyImportResult(
            status="invalid",
            error=validation_error,
        )

    return JourneyImportResult(
        status="valid",
        journey=deepcopy(migrated_journey),
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


def _prepare_stored_journey(
    serialized_journey: str,
    *,
    source_label: str,
) -> tuple[dict | None, str | None]:
    """Decode, migrate, and validate one serialized Journey copy."""

    try:
        journey = json.loads(serialized_journey)
    except json.JSONDecodeError as error:
        return (
            None,
            f"{source_label} Journey JSON could not be read: {error}",
        )

    migrated_journey, migration_error = (
        _migrate_journey_to_current(journey)
    )

    if migration_error or migrated_journey is None:
        return (
            None,
            migration_error
            or f"{source_label} Journey could not be migrated.",
        )

    validation_error = _validate_journey(
        migrated_journey
    )

    if validation_error:
        return None, validation_error

    return migrated_journey, None


async def load_journey(
    storage: StorageBackend,
) -> JourneyLoadResult:
    """
    Load the saved Journey, recovering from the last-known-good backup
    when the primary copy is missing or unusable.
    """

    stored_value = await storage.get(
        JOURNEY_STORAGE_KEY
    )

    primary_error: str | None = None

    if stored_value is not None:
        primary_journey, primary_error = (
            _prepare_stored_journey(
                stored_value,
                source_label="Stored",
            )
        )

        if primary_journey is not None:
            return JourneyLoadResult(
                status="valid",
                journey=primary_journey,
            )

    backup_value = await storage.get(
        JOURNEY_BACKUP_STORAGE_KEY
    )

    if backup_value is not None:
        backup_journey, backup_error = (
            _prepare_stored_journey(
                backup_value,
                source_label="Backup",
            )
        )

        if backup_journey is not None:
            restored_value = json.dumps(
                backup_journey,
                ensure_ascii=False,
                separators=(",", ":"),
            )

            # Best-effort repair of the primary copy. Even if this write
            # fails, the validated backup can safely be used for this session.
            await storage.set(
                JOURNEY_STORAGE_KEY,
                restored_value,
            )

            return JourneyLoadResult(
                status="valid",
                journey=backup_journey,
                recovered_from_backup=True,
            )

        if stored_value is None:
            return JourneyLoadResult(
                status="invalid",
                error=backup_error,
            )

    if stored_value is None:
        return JourneyLoadResult(
            status="missing",
        )

    return JourneyLoadResult(
        status="invalid",
        error=(
            primary_error
            or "Stored Journey could not be loaded."
        ),
    )


async def save_journey(
    storage: StorageBackend,
    journey: dict,
) -> bool:
    """
    Save a valid Journey while preserving the previous valid primary copy
    as the last-known-good backup.
    """

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

    current_value = await storage.get(
        JOURNEY_STORAGE_KEY
    )

    if current_value is not None:
        current_journey, _ = _prepare_stored_journey(
            current_value,
            source_label="Stored",
        )

        if current_journey is not None:
            backup_succeeded = await storage.set(
                JOURNEY_BACKUP_STORAGE_KEY,
                current_value,
            )

            # Do not risk replacing the known-good primary if we were unable
            # to preserve it first.
            if not backup_succeeded:
                return False

    save_succeeded = await storage.set(
        JOURNEY_STORAGE_KEY,
        serialized_journey,
    )

    if save_succeeded:
        journey.clear()
        journey.update(journey_to_save)

    return save_succeeded


async def clear_journey(
    storage: StorageBackend,
) -> bool:
    """Remove both the active Journey and its recovery backup."""

    primary_succeeded = True
    backup_succeeded = True

    if await storage.contains(JOURNEY_STORAGE_KEY):
        primary_succeeded = await storage.remove(
            JOURNEY_STORAGE_KEY
        )

    if await storage.contains(JOURNEY_BACKUP_STORAGE_KEY):
        backup_succeeded = await storage.remove(
            JOURNEY_BACKUP_STORAGE_KEY
        )

    return primary_succeeded and backup_succeeded