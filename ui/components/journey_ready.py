"""
Journey-ready component.

Displays the final onboarding screen after the player's starter has
been saved successfully.
"""

from __future__ import annotations

from collections.abc import Callable
from typing import cast

import flet as ft

from ui.theme import (
    BORDER_DEFAULT,
    CARD_RADIUS,
    PRIMARY_BLUE,
    SUCCESS,
    SURFACE,
    TEXT_MUTED,
    TEXT_PRIMARY,
    TEXT_SECONDARY,
)


class JourneyReady(ft.Container):
    """Final onboarding screen before entering the main application."""

    def __init__(
        self,
        *,
        on_continue: Callable[[], None],
    ) -> None:
        super().__init__()

        self.on_continue = on_continue

        self.content = self._build()

        self.width = 760
        self.padding = 36
        self.bgcolor = SURFACE
        self.border = ft.Border.all(
            1,
            BORDER_DEFAULT,
        )
        self.border_radius = CARD_RADIUS
        self.alignment = ft.Alignment.CENTER

    def _build(self) -> ft.Control:
        """Build the Journey-ready message and action."""

        return ft.Column(
            controls=cast(
                list[ft.Control],
                [
                    ft.Icon(
                        ft.Icons.AUTO_AWESOME_ROUNDED,
                        size=46,
                        color=SUCCESS,
                    ),
                    ft.Text(
                        "You’re ready for your Journey.",
                        size=30,
                        weight=ft.FontWeight.BOLD,
                        color=TEXT_PRIMARY,
                        text_align=ft.TextAlign.CENTER,
                    ),
                    ft.Text(
                        (
                            "The Battle Compass is ready to help "
                            "you navigate every matchup with "
                            "confidence."
                        ),
                        size=17,
                        color=TEXT_SECONDARY,
                        text_align=ft.TextAlign.CENTER,
                    ),
                    ft.Text(
                        "Let’s make you a Champion!",
                        size=22,
                        weight=ft.FontWeight.BOLD,
                        color=PRIMARY_BLUE,
                        text_align=ft.TextAlign.CENTER,
                    ),
                    ft.Text(
                        (
                            "You can update your team anytime from "
                            "My Team as your adventure continues. "
                            "In fact, keeping your team current after "
                            "every level-up, move change, Ability "
                            "change, or held item change is "
                            "recommended—it helps the Battle Compass "
                            "give you the most accurate recommendations "
                            "possible."
                        ),
                        size=14,
                        color=TEXT_MUTED,
                        text_align=ft.TextAlign.CENTER,
                    ),
                    ft.Button(
                        content="Let’s Go!",
                        icon=ft.Icons.ARROW_FORWARD_ROUNDED,
                        bgcolor=PRIMARY_BLUE,
                        color=TEXT_PRIMARY,
                        icon_color=TEXT_PRIMARY,
                        on_click=self._continue_clicked,
                    ),
                ],
            ),
            spacing=18,
            horizontal_alignment=ft.CrossAxisAlignment.CENTER,
        )

    def _continue_clicked(
        self,
        event: ft.Event[ft.Button],
    ) -> None:
        """Hand control back to the onboarding controller."""

        del event
        self.on_continue()