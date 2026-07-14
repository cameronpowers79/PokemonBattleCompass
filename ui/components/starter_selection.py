"""
Starter selection component.

Displays the first screen of the Journey onboarding flow where the
player chooses their starter Pokémon.
"""

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path
from typing import cast

import flet as ft

from ui.rendering import get_sprite_path
from ui.theme import (
    BORDER_DEFAULT,
    CARD_RADIUS,
    PRIMARY_BLUE,
    PRIMARY_BLUE_SOFT,
    SURFACE,
    SURFACE_RAISED,
    TEXT_MUTED,
    TEXT_PRIMARY,
    TEXT_SECONDARY,
)


PROJECT_ROOT = Path(__file__).resolve().parents[2]
ASSETS_DIR = PROJECT_ROOT / "assets"


class StarterSelection(ft.Container):
    """Starter selection screen."""

    def __init__(
        self,
        *,
        starter_defaults: dict[str, dict],
        on_selected: Callable[[str], None],
    ) -> None:
        super().__init__()

        self._starter_defaults = starter_defaults
        self._on_selected = on_selected

        self.selected_starter: str | None = None
        self.cards: dict[str, ft.Container] = {}

        self.status_text = ft.Text(
            "",
            size=14,
            color=TEXT_MUTED,
            text_align=ft.TextAlign.CENTER,
        )

        self.continue_button = ft.Button(
            content="Choose a Partner",
            icon=ft.Icons.ARROW_FORWARD_ROUNDED,
            disabled=True,
            bgcolor=PRIMARY_BLUE,
            color=TEXT_PRIMARY,
            icon_color=TEXT_PRIMARY,
            on_click=self._continue_clicked,
        )

        self.content = self._build()

        self.width = 980
        self.padding = 28
        self.bgcolor = SURFACE
        self.border = ft.Border.all(
            1,
            BORDER_DEFAULT,
        )
        self.border_radius = CARD_RADIUS

    def _build(self) -> ft.Control:

        cards = cast(
            list[ft.Control],
            [
                self._build_card(
                    name,
                    data["Type1"],
                )
                for name, data
                in self._starter_defaults.items()
            ],
        )

        return ft.Column(
            controls=cast(
                list[ft.Control],
                [
                    ft.Text(
                        "Welcome!",
                        size=32,
                        weight=ft.FontWeight.BOLD,
                        color=TEXT_PRIMARY,
                        text_align=ft.TextAlign.CENTER,
                    ),
                    ft.Text(
                        "Choose your first partner to begin your Journey.",
                        size=23,
                        weight=ft.FontWeight.BOLD,
                        color=TEXT_PRIMARY,
                        text_align=ft.TextAlign.CENTER,
                    ),
                    ft.Text(
                        (
                            "Leon has just entrusted you with your first "
                            "Pokémon. The Battle Compass is ready to travel "
                            "alongside you throughout your adventure and help "
                            "you navigate every matchup with confidence!"
                        ),
                        size=16,
                        color=TEXT_SECONDARY,
                        text_align=ft.TextAlign.CENTER,
                    ),
                    ft.Text(
                        "Which partner will be joining you?",
                        size=19,
                        weight=ft.FontWeight.BOLD,
                        color=PRIMARY_BLUE,
                        text_align=ft.TextAlign.CENTER,
                    ),
                    ft.ResponsiveRow(
                        controls=cards,
                        columns=12,
                        spacing=18,
                        run_spacing=18,
                        alignment=ft.MainAxisAlignment.CENTER,
                    ),
                    self.continue_button,
                    self.status_text,
                ],
            ),
            spacing=22,
            horizontal_alignment=ft.CrossAxisAlignment.CENTER,
        )

    def _build_card(
        self,
        starter_name: str,
        starter_type: str,
    ) -> ft.Control:

        card = ft.Container(
            col={
                "xs": 12,
                "sm": 4,
            },
            padding=20,
            bgcolor=SURFACE_RAISED,
            border=ft.Border.all(
                1,
                BORDER_DEFAULT,
            ),
            border_radius=16,
            ink=True,
            on_click=lambda e, name=starter_name: self._select(name),
            content=ft.Column(
                horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                spacing=12,
                controls=[
                    self._build_sprite(
                        starter_name,
                    ),
                    ft.Text(
                        starter_name,
                        size=23,
                        weight=ft.FontWeight.BOLD,
                        color=TEXT_PRIMARY,
                    ),
                    ft.Text(
                        starter_type,
                        color=TEXT_SECONDARY,
                    ),
                ],
            ),
        )

        self.cards[starter_name] = card

        return card

    def _select(
        self,
        starter_name: str,
    ) -> None:

        self.selected_starter = starter_name

        for name, card in self.cards.items():

            selected = name == starter_name

            card.bgcolor = (
                PRIMARY_BLUE_SOFT
                if selected
                else SURFACE_RAISED
            )

            card.border = ft.Border.all(
                3 if selected else 1,
                PRIMARY_BLUE if selected else BORDER_DEFAULT,
            )

        self.continue_button.content = (
            f"Continue with {starter_name}"
        )
        self.continue_button.disabled = False

        self.update()

    def _continue_clicked(
    self,
    event: ft.Event[ft.Button],
    ) -> None:
        """Handle the Continue button."""

        del event

        if self.selected_starter is not None:
            self._on_selected(
                self.selected_starter,
            )

    @staticmethod
    def _build_sprite(
        pokemon: str,
    ) -> ft.Control:

        sprite = get_sprite_path(
            pokemon,
            use_texture=True,
        )

        if sprite is None:
            return ft.Text("?")

        path = Path(sprite)

        if not path.is_absolute():
            path = PROJECT_ROOT / path

        src = path.resolve().relative_to(
            ASSETS_DIR.resolve()
        ).as_posix()

        return ft.Image(
            src=src,
            width=180,
            fit=ft.BoxFit.CONTAIN,
        )