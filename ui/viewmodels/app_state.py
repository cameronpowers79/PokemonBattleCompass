"""
Application-level Journey state.

Owns the active Journey and coordinates persistent storage without
placing application lifecycle responsibilities inside individual views.
"""

from __future__ import annotations

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
        reference_data: dict[str, list[dict]],
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