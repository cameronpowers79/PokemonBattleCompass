"""
Journey onboarding view.

Coordinates starter selection, starter details, and Journey completion.
The existing Journey is not replaced until the player finishes entering
and validates the new starter's information.
"""

from __future__ import annotations

from collections.abc import Callable
from typing import cast

import flet as ft

from ui.components.journey_ready import JourneyReady
from ui.components.starter_details import StarterDetails
from ui.components.starter_selection import StarterSelection
from ui.theme import (
    APP_BACKGROUND,
    CONTENT_MAX_WIDTH,
)
from ui.viewmodels.app_state import AppState


STARTER_DEFAULTS = {
    "Grookey": {
        "Type1": "Grass",
        "Ability": "Overgrow",
        "Move1": "Scratch",
        "Move2": "Growl",
    },
    "Scorbunny": {
        "Type1": "Fire",
        "Ability": "Blaze",
        "Move1": "Tackle",
        "Move2": "Growl",
    },
    "Sobble": {
        "Type1": "Water",
        "Ability": "Torrent",
        "Move1": "Pound",
        "Move2": "Growl",
    },
}


class OnboardingView:
    """Coordinate the first-use Journey onboarding flow."""

    def __init__(
        self,
        page: ft.Page,
        *,
        app_state: AppState,
        on_complete: Callable[[], None],
    ) -> None:
        self.page = page
        self.app_state = app_state
        self.on_complete = on_complete

        self.pending_starter: str | None = None
        self.starter_details: StarterDetails | None = None

        initial_content: ft.Control

        if (
            not app_state.has_team_member
            and app_state.starter in STARTER_DEFAULTS
        ):
            self.pending_starter = app_state.starter
            initial_content = self._build_starter_details(
                app_state.starter
            )
        else:
            initial_content = self._build_starter_selection()

        self.content_host = ft.Container(
            content=initial_content,
            width=CONTENT_MAX_WIDTH,
            alignment=ft.Alignment.TOP_CENTER,
        )

    def build(self) -> ft.Control:
        """Return the complete onboarding view."""

        return ft.Container(
            content=ft.SafeArea(
                content=ft.Column(
                    controls=cast(
                        list[ft.Control],
                        [
                            self._build_branding_header(),
                            self.content_host,
                        ],
                    ),
                    spacing=28,
                    horizontal_alignment=(
                        ft.CrossAxisAlignment.CENTER
                    ),
                ),
            ),
            expand=True,
            bgcolor=APP_BACKGROUND,
            padding=28,
            alignment=ft.Alignment.TOP_CENTER,
        )

    @staticmethod
    def _build_branding_header() -> ft.Control:
        """Build the onboarding branding header."""

        return ft.Column(
            controls=cast(
                list[ft.Control],
                [
                    ft.Image(
                        src="raw/BattleCompassLogo.png",
                        width=112,
                        fit=ft.BoxFit.CONTAIN,
                        semantics_label="Battle Compass logo",
                    ),
                    ft.Image(
                        src="raw/WordMarkLogoBlock.png",
                        width=620,
                        fit=ft.BoxFit.CONTAIN,
                        semantics_label="Pokémon Battle Compass",
                    ),
                ],
            ),
            spacing=8,
            horizontal_alignment=ft.CrossAxisAlignment.CENTER,
        )

    def _build_starter_selection(self) -> ft.Control:
        """Build the starter-selection component."""

        return StarterSelection(
            starter_defaults=STARTER_DEFAULTS,
            on_selected=self._handle_starter_selected,
        )

    def _build_starter_details(
        self,
        starter_name: str | None,
    ) -> ft.Control:
        """Build the starter-details component."""

        if (
            starter_name is None
            or starter_name not in STARTER_DEFAULTS
        ):
            return self._build_starter_selection()

        self.starter_details = StarterDetails(
            starter_name=starter_name,
            starter_defaults=STARTER_DEFAULTS[
                starter_name
            ],
            moves_data=self.app_state.moves_data,
            on_completed=self._starter_ready,
        )

        return self.starter_details

    def _handle_starter_selected(
        self,
        starter_name: str,
    ) -> None:
        """
        Open starter details without changing persistent Journey data.

        The selected starter remains pending until the player completes
        and validates the starter-details form.
        """

        if starter_name not in STARTER_DEFAULTS:
            return

        self.pending_starter = starter_name

        self.content_host.content = (
            self._build_starter_details(
                starter_name
            )
        )

        self.page.update()

    def _starter_ready(
        self,
        starter_record: dict,
    ) -> None:
        """Begin saving the completed replacement Journey."""

        if self.pending_starter is None:
            if self.starter_details is not None:
                self.starter_details.show_save_error(
                    "No starter is selected. "
                    "Please return to starter selection."
                )
            return

        self.page.run_task(
            self._replace_journey,
            starter_record,
        )

    async def _replace_journey(
        self,
        starter_record: dict,
    ) -> None:
        """
        Atomically replace the active Journey after onboarding finishes.

        Until this succeeds, any previously saved Journey remains intact.
        """

        if self.pending_starter is None:
            return

        save_succeeded = await self.app_state.replace_journey(
            starter=self.pending_starter,
            team_data=[
                starter_record
            ],
        )

        if not save_succeeded:
            if self.starter_details is not None:
                self.starter_details.show_save_error(
                    "Your Journey could not be saved. "
                    "Your previous Journey is still safe. "
                    "Please try again."
                )
            return

        self._show_journey_ready()

    def _show_journey_ready(self) -> None:
        """Show the final onboarding screen."""

        self.content_host.content = JourneyReady(
            on_continue=self.on_complete,
        )

        self.page.update()