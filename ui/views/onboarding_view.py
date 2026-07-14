"""
Journey onboarding view.

Guides first-time players through choosing a starter, entering its
starting stats, and beginning their Journey with the Battle Compass.
"""

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path
from typing import cast

import flet as ft

from engine.moves import apply_move_metadata
from ui.rendering import get_sprite_path
from ui.theme import (
    APP_BACKGROUND,
    BORDER_DEFAULT,
    CARD_RADIUS,
    CONTENT_MAX_WIDTH,
    PRIMARY_BLUE,
    PRIMARY_BLUE_SOFT,
    SUCCESS,
    SURFACE,
    SURFACE_RAISED,
    TEXT_MUTED,
    TEXT_PRIMARY,
    TEXT_SECONDARY,
)
from ui.viewmodels.app_state import AppState


PROJECT_ROOT = Path(__file__).resolve().parents[2]
ASSETS_DIR = PROJECT_ROOT / "assets"

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

STAT_NAMES = [
    "HP",
    "ATK",
    "DEF",
    "SPA",
    "SPD",
    "SPE",
]


class OnboardingView:
    """First-use Journey onboarding flow."""

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

        self.selected_starter: str | None = (
            app_state.starter
            if app_state.has_journey
            else None
        )

        self.starter_cards: dict[str, ft.Container] = {}
        self.stat_fields: dict[str, ft.TextField] = {}

        self.gender_dropdown = ft.Dropdown(
            label="Gender",
            options=[
                ft.DropdownOption(
                    key="Male",
                    text="Male",
                ),
                ft.DropdownOption(
                    key="Female",
                    text="Female",
                ),
            ],
            width=220,
        )

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
            on_click=self._continue_with_starter,
        )

        initial_content = (
            self._build_starter_details(
                self.selected_starter
            )
            if self.selected_starter
            else self._build_starter_selection()
        )

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
                    starter_name,
                    starter_data["Type1"],
                )
                for starter_name, starter_data
                in STARTER_DEFAULTS.items()
            ],
        )

        return ft.Container(
            content=ft.Column(
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
                            (
                                "Choose your first partner to begin "
                                "your Journey."
                            ),
                            size=23,
                            weight=ft.FontWeight.BOLD,
                            color=TEXT_PRIMARY,
                            text_align=ft.TextAlign.CENTER,
                        ),
                        ft.Text(
                            (
                                "Leon has just entrusted you with your "
                                "first Pokémon. The Battle Compass is "
                                "ready to travel alongside you throughout "
                                "your adventure and help you navigate "
                                "every matchup with confidence!"
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

        type_control = self._build_type_badge(
            starter_type,
            height=24,
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

        self.status_text.value = ""
        self.content_host.content = (
            self._build_starter_details(
                self.selected_starter
            )
        )
        self.page.update()

    def _build_starter_details(
        self,
        starter_name: str,
    ) -> ft.Control:
        defaults = STARTER_DEFAULTS[starter_name]

        self.stat_fields = {
            stat_name: ft.TextField(
                label=stat_name,
                value="",
                width=135,
                keyboard_type=ft.KeyboardType.NUMBER,
                text_align=ft.TextAlign.RIGHT,
            )
            for stat_name in STAT_NAMES
        }

        starter_sprite = get_sprite_path(
            starter_name,
            use_texture=True,
        )

        if starter_sprite is None:
            artwork: ft.Control = ft.Container(
                content=ft.Text(
                    "?",
                    size=48,
                    color=TEXT_MUTED,
                ),
                width=190,
                height=190,
                alignment=ft.Alignment.CENTER,
            )
        else:
            artwork = ft.Image(
                src=self._asset_src(starter_sprite),
                width=190,
                height=190,
                fit=ft.BoxFit.CONTAIN,
                semantics_label=starter_name,
            )

        fixed_details = [
            ("Pokémon", starter_name),
            ("Type", defaults["Type1"]),
            ("Level", "5"),
            ("Ability", defaults["Ability"]),
            ("Move 1", defaults["Move1"]),
            ("Move 2", defaults["Move2"]),
            ("Move 3", "—"),
            ("Move 4", "—"),
            ("Held Item", "—"),
        ]

        fixed_controls = cast(
            list[ft.Control],
            [
                self._build_fixed_field(
                    label,
                    value,
                )
                for label, value in fixed_details
            ],
        )

        stat_controls = cast(
            list[ft.Control],
            [
                ft.Container(
                    content=self.stat_fields[stat_name],
                    col={
                        "xs": 6,
                        "sm": 4,
                        "md": 2,
                    },
                )
                for stat_name in STAT_NAMES
            ],
        )

        return ft.Container(
            content=ft.Column(
                controls=cast(
                    list[ft.Control],
                    [
                        ft.Text(
                            f"Meet {starter_name}",
                            size=30,
                            weight=ft.FontWeight.BOLD,
                            color=TEXT_PRIMARY,
                            text_align=ft.TextAlign.CENTER,
                        ),
                        ft.Text(
                            (
                                f"We’ve filled in everything every new "
                                f"{starter_name} begins with: its type, "
                                f"Level 5, Ability, and starting moves."
                            ),
                            size=16,
                            color=TEXT_SECONDARY,
                            text_align=ft.TextAlign.CENTER,
                        ),
                        ft.Text(
                            (
                                f"Enter {starter_name}’s gender and "
                                f"current stats to finish preparing "
                                f"your Journey."
                            ),
                            size=16,
                            color=TEXT_SECONDARY,
                            text_align=ft.TextAlign.CENTER,
                        ),
                        ft.Text(
                            (
                                "Already farther into your adventure? "
                                "No problem! After setup, visit My Team "
                                "to update levels, moves, Abilities, held "
                                "items, and add the rest of your party."
                            ),
                            size=14,
                            color=TEXT_MUTED,
                            text_align=ft.TextAlign.CENTER,
                        ),
                        artwork,
                        self._build_type_badge(
                            defaults["Type1"],
                            height=24,
                        ),
                        ft.ResponsiveRow(
                            controls=fixed_controls,
                            columns=12,
                            spacing=12,
                            run_spacing=12,
                        ),
                        self.gender_dropdown,
                        ft.Text(
                            "Current Stats",
                            size=19,
                            weight=ft.FontWeight.BOLD,
                            color=TEXT_PRIMARY,
                        ),
                        ft.ResponsiveRow(
                            controls=stat_controls,
                            columns=12,
                            spacing=12,
                            run_spacing=12,
                        ),
                        ft.Button(
                            content="Prepare My Journey",
                            icon=ft.Icons.AUTO_AWESOME_ROUNDED,
                            bgcolor=PRIMARY_BLUE,
                            color=TEXT_PRIMARY,
                            icon_color=TEXT_PRIMARY,
                            on_click=self._save_starter_details,
                        ),
                        self.status_text,
                    ],
                ),
                spacing=20,
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

    @staticmethod
    def _build_fixed_field(
        label: str,
        value: str,
    ) -> ft.Control:
        return ft.Container(
            content=ft.Column(
                controls=cast(
                    list[ft.Control],
                    [
                        ft.Text(
                            label,
                            size=12,
                            color=TEXT_MUTED,
                        ),
                        ft.Text(
                            value,
                            size=15,
                            weight=ft.FontWeight.BOLD,
                            color=TEXT_PRIMARY,
                        ),
                    ],
                ),
                spacing=4,
            ),
            col={
                "xs": 6,
                "sm": 4,
                "md": 3,
            },
            padding=12,
            bgcolor=SURFACE_RAISED,
            border_radius=10,
        )

    async def _save_starter_details(
        self,
        event: ft.Event[ft.Button],
    ) -> None:
        del event

        if self.selected_starter is None:
            return

        gender = self.gender_dropdown.value

        if gender not in {"Male", "Female"}:
            self._show_error(
                "Please select your starter’s gender."
            )
            return

        stats: dict[str, int] = {}

        for stat_name, field in self.stat_fields.items():
            raw_value = (
                field.value or ""
            ).strip()

            try:
                stat_value = int(raw_value)
            except ValueError:
                self._show_error(
                    f"Enter a whole-number value for {stat_name}."
                )
                return

            if stat_value <= 0:
                self._show_error(
                    f"{stat_name} must be greater than zero."
                )
                return

            stats[stat_name] = stat_value

        defaults = STARTER_DEFAULTS[
            self.selected_starter
        ]

        starter_record = {
            "Pokemon": self.selected_starter,
            "Gender": gender,
            "Type1": defaults["Type1"],
            "Type2": None,
            "Level": 5,
            **stats,
            "Move1": defaults["Move1"],
            "Move2": defaults["Move2"],
            "Move3": None,
            "Move4": None,
            "Ability": defaults["Ability"],
            "Held Item": None,
            "EffectiveDEF": stats["DEF"],
            "EffectiveSPD": stats["SPD"],
        }

        starter_record = apply_move_metadata(
            starter_record,
            self.app_state.moves_data,
        )

        save_succeeded = await self.app_state.save_team(
            [starter_record]
        )

        if not save_succeeded:
            self._show_error(
                "Your starter could not be saved. "
                "Please try again."
            )
            return

        self.status_text.value = ""
        self.content_host.content = (
            self._build_journey_ready()
        )
        self.page.update()

    def _build_journey_ready(self) -> ft.Control:
        return ft.Container(
            content=ft.Column(
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
                                "In fact, keeping your team current "
                                "after every level-up, move change, "
                                "Ability change, or held item change is "
                                "recommended—it helps the Battle Compass "
                                "give you the most accurate "
                                "recommendations possible."
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
                            on_click=self._finish_onboarding,
                        ),
                    ],
                ),
                spacing=18,
                horizontal_alignment=ft.CrossAxisAlignment.CENTER,
            ),
            width=760,
            padding=36,
            bgcolor=SURFACE,
            border=ft.Border.all(
                1,
                BORDER_DEFAULT,
            ),
            border_radius=CARD_RADIUS,
            alignment=ft.Alignment.CENTER,
        )

    def _finish_onboarding(
        self,
        event: ft.Event[ft.Button],
    ) -> None:
        del event
        self.on_complete()

    def _show_error(
        self,
        message: str,
    ) -> None:
        self.status_text.value = message
        self.status_text.color = "#F87171"
        self.page.update()

    def _build_type_badge(
        self,
        pokemon_type: str,
        *,
        height: int,
    ) -> ft.Control:
        badge_path = (
            ASSETS_DIR
            / "type_badges"
            / f"{pokemon_type}.png"
        )

        if badge_path.exists():
            return ft.Image(
                src=self._asset_src(badge_path),
                height=height,
                fit=ft.BoxFit.CONTAIN,
                semantics_label=f"{pokemon_type} type",
            )

        return ft.Text(
            pokemon_type,
            color=TEXT_SECONDARY,
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