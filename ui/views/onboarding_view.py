"""
Journey onboarding view.

Introduces first-time players to the Battle Compass and lets them choose
their first partner before entering starter details.
"""

from __future__ import annotations

from pathlib import Path
from typing import cast

import flet as ft

from ui.rendering import get_sprite_path
from ui.theme import (
    APP_BACKGROUND,
    BORDER_DEFAULT,
    CARD_RADIUS,
    CONTENT_MAX_WIDTH,
    PRIMARY_BLUE,
    PRIMARY_BLUE_SOFT,
    SURFACE,
    SURFACE_RAISED,
    TEXT_MUTED,
    TEXT_PRIMARY,
    TEXT_SECONDARY,
)
from ui.viewmodels.app_state import AppState


PROJECT_ROOT = Path(__file__).resolve().parents[2]
ASSETS_DIR = PROJECT_ROOT / "assets"

STARTERS = [
    {
        "name": "Grookey",
        "type": "Grass",
    },
    {
        "name": "Scorbunny",
        "type": "Fire",
    },
    {
        "name": "Sobble",
        "type": "Water",
    },
]


class OnboardingView:
    """First-use Journey onboarding flow."""

    def __init__(
        self,
        page: ft.Page,
        *,
        app_state: AppState,
    ) -> None:
        self.page = page
        self.app_state = app_state

        self.selected_starter: str | None = None
        self.starter_cards: dict[str, ft.Container] = {}

        self.continue_button = ft.Button(
            content="Choose a Partner",
            icon=ft.Icons.ARROW_FORWARD_ROUNDED,
            disabled=True,
            bgcolor=PRIMARY_BLUE,
            color=TEXT_PRIMARY,
            icon_color=TEXT_PRIMARY,
            on_click=self._continue_with_starter,
        )

        self.status_text = ft.Text(
            "",
            size=14,
            color=TEXT_MUTED,
            text_align=ft.TextAlign.CENTER,
        )

        self.content_host = ft.Container(
            content=self._build_starter_selection(),
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
        starter_cards = cast(
            list[ft.Control],
            [
                self._build_starter_card(
                    starter["name"],
                    starter["type"],
                )
                for starter in STARTERS
            ],
        )

        return ft.Container(
            content=ft.Column(
                controls=cast(
                    list[ft.Control],
                    [
                        ft.Text(
                            "Welcome! Choose your first partner "
                            "to get started.",
                            size=28,
                            weight=ft.FontWeight.BOLD,
                            color=TEXT_PRIMARY,
                            text_align=ft.TextAlign.CENTER,
                        ),
                        ft.Text(
                            (
                                "Haven’t made it to Hop’s house yet? "
                                "No worries. Return when you have your "
                                "first partner, enter their details, and "
                                "the Compass will be ready to journey "
                                "alongside your Pokédex, your Pokémon, "
                                "and you."
                            ),
                            size=16,
                            color=TEXT_SECONDARY,
                            text_align=ft.TextAlign.CENTER,
                        ),
                        ft.ResponsiveRow(
                            controls=starter_cards,
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
            ),
            width=980,
            padding=28,
            bgcolor=SURFACE,
            border=ft.Border.all(
                1,
                BORDER_DEFAULT,
            ),
            border_radius=CARD_RADIUS,
        )

    def _build_starter_card(
        self,
        starter_name: str,
        starter_type: str,
    ) -> ft.Control:
        sprite_path = get_sprite_path(
            starter_name,
            use_texture=True,
        )

        if sprite_path is None:
            artwork: ft.Control = ft.Container(
                content=ft.Text(
                    "?",
                    size=48,
                    color=TEXT_MUTED,
                ),
                width=180,
                height=180,
                alignment=ft.Alignment.CENTER,
            )
        else:
            artwork = ft.Image(
                src=self._asset_src(sprite_path),
                width=180,
                height=180,
                fit=ft.BoxFit.CONTAIN,
                semantics_label=starter_name,
            )

        type_badge_path = (
            ASSETS_DIR
            / "type_badges"
            / f"{starter_type}.png"
        )

        if type_badge_path.exists():
            type_control: ft.Control = ft.Image(
                src=self._asset_src(type_badge_path),
                height=24,
                fit=ft.BoxFit.CONTAIN,
                semantics_label=f"{starter_type} type",
            )
        else:
            type_control = ft.Text(
                starter_type,
                color=TEXT_SECONDARY,
            )

        card = ft.Container(
            content=ft.Column(
                controls=cast(
                    list[ft.Control],
                    [
                        artwork,
                        ft.Text(
                            starter_name,
                            size=23,
                            weight=ft.FontWeight.BOLD,
                            color=TEXT_PRIMARY,
                            text_align=ft.TextAlign.CENTER,
                        ),
                        type_control,
                    ],
                ),
                spacing=12,
                horizontal_alignment=(
                    ft.CrossAxisAlignment.CENTER
                ),
            ),
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
            alignment=ft.Alignment.CENTER,
            on_click=(
                lambda event, name=starter_name:
                self._select_starter(event, name)
            ),
            ink=True,
        )

        self.starter_cards[starter_name] = card

        return card

    def _select_starter(
        self,
        event: ft.Event[ft.Container],
        starter_name: str,
    ) -> None:
        del event

        self.selected_starter = starter_name

        for name, card in self.starter_cards.items():
            is_selected = name == starter_name

            card.border = ft.Border.all(
                3 if is_selected else 1,
                PRIMARY_BLUE if is_selected else BORDER_DEFAULT,
            )
            card.bgcolor = (
                PRIMARY_BLUE_SOFT
                if is_selected
                else SURFACE_RAISED
            )
            card.shadow = (
                ft.BoxShadow(
                    blur_radius=18,
                    spread_radius=1,
                    color="#334F9CFF",
                )
                if is_selected
                else None
            )

        self.continue_button.content = (
            f"Continue with {starter_name}"
        )
        self.continue_button.disabled = False
        self.status_text.value = ""

        self.page.update()

    async def _continue_with_starter(
        self,
        event: ft.Event[ft.Button],
    ) -> None:
        del event

        if self.selected_starter is None:
            return

        self.continue_button.disabled = True
        self.status_text.value = (
            f"Starting your Journey with "
            f"{self.selected_starter}..."
        )
        self.page.update()

        save_succeeded = await self.app_state.begin_journey(
            self.selected_starter
        )

        if not save_succeeded:
            self.status_text.value = (
                "Your Journey could not be started. "
                "Please try again."
            )
            self.status_text.color = "#F87171"
            self.continue_button.disabled = False
            self.page.update()
            return

        self.content_host.content = (
            self._build_starter_details_placeholder(
                self.selected_starter
            )
        )
        self.page.update()

    @staticmethod
    def _build_starter_details_placeholder(
        starter_name: str,
    ) -> ft.Control:
        return ft.Container(
            content=ft.Column(
                controls=cast(
                    list[ft.Control],
                    [
                        ft.Icon(
                            ft.Icons.AUTO_AWESOME_ROUNDED,
                            size=42,
                            color=PRIMARY_BLUE,
                        ),
                        ft.Text(
                            f"Tell me about {starter_name}",
                            size=28,
                            weight=ft.FontWeight.BOLD,
                            color=TEXT_PRIMARY,
                            text_align=ft.TextAlign.CENTER,
                        ),
                        ft.Text(
                            (
                                "Starter details will be entered "
                                "here in the next build step."
                            ),
                            size=16,
                            color=TEXT_SECONDARY,
                            text_align=ft.TextAlign.CENTER,
                        ),
                    ],
                ),
                spacing=14,
                horizontal_alignment=ft.CrossAxisAlignment.CENTER,
            ),
            width=760,
            padding=32,
            bgcolor=SURFACE,
            border=ft.Border.all(
                1,
                BORDER_DEFAULT,
            ),
            border_radius=CARD_RADIUS,
            alignment=ft.Alignment.CENTER,
        )

    @staticmethod
    def _asset_src(
        file_path: str | Path,
    ) -> str:
        path = Path(file_path)

        if not path.is_absolute():
            path = PROJECT_ROOT / path

        return path.resolve().relative_to(
            ASSETS_DIR.resolve()
        ).as_posix()