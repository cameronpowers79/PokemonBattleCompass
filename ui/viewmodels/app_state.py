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
from typing import Literal

import flet as ft

from ui.storage.journey_storage import (
    JourneyLoadResult,
    clear_journey,
    create_journey,
    load_journey,
    save_journey,
)


AppStartupState = Literal[
    "needs_onboarding",
    "ready",
    "invalid_save",
]


class AppState:
    """Own the active Journey and shared application data."""

    def __init__(
        self,
        page: ft.Page,
        *,
        reference_data: ReferenceData,
    ) -> None:
        self.page = page
        self.reference_data = reference_data

        self.journey: dict | None = None
        self.startup_state: AppStartupState = (
            "needs_onboarding"
        )
        self.load_error: str | None = None

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
            "item_objectives": [],
            "pokemon_objectives": [],
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

        item_objectives = my_journey.get("item_objectives", [])
        if not isinstance(item_objectives, list):
            item_objectives = []

        pokemon_objectives = my_journey.get(
            "pokemon_objectives",
            [],
        )
        if not isinstance(pokemon_objectives, list):
            pokemon_objectives = []

        return {
            "earned_badges": earned_badges,
            "item_objectives": item_objectives,
            "pokemon_objectives": pokemon_objectives,
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
            self.page
        )

        self._apply_load_result(result)

        return self.startup_state

    def _apply_load_result(
        self,
        result: JourneyLoadResult,
    ) -> None:
        """Apply a Journey storage result to application state."""

        self.load_error = result.error

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
            self.page,
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
            self.page,
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
            self.page,
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
            self.page,
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
                self.page,
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
                self.page,
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
            save_succeeded = await save_journey(self.page, self.journey)
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
            save_succeeded = await save_journey(self.page, self.journey)
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
                self.page,
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
            self.page
        )

        if not clear_succeeded:
            return False

        self.journey = None
        self.startup_state = (
            "needs_onboarding"
        )
        self.load_error = None

        return True