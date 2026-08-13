"""
Application-level Journey state.

Owns the active Journey and coordinates persistent storage without
placing application lifecycle responsibilities inside individual views.
"""

from __future__ import annotations
from ui.viewmodels.battle_compass_vm import (
    ReferenceData,
)

from copy import deepcopy
import json
from pathlib import Path
from typing import Any, Literal


from ui.storage.storage_backend import StorageBackend
from ui.storage.journey_storage import (
    JourneyLoadResult,
    clear_journey,
    create_journey,
    load_journey,
    save_journey,
)


DATA_DIR = Path(__file__).resolve().parents[2] / "data"


AppStartupState = Literal[
    "needs_onboarding",
    "ready",
    "invalid_save",
]


class AppState:
    """Own the active Journey and shared application data."""

    def __init__(
        self,
        *,
        storage: StorageBackend,
        reference_data: ReferenceData,
    ) -> None:
        self.storage = storage
        self.reference_data = reference_data

        self.journey: dict | None = None
        self.startup_state: AppStartupState = (
            "needs_onboarding"
        )
        self.load_error: str | None = None
        self.recovered_from_backup = False

    @property
    def starter(self) -> str | None:
        """Return the active Journey's selected starter."""

        if self.journey is None:
            return None

        starter = self.journey.get("starter")

        if isinstance(starter, str):
            return starter

        return None
    
    @property
    def battle_compass_selection(
        self,
    ) -> dict[str, str | None]:
        """Return the saved Battle Compass selection."""

        empty_selection: dict[
            str,
            str | None,
        ] = {
            "trainer": None,
            "battle": None,
            "opponent": None,
        }

        if self.journey is None:
            return empty_selection

        selection = self.journey.get(
            "battle_compass_selection"
        )

        if not isinstance(selection, dict):
            return empty_selection

        return {
            "trainer": (
                selection.get("trainer")
                if isinstance(
                    selection.get("trainer"),
                    str,
                )
                else None
            ),
            "battle": (
                selection.get("battle")
                if isinstance(
                    selection.get("battle"),
                    str,
                )
                else None
            ),
            "opponent": (
                selection.get("opponent")
                if isinstance(
                    selection.get("opponent"),
                    str,
                )
                else None
            ),
        }

    @property
    def active_view(self) -> str:
        """Return the last primary application view saved in the Journey."""

        if self.journey is None:
            return "battle_compass"

        active_view = self.journey.get("active_view")

        if isinstance(active_view, str) and active_view:
            return active_view

        return "battle_compass"

    @property
    def my_journey_data(self) -> dict:
        """Return normalized player-owned My Journey state."""

        default_state = {
            "earned_badges": 0,
            "checklist_initialized": False,
            "planner_initialized": False,
            "planned_pokemon_ids": [],
            "item_objectives": [],
            "pokemon_objectives": [],
            "hide_obtained_items": False,
            "hide_obtained_pokemon": False,
        }

        if self.journey is None:
            return default_state

        my_journey = self.journey.get("my_journey")
        if not isinstance(my_journey, dict):
            return default_state

        earned_badges = my_journey.get("earned_badges", 0)
        if (
            not isinstance(earned_badges, int)
            or isinstance(earned_badges, bool)
            or not 0 <= earned_badges <= 8
        ):
            earned_badges = 0

        checklist_initialized = my_journey.get(
            "checklist_initialized",
            False,
        )
        if not isinstance(checklist_initialized, bool):
            checklist_initialized = False

        planner_initialized = my_journey.get(
            "planner_initialized",
            False,
        )
        if not isinstance(planner_initialized, bool):
            planner_initialized = False

        planned_pokemon_ids = my_journey.get(
            "planned_pokemon_ids",
            [],
        )
        if not isinstance(planned_pokemon_ids, list):
            planned_pokemon_ids = []
        planned_pokemon_ids = [
            pokemon_id
            for pokemon_id in planned_pokemon_ids
            if isinstance(pokemon_id, str) and pokemon_id.strip()
        ]

        item_objectives = my_journey.get("item_objectives", [])
        if not isinstance(item_objectives, list):
            item_objectives = []

        pokemon_objectives = my_journey.get(
            "pokemon_objectives",
            [],
        )
        if not isinstance(pokemon_objectives, list):
            pokemon_objectives = []

        hide_obtained_items = my_journey.get(
            "hide_obtained_items",
            False,
        )
        if not isinstance(hide_obtained_items, bool):
            hide_obtained_items = False

        hide_obtained_pokemon = my_journey.get(
            "hide_obtained_pokemon",
            False,
        )
        if not isinstance(hide_obtained_pokemon, bool):
            hide_obtained_pokemon = False

        return {
            "earned_badges": earned_badges,
            "checklist_initialized": checklist_initialized,
            "planner_initialized": planner_initialized,
            "planned_pokemon_ids": planned_pokemon_ids,
            "item_objectives": item_objectives,
            "pokemon_objectives": pokemon_objectives,
            "hide_obtained_items": hide_obtained_items,
            "hide_obtained_pokemon": hide_obtained_pokemon,
        }

    @property
    def earned_badges(self) -> int:
        """Return the number of earned Galar badges."""

        return int(self.my_journey_data["earned_badges"])


    def get_item_quantity_obtained(
        self,
        item_id: str,
    ) -> int:
        """Return saved obtained quantity for a Journey item objective."""

        for record in self.my_journey_data["item_objectives"]:
            if (
                isinstance(record, dict)
                and record.get("id") == item_id
            ):
                quantity = record.get("quantity_obtained", 0)
                if (
                    isinstance(quantity, int)
                    and not isinstance(quantity, bool)
                    and quantity >= 0
                ):
                    return quantity
        return 0

    def is_pokemon_obtained(
        self,
        pokemon_id: str,
    ) -> bool:
        """Return whether a planned Pokémon has been marked caught."""

        for record in self.my_journey_data["pokemon_objectives"]:
            if (
                isinstance(record, dict)
                and record.get("id") == pokemon_id
            ):
                return record.get("obtained") is True
        return False

    @property
    def team_data(self) -> list[dict]:
        """Return the active Journey's mutable team list."""

        if self.journey is None:
            return []

        team = self.journey.get("team")

        if not isinstance(team, list):
            return []

        return team

    @property
    def box_data(self) -> list[dict]:
        """Return the active Journey's boxed Pokémon list."""

        if self.journey is None:
            return []

        box = self.journey.get("box")

        if not isinstance(box, list):
            box = []
            self.journey["box"] = box

        return box

    @property
    def moves_data(self) -> list[dict]:
        """Return bundled move reference data."""

        return self.reference_data["moves_data"]

    @property
    def has_journey(self) -> bool:
        """Return whether a Journey currently exists."""

        return self.journey is not None

    @property
    def has_team_member(self) -> bool:
        """Return whether the Journey has a named Pokémon."""

        return any(
            isinstance(pokemon, dict)
            and isinstance(
                pokemon.get("Pokemon"),
                str,
            )
            and bool(
                pokemon["Pokemon"].strip()
            )
            for pokemon in self.team_data
        )

    @property
    def is_ready(self) -> bool:
        """Return whether the normal application may be shown."""

        return (
            self.startup_state == "ready"
            and self.has_journey
            and self.has_team_member
        )

    async def initialize(self) -> AppStartupState:
        """Load persistent Journey state during application startup."""

        result = await load_journey(
            self.storage
        )

        self._apply_load_result(result)

        return self.startup_state

    def _apply_load_result(
        self,
        result: JourneyLoadResult,
    ) -> None:
        """Apply a Journey storage result to application state."""

        self.load_error = result.error
        self.recovered_from_backup = (
            result.recovered_from_backup
        )

        if (
            result.status == "valid"
            and result.journey is not None
        ):
            self.journey = result.journey

            self.startup_state = (
                "ready"
                if self.has_team_member
                else "needs_onboarding"
            )

            return

        self.journey = None

        if result.status == "invalid":
            self.startup_state = "invalid_save"
        else:
            self.startup_state = (
                "needs_onboarding"
            )

    def use_example_journey(
        self,
        *,
        starter: str,
        team_data: list[dict],
    ) -> None:
        """
        Load bundled example data for the current session.

        This temporary bridge does not write to persistent storage.
        """

        self.journey = create_journey(
            starter=starter,
            team=team_data,
        )

        self.startup_state = (
            "ready"
            if self.has_team_member
            else "needs_onboarding"
        )

        self.load_error = None
        self.recovered_from_backup = False

    async def replace_journey(
        self,
        *,
        starter: str,
        team_data: list[dict],
    ) -> bool:
        """
        Persist a complete replacement Journey.

        The current Journey remains active unless the replacement is
        saved successfully.
        """

        replacement_journey = create_journey(
            starter=starter,
            team=deepcopy(team_data),
        )

        save_succeeded = await save_journey(
            self.storage,
            replacement_journey,
        )

        if not save_succeeded:
            return False

        self.journey = replacement_journey
        self.startup_state = (
            "ready"
            if self.has_team_member
            else "needs_onboarding"
        )
        self.load_error = None
        self.recovered_from_backup = False

        return True

    def get_journey_export_copy(self) -> dict:
        """
        Return an isolated copy of the active saved Journey.

        Unsaved My Team editor changes are intentionally excluded.
        """

        if self.journey is None:
            raise RuntimeError(
                "No Journey is currently available to export."
            )

        return deepcopy(self.journey)

    async def import_journey(
        self,
        journey: dict,
    ) -> bool:
        """
        Persist and activate a complete imported Journey.

        The currently active Journey remains unchanged unless the imported
        Journey is saved successfully.
        """

        imported_journey = deepcopy(journey)

        save_succeeded = await save_journey(
            self.storage,
            imported_journey,
        )

        if not save_succeeded:
            return False

        self.journey = imported_journey
        self.startup_state = (
            "ready"
            if self.has_team_member
            else "needs_onboarding"
        )
        self.load_error = None

        return True

    async def begin_journey(
        self,
        starter: str,
    ) -> bool:
        """
        Create and persist a new empty Journey.

        Retained for compatibility. Onboarding should prefer
        replace_journey() after starter details have been completed.
        """

        return await self.replace_journey(
            starter=starter,
            team_data=[],
        )

    async def save_team(
        self,
        team_data: list[dict],
    ) -> bool:
        """Save team data into the active Journey."""

        if self.journey is None:
            raise RuntimeError(
                "A Journey must exist before a team can be saved."
            )

        previous_team = deepcopy(
            self.team_data
        )

        updated_team = deepcopy(
            team_data
        )

        self.journey["team"] = updated_team

        save_succeeded = await save_journey(
            self.storage,
            self.journey,
        )

        if not save_succeeded:
            self.journey["team"] = previous_team
            return False

        self.startup_state = (
            "ready"
            if self.has_team_member
            else "needs_onboarding"
        )

        return True
    

    @staticmethod
    def _normalize_pokemon_name(value: object) -> str:
        """Return a comparison-safe Pokémon name."""

        normalized = str(value or "").strip().casefold()
        for prefix in ("galarian ", "alolan ", "hisuian ", "paldean "):
            if normalized.startswith(prefix):
                normalized = normalized[len(prefix):]
                break
        return normalized

    @classmethod
    def _planned_pokemon_matches_owned_record(
        cls,
        planned: dict[str, Any],
        owned: dict[str, Any],
    ) -> bool:
        """Return whether a party/Box record satisfies a Journey plan."""

        owned_name = cls._normalize_pokemon_name(owned.get("Pokemon"))
        if not owned_name:
            return False

        valid_names = {
            cls._normalize_pokemon_name(planned.get("pokemon")),
            cls._normalize_pokemon_name(planned.get("acquire_as")),
        }

        for step in planned.get("evolution_steps", []):
            if not isinstance(step, dict):
                continue
            valid_names.add(cls._normalize_pokemon_name(step.get("from")))
            valid_names.add(cls._normalize_pokemon_name(step.get("to")))

        valid_names.discard("")
        if owned_name not in valid_names:
            return False

        requirement = str(
            planned.get("acquisition_requirement", "")
        ).strip().casefold()
        if "female" in requirement:
            return str(owned.get("Gender", "")).strip().casefold() == "female"

        return True

    def _sync_pokemon_objectives_from_owned_pokemon(
        self,
        team_data: list[dict],
        box_data: list[dict],
    ) -> None:
        """Synchronize acquired objectives to Pokémon currently owned."""

        journey = self.journey
        if journey is None:
            return

        try:
            with (DATA_DIR / "journey_pokemon.json").open(
                "r",
                encoding="utf-8",
            ) as file:
                planned_pokemon = json.load(file)
        except (OSError, json.JSONDecodeError):
            return

        if not isinstance(planned_pokemon, list):
            return

        owned_pokemon = [
            record
            for record in [*team_data, *box_data]
            if isinstance(record, dict)
        ]

        acquired_records: list[dict[str, object]] = []
        for planned in planned_pokemon:
            if not isinstance(planned, dict):
                continue

            pokemon_id = str(planned.get("id", "")).strip()
            if not pokemon_id:
                continue

            if any(
                self._planned_pokemon_matches_owned_record(
                    planned,
                    owned,
                )
                for owned in owned_pokemon
            ):
                acquired_records.append({
                    "id": pokemon_id,
                    "obtained": True,
                })

        updated_my_journey = deepcopy(self.my_journey_data)
        updated_my_journey["pokemon_objectives"] = acquired_records
        journey["my_journey"] = updated_my_journey

    async def save_team_and_box(
        self,
        team_data: list[dict],
        box_data: list[dict],
    ) -> bool:
        """Atomically save active-party and boxed Pokémon data."""

        if self.journey is None:
            raise RuntimeError(
                "A Journey must exist before Pokémon can be saved."
            )

        previous_team = deepcopy(self.team_data)
        previous_box = deepcopy(self.box_data)
        previous_my_journey = deepcopy(self.journey.get("my_journey"))

        self.journey["team"] = deepcopy(team_data)
        self.journey["box"] = deepcopy(box_data)
        self._sync_pokemon_objectives_from_owned_pokemon(
            team_data,
            box_data,
        )

        save_succeeded = await save_journey(
            self.storage,
            self.journey,
        )

        if not save_succeeded:
            self.journey["team"] = previous_team
            self.journey["box"] = previous_box
            if previous_my_journey is None:
                self.journey.pop("my_journey", None)
            else:
                self.journey["my_journey"] = previous_my_journey
            return False

        self.startup_state = (
            "ready"
            if self.has_team_member
            else "needs_onboarding"
        )
        return True

    async def save_battle_compass_selection(
        self,
        *,
        trainer: str,
        battle: str,
        opponent: str,
    ) -> bool:
        """Persist the current Battle Compass dropdown selection."""

        if self.journey is None:
            return False

        previous_selection = deepcopy(
            self.journey.get(
                "battle_compass_selection"
            )
        )

        self.journey[
            "battle_compass_selection"
        ] = {
            "trainer": trainer,
            "battle": battle,
            "opponent": opponent,
        }

        save_succeeded = await save_journey(
            self.storage,
            self.journey,
        )

        if not save_succeeded:
            if previous_selection is None:
                self.journey.pop(
                    "battle_compass_selection",
                    None,
                )
            else:
                self.journey[
                    "battle_compass_selection"
                ] = previous_selection

        return save_succeeded

    async def save_active_view(
        self,
        view_name: str,
    ) -> bool:
        """Persist primary-page navigation independently of team drafts."""

        if self.journey is None:
            return False

        previous_view = self.journey.get("active_view")
        self.journey["active_view"] = view_name

        try:
            save_succeeded = await save_journey(
                self.storage,
                self.journey,
            )
        except ValueError:
            if previous_view is None:
                self.journey.pop("active_view", None)
            else:
                self.journey["active_view"] = previous_view
            raise

        if not save_succeeded:
            if previous_view is None:
                self.journey.pop("active_view", None)
            else:
                self.journey["active_view"] = previous_view

        return save_succeeded

    async def save_journey_filter_preferences(
        self,
        *,
        hide_obtained_items: bool,
        hide_obtained_pokemon: bool,
    ) -> bool:
        """Persist My Journey display-filter preferences."""

        if self.journey is None:
            return False

        if not isinstance(hide_obtained_items, bool):
            raise ValueError(
                "Hide Obtained Items preference must be boolean."
            )
        if not isinstance(hide_obtained_pokemon, bool):
            raise ValueError(
                "Hide Obtained Pokémon preference must be boolean."
            )

        previous_my_journey = deepcopy(
            self.journey.get("my_journey")
        )
        updated_my_journey = deepcopy(self.my_journey_data)
        updated_my_journey["hide_obtained_items"] = (
            hide_obtained_items
        )
        updated_my_journey["hide_obtained_pokemon"] = (
            hide_obtained_pokemon
        )
        self.journey["my_journey"] = updated_my_journey

        try:
            save_succeeded = await save_journey(
                self.storage,
                self.journey,
            )
        except ValueError:
            if previous_my_journey is None:
                self.journey.pop("my_journey", None)
            else:
                self.journey["my_journey"] = previous_my_journey
            raise

        if not save_succeeded:
            if previous_my_journey is None:
                self.journey.pop("my_journey", None)
            else:
                self.journey["my_journey"] = previous_my_journey

        return save_succeeded


    async def save_earned_badges(
        self,
        earned_badges: int,
    ) -> bool:
        """Persist sequential Galar badge progress."""

        if self.journey is None:
            return False

        if (
            not isinstance(earned_badges, int)
            or isinstance(earned_badges, bool)
            or not 0 <= earned_badges <= 8
        ):
            raise ValueError(
                "Earned badges must be an integer from 0 through 8."
            )

        previous_my_journey = deepcopy(
            self.journey.get("my_journey")
        )
        updated_my_journey = deepcopy(
            self.my_journey_data
        )
        updated_my_journey["earned_badges"] = earned_badges
        self.journey["my_journey"] = updated_my_journey

        try:
            save_succeeded = await save_journey(
                self.storage,
                self.journey,
            )
        except ValueError:
            if previous_my_journey is None:
                self.journey.pop("my_journey", None)
            else:
                self.journey["my_journey"] = (
                    previous_my_journey
                )
            raise

        if not save_succeeded:
            if previous_my_journey is None:
                self.journey.pop("my_journey", None)
            else:
                self.journey["my_journey"] = (
                    previous_my_journey
                )

        return save_succeeded


    async def save_item_objective_quantity(
        self,
        *,
        item_id: str,
        quantity_obtained: int,
    ) -> bool:
        """Persist quantity progress for one Journey item objective."""

        if self.journey is None:
            return False
        if not item_id.strip():
            raise ValueError("Item objective ID cannot be empty.")
        if (
            not isinstance(quantity_obtained, int)
            or isinstance(quantity_obtained, bool)
            or quantity_obtained < 0
        ):
            raise ValueError("Item quantity must be a non-negative integer.")

        previous_my_journey = deepcopy(self.journey.get("my_journey"))
        updated_my_journey = deepcopy(self.my_journey_data)
        records = [
            record
            for record in updated_my_journey["item_objectives"]
            if not (isinstance(record, dict) and record.get("id") == item_id)
        ]
        if quantity_obtained > 0:
            records.append({
                "id": item_id,
                "quantity_obtained": quantity_obtained,
            })
        updated_my_journey["item_objectives"] = records
        self.journey["my_journey"] = updated_my_journey

        try:
            save_succeeded = await save_journey(self.storage, self.journey)
        except ValueError:
            if previous_my_journey is None:
                self.journey.pop("my_journey", None)
            else:
                self.journey["my_journey"] = previous_my_journey
            raise

        if not save_succeeded:
            if previous_my_journey is None:
                self.journey.pop("my_journey", None)
            else:
                self.journey["my_journey"] = previous_my_journey
        return save_succeeded

    async def save_item_checklist(
        self,
        records: list[dict],
    ) -> bool:
        """Persist the complete editable Journey Checklist state."""

        if self.journey is None:
            return False
        if not isinstance(records, list):
            raise ValueError("Item objectives must be a list.")

        normalized_records: list[dict] = []
        seen_ids: set[str] = set()

        for record in records:
            if not isinstance(record, dict):
                raise ValueError("Each item objective must be an object.")

            item_id = str(record.get("id", "")).strip()
            if not item_id or item_id in seen_ids:
                raise ValueError("Item objective IDs must be unique.")

            quantity_obtained = record.get("quantity_obtained", 0)
            manual_quantity_required = record.get(
                "manual_quantity_required",
                0,
            )

            for value, label in (
                (quantity_obtained, "obtained quantity"),
                (manual_quantity_required, "manual required quantity"),
            ):
                if (
                    not isinstance(value, int)
                    or isinstance(value, bool)
                    or value < 0
                ):
                    raise ValueError(
                        f"Item objective {label} must be a "
                        "non-negative integer."
                    )

            normalized_records.append({
                "id": item_id,
                "quantity_obtained": quantity_obtained,
                "manual_quantity_required": manual_quantity_required,
            })
            seen_ids.add(item_id)

        previous_my_journey = deepcopy(
            self.journey.get("my_journey")
        )
        updated_my_journey = deepcopy(self.my_journey_data)
        updated_my_journey["checklist_initialized"] = True
        updated_my_journey["item_objectives"] = normalized_records
        self.journey["my_journey"] = updated_my_journey

        try:
            save_succeeded = await save_journey(
                self.storage,
                self.journey,
            )
        except ValueError:
            if previous_my_journey is None:
                self.journey.pop("my_journey", None)
            else:
                self.journey["my_journey"] = previous_my_journey
            raise

        if not save_succeeded:
            if previous_my_journey is None:
                self.journey.pop("my_journey", None)
            else:
                self.journey["my_journey"] = previous_my_journey

        return save_succeeded


    async def add_manual_item_objective(
        self,
        *,
        item_id: str,
        quantity: int = 1,
    ) -> bool:
        """Add or increment one manually selected Journey Checklist item."""

        if self.journey is None:
            return False
        if not item_id.strip():
            raise ValueError("Item objective ID cannot be empty.")
        if (
            not isinstance(quantity, int)
            or isinstance(quantity, bool)
            or quantity <= 0
        ):
            raise ValueError("Item quantity must be a positive integer.")

        journey_items_path = DATA_DIR / "journey_items.json"
        journey_pokemon_path = DATA_DIR / "journey_pokemon.json"

        try:
            journey_items = json.loads(
                journey_items_path.read_text(encoding="utf-8")
            )
            journey_pokemon = json.loads(
                journey_pokemon_path.read_text(encoding="utf-8")
            )
        except (OSError, UnicodeError, json.JSONDecodeError) as error:
            raise RuntimeError(
                "Journey reference data could not be loaded."
            ) from error

        if not isinstance(journey_items, list):
            raise RuntimeError("Journey item reference data is invalid.")
        if not isinstance(journey_pokemon, list):
            raise RuntimeError("Journey Pokémon reference data is invalid.")

        catalog_by_id = {
            str(item.get("id", "")).strip(): item
            for item in journey_items
            if isinstance(item, dict)
            and str(item.get("id", "")).strip()
        }
        if item_id not in catalog_by_id:
            raise ValueError(
                "That held item is not yet available in the Journey catalog."
            )

        derived_requirements: dict[str, int] = {}
        for pokemon in journey_pokemon:
            if not isinstance(pokemon, dict):
                continue
            for requirement in pokemon.get("required_items", []):
                if not isinstance(requirement, dict):
                    continue
                required_item_id = str(
                    requirement.get("item_id", "")
                ).strip()
                required_quantity = requirement.get("quantity", 0)
                if (
                    required_item_id
                    and isinstance(required_quantity, int)
                    and not isinstance(required_quantity, bool)
                    and required_quantity > 0
                ):
                    derived_requirements[required_item_id] = (
                        derived_requirements.get(required_item_id, 0)
                        + required_quantity
                    )

        previous_my_journey = deepcopy(
            self.journey.get("my_journey")
        )
        updated_my_journey = deepcopy(self.my_journey_data)
        initialized = (
            updated_my_journey.get("checklist_initialized") is True
        )
        existing_records = updated_my_journey.get(
            "item_objectives",
            [],
        )
        records_by_id: dict[str, dict] = {
            str(record.get("id", "")).strip(): deepcopy(record)
            for record in existing_records
            if isinstance(record, dict)
            and str(record.get("id", "")).strip()
        }

        if not initialized:
            for catalog_id, item in catalog_by_id.items():
                catalog_required = item.get("quantity_required", 1)
                if (
                    not isinstance(catalog_required, int)
                    or isinstance(catalog_required, bool)
                    or catalog_required < 1
                ):
                    catalog_required = 1

                legacy = records_by_id.get(catalog_id, {})
                obtained = legacy.get("quantity_obtained", 0)
                if (
                    not isinstance(obtained, int)
                    or isinstance(obtained, bool)
                    or obtained < 0
                ):
                    obtained = 0

                records_by_id[catalog_id] = {
                    "id": catalog_id,
                    "quantity_obtained": obtained,
                    "manual_quantity_required": max(
                        0,
                        catalog_required
                        - derived_requirements.get(catalog_id, 0),
                    ),
                }

        target = records_by_id.setdefault(
            item_id,
            {
                "id": item_id,
                "quantity_obtained": 0,
                "manual_quantity_required": 0,
            },
        )
        manual_quantity = target.get(
            "manual_quantity_required",
            0,
        )
        if (
            not isinstance(manual_quantity, int)
            or isinstance(manual_quantity, bool)
            or manual_quantity < 0
        ):
            manual_quantity = 0
        target["manual_quantity_required"] = manual_quantity + quantity

        normalized_records: list[dict] = []
        for record_id, record in records_by_id.items():
            obtained = record.get("quantity_obtained", 0)
            manual = record.get("manual_quantity_required", 0)
            if (
                not isinstance(obtained, int)
                or isinstance(obtained, bool)
                or obtained < 0
            ):
                obtained = 0
            if (
                not isinstance(manual, int)
                or isinstance(manual, bool)
                or manual < 0
            ):
                manual = 0

            required_total = (
                manual + derived_requirements.get(record_id, 0)
            )
            if required_total <= 0:
                continue

            normalized_records.append({
                "id": record_id,
                "quantity_obtained": min(obtained, required_total),
                "manual_quantity_required": manual,
            })

        updated_my_journey["checklist_initialized"] = True
        updated_my_journey["item_objectives"] = normalized_records
        self.journey["my_journey"] = updated_my_journey

        try:
            save_succeeded = await save_journey(
                self.storage,
                self.journey,
            )
        except ValueError:
            if previous_my_journey is None:
                self.journey.pop("my_journey", None)
            else:
                self.journey["my_journey"] = previous_my_journey
            raise

        if not save_succeeded:
            if previous_my_journey is None:
                self.journey.pop("my_journey", None)
            else:
                self.journey["my_journey"] = previous_my_journey

        return save_succeeded


    async def save_planned_pokemon_ids(
        self,
        pokemon_ids: list[str],
    ) -> bool:
        """Persist the ordered Pokémon IDs selected for Team Planner."""

        if self.journey is None:
            return False
        if not isinstance(pokemon_ids, list):
            raise ValueError("Planned Pokémon IDs must be a list.")

        normalized_ids: list[str] = []
        seen_ids: set[str] = set()
        for raw_id in pokemon_ids:
            if not isinstance(raw_id, str):
                raise ValueError("Each planned Pokémon ID must be text.")
            pokemon_id = raw_id.strip()
            if not pokemon_id:
                raise ValueError("Planned Pokémon IDs cannot be empty.")
            if pokemon_id in seen_ids:
                raise ValueError("Planned Pokémon IDs must be unique.")
            normalized_ids.append(pokemon_id)
            seen_ids.add(pokemon_id)

        previous_my_journey = deepcopy(
            self.journey.get("my_journey")
        )
        updated_my_journey = deepcopy(self.my_journey_data)
        updated_my_journey["planner_initialized"] = True
        updated_my_journey["planned_pokemon_ids"] = normalized_ids
        self.journey["my_journey"] = updated_my_journey

        try:
            save_succeeded = await save_journey(
                self.storage,
                self.journey,
            )
        except ValueError:
            if previous_my_journey is None:
                self.journey.pop("my_journey", None)
            else:
                self.journey["my_journey"] = previous_my_journey
            raise

        if not save_succeeded:
            if previous_my_journey is None:
                self.journey.pop("my_journey", None)
            else:
                self.journey["my_journey"] = previous_my_journey

        return save_succeeded

    async def save_pokemon_objective(
        self,
        *,
        pokemon_id: str,
        obtained: bool,
    ) -> bool:
        """Persist caught status for one planned Pokémon objective."""

        if self.journey is None:
            return False
        if not pokemon_id.strip():
            raise ValueError("Pokémon objective ID cannot be empty.")
        if not isinstance(obtained, bool):
            raise ValueError("Pokémon obtained state must be boolean.")

        previous_my_journey = deepcopy(self.journey.get("my_journey"))
        updated_my_journey = deepcopy(self.my_journey_data)
        records = [
            record
            for record in updated_my_journey["pokemon_objectives"]
            if not (isinstance(record, dict) and record.get("id") == pokemon_id)
        ]
        if obtained:
            records.append({
                "id": pokemon_id,
                "obtained": True,
            })
        updated_my_journey["pokemon_objectives"] = records
        self.journey["my_journey"] = updated_my_journey

        try:
            save_succeeded = await save_journey(self.storage, self.journey)
        except ValueError:
            if previous_my_journey is None:
                self.journey.pop("my_journey", None)
            else:
                self.journey["my_journey"] = previous_my_journey
            raise

        if not save_succeeded:
            if previous_my_journey is None:
                self.journey.pop("my_journey", None)
            else:
                self.journey["my_journey"] = previous_my_journey
        return save_succeeded

    async def set_starter(
        self,
        starter: str,
    ) -> bool:
        """Update the active Journey's selected starter."""

        if self.journey is None:
            return await self.begin_journey(
                starter
            )

        previous_starter = self.journey.get(
            "starter"
        )

        self.journey["starter"] = starter

        try:
            save_succeeded = await save_journey(
                self.storage,
                self.journey,
            )
        except ValueError:
            self.journey["starter"] = (
                previous_starter
            )
            raise

        if not save_succeeded:
            self.journey["starter"] = (
                previous_starter
            )

        return save_succeeded

    async def start_new_journey(
        self,
        starter: str,
    ) -> bool:
        """
        Replace the current Journey with a new empty Journey.

        Call this only after the player has confirmed that the existing
        Journey should be replaced.
        """

        return await self.replace_journey(
            starter=starter,
            team_data=[],
        )

    async def clear_current_journey(self) -> bool:
        """Clear persistent and in-memory Journey state."""

        clear_succeeded = await clear_journey(
            self.storage
        )

        if not clear_succeeded:
            return False

        self.journey = None
        self.startup_state = (
            "needs_onboarding"
        )
        self.load_error = None

        return True