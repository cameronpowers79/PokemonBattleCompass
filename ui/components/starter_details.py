"""
Starter details component.

Displays the second screen of Journey onboarding, where the player
reviews fixed starter information and enters gender and current stats.
"""

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path
from typing import cast

import flet as ft

from engine.moves import apply_move_metadata
from ui.constants import TYPE_COLORS
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

STAT_NAMES = [
    "HP",
    "ATK",
    "DEF",
    "SPA",
    "SPD",
    "SPE",
]

STAT_LABELS = {
    "HP": "HP",
    "ATK": "Attack",
    "DEF": "Defense",
    "SPA": "Sp. Atk",
    "SPD": "Sp. Def",
    "SPE": "Speed",
}


class StarterDetails(ft.Container):
    """Starter information and stat-entry screen."""

    def __init__(
        self,
        *,
        starter_name: str,
        starter_defaults: dict,
        moves_data: list[dict],
        on_completed: Callable[[dict], None],
    ) -> None:
        super().__init__()

        self.starter_name = starter_name
        self.starter_defaults = starter_defaults
        self.moves_data = moves_data
        self.on_completed = on_completed

        self.move_lookup = {
            move["Move"]: move
            for move in self.moves_data
            if isinstance(
                move.get("Move"),
                str,
            )
        }

        self.stat_fields = {
            stat_name: ft.TextField(
                label=STAT_LABELS[stat_name],
                value="",
                keyboard_type=ft.KeyboardType.NUMBER,
                text_align=ft.TextAlign.RIGHT,
            )
            for stat_name in STAT_NAMES
        }

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
        )

        self.status_text = ft.Text(
            "",
            size=14,
            color=TEXT_MUTED,
            text_align=ft.TextAlign.CENTER,
        )

        self.save_button = ft.Button(
            content="Prepare My Journey",
            icon=ft.Icons.AUTO_AWESOME_ROUNDED,
            bgcolor=PRIMARY_BLUE,
            color=TEXT_PRIMARY,
            icon_color=TEXT_PRIMARY,
            on_click=self._prepare_starter,
        )

        self.content = self._build()

        self.width = 1040
        self.padding = 28
        self.bgcolor = SURFACE
        self.border = ft.Border.all(
            1,
            BORDER_DEFAULT,
        )
        self.border_radius = CARD_RADIUS

    def _build(self) -> ft.Control:
        """Build the complete responsive starter-details screen."""

        return ft.Column(
            controls=cast(
                list[ft.Control],
                [
                    self._build_introduction(),
                    ft.ResponsiveRow(
                        controls=cast(
                            list[ft.Control],
                            [
                                ft.Container(
                                    content=self._build_summary_panel(),
                                    col={
                                        "xs": 12,
                                        "md": 5,
                                    },
                                ),
                                ft.Container(
                                    content=self._build_entry_panel(),
                                    col={
                                        "xs": 12,
                                        "md": 7,
                                    },
                                ),
                            ],
                        ),
                        columns=12,
                        spacing=20,
                        run_spacing=20,
                    ),
                    self._build_progress_note(),
                    self.save_button,
                    self.status_text,
                ],
            ),
            spacing=22,
            horizontal_alignment=ft.CrossAxisAlignment.CENTER,
        )

    def _build_introduction(self) -> ft.Control:
        """Build the starter welcome copy."""

        return ft.Column(
            controls=cast(
                list[ft.Control],
                [
                    ft.Text(
                        f"Meet {self.starter_name}",
                        size=30,
                        weight=ft.FontWeight.BOLD,
                        color=TEXT_PRIMARY,
                        text_align=ft.TextAlign.CENTER,
                    ),
                    ft.Text(
                        (
                            f"{self.starter_name}, great! We already "
                            "know the basics about every new "
                            f"{self.starter_name}. Please provide their "
                            "gender and current stats below to help the "
                            "Battle Compass get ready for your Journey."
                        ),
                        size=16,
                        color=TEXT_SECONDARY,
                        text_align=ft.TextAlign.CENTER,
                    ),
                ],
            ),
            spacing=10,
            horizontal_alignment=ft.CrossAxisAlignment.CENTER,
        )

    def _build_summary_panel(self) -> ft.Control:
        """Build artwork and fixed starter information."""

        starter_type = str(
            self.starter_defaults["Type1"]
        )

        starter_record = {
            "Ability": self.starter_defaults["Ability"],
            "Held Item": None,
        }

        move_cards = cast(
            list[ft.Control],
            [
                self._build_move_card(
                    self.starter_defaults["Move1"]
                ),
                self._build_move_card(
                    self.starter_defaults["Move2"]
                ),
                self._build_move_card(None),
                self._build_move_card(None),
            ],
        )

        return ft.Container(
            content=ft.Column(
                controls=cast(
                    list[ft.Control],
                    [
                        self._build_starter_artwork(),
                        ft.Text(
                            self.starter_name,
                            size=25,
                            weight=ft.FontWeight.BOLD,
                            color=TEXT_PRIMARY,
                            text_align=ft.TextAlign.CENTER,
                        ),
                        self._build_type_badge(
                            starter_type,
                            height=25,
                        ),
                        ft.Text(
                            "Lv. 5",
                            size=16,
                            color=TEXT_SECONDARY,
                            text_align=ft.TextAlign.CENTER,
                        ),
                        ft.Divider(
                            color=BORDER_DEFAULT,
                            height=1,
                        ),
                        ft.Text(
                            "Moveset",
                            size=19,
                            weight=ft.FontWeight.BOLD,
                            color=TEXT_PRIMARY,
                        ),
                        ft.ResponsiveRow(
                            controls=move_cards,
                            columns=12,
                            spacing=12,
                            run_spacing=12,
                        ),
                        self._build_footer(
                            starter_record
                        ),
                    ],
                ),
                spacing=14,
                horizontal_alignment=ft.CrossAxisAlignment.CENTER,
            ),
            padding=22,
            bgcolor=SURFACE_RAISED,
            border=ft.Border.all(
                1,
                BORDER_DEFAULT,
            ),
            border_radius=16,
        )

    def _build_entry_panel(self) -> ft.Control:
        """Build the gender and current-stat entry panel."""

        stat_controls = cast(
            list[ft.Control],
            [
                ft.Container(
                    content=self.stat_fields[stat_name],
                    col={
                        "xs": 6,
                        "sm": 4,
                        "md": 6,
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
                        ft.Row(
                            controls=cast(
                                list[ft.Control],
                                [
                                    ft.Icon(
                                        ft.Icons.EDIT_NOTE_ROUNDED,
                                        size=25,
                                        color=PRIMARY_BLUE,
                                    ),
                                    ft.Text(
                                        "Tell Us About Your Partner",
                                        size=21,
                                        weight=ft.FontWeight.BOLD,
                                        color=TEXT_PRIMARY,
                                    ),
                                ],
                            ),
                            spacing=10,
                            wrap=True,
                        ),
                        ft.Text(
                            (
                                "Enter the gender and six current stats "
                                "shown on your Pokémon summary screen."
                            ),
                            size=14,
                            color=TEXT_SECONDARY,
                        ),
                        ft.Divider(
                            color=BORDER_DEFAULT,
                            height=1,
                        ),
                        ft.Text(
                            "Gender",
                            size=16,
                            weight=ft.FontWeight.BOLD,
                            color=TEXT_PRIMARY,
                        ),
                        self.gender_dropdown,
                        ft.Text(
                            "Current Stats",
                            size=16,
                            weight=ft.FontWeight.BOLD,
                            color=TEXT_PRIMARY,
                        ),
                        ft.Text(
                            (
                                "Enter each stat as a whole number "
                                "greater than zero."
                            ),
                            size=13,
                            color=TEXT_MUTED,
                        ),
                        ft.ResponsiveRow(
                            controls=stat_controls,
                            columns=12,
                            spacing=14,
                            run_spacing=14,
                        ),
                    ],
                ),
                spacing=16,
            ),
            padding=22,
            bgcolor=SURFACE_RAISED,
            border=ft.Border.all(
                1,
                BORDER_DEFAULT,
            ),
            border_radius=16,
        )

    def _build_move_card(
        self,
        move_name_value: object,
    ) -> ft.Control:
        """Build a full-width move card matching My Team styling."""

        move_name = (
            str(move_name_value).strip()
            if move_name_value
            else ""
        )

        move = self.move_lookup.get(
            move_name
        )

        move_type_value = (
            move.get("Type")
            if move
            else None
        )

        move_type = (
            move_type_value
            if isinstance(
                move_type_value,
                str,
            )
            else None
        )

        background = (
            TYPE_COLORS.get(
                move_type,
                "#4B5563",
            )
            if move_type
            else "#4B5563"
        )

        card_controls = cast(
            list[ft.Control],
            [
                ft.Text(
                    move_name or "Empty move slot",
                    size=16,
                    weight=ft.FontWeight.BOLD,
                    color="#FFFFFFFF",
                    expand=True,
                    no_wrap=True,
                ),
            ],
        )

        if move_type:
            badge_path = (
                ASSETS_DIR
                / "type_badges"
                / f"{move_type}.png"
            )

            if badge_path.exists():
                card_controls.append(
                    ft.Image(
                        src=self._asset_src(
                            badge_path
                        ),
                        height=18,
                        fit=ft.BoxFit.CONTAIN,
                        semantics_label=(
                            f"{move_type} type"
                        ),
                    )
                )

        return ft.Container(
            content=ft.Row(
                controls=card_controls,
                spacing=8,
                vertical_alignment=(
                    ft.CrossAxisAlignment.CENTER
                ),
            ),
            col={
                "xs": 12,
            },
            padding=14,
            bgcolor=background,
            border_radius=10,
        )

    @staticmethod
    def _build_footer(
        pokemon: dict,
    ) -> ft.Control:
        """Build Ability and Held Item cards matching My Team."""

        return ft.ResponsiveRow(
            controls=cast(
                list[ft.Control],
                [
                    ft.Container(
                        content=ft.Column(
                            controls=cast(
                                list[ft.Control],
                                [
                                    ft.Text(
                                        "Ability",
                                        size=13,
                                        color=TEXT_MUTED,
                                    ),
                                    ft.Text(
                                        str(
                                            pokemon.get(
                                                "Ability"
                                            )
                                            or "—"
                                        ),
                                        size=16,
                                        weight=ft.FontWeight.BOLD,
                                        color=TEXT_PRIMARY,
                                    ),
                                ],
                            ),
                            spacing=4,
                        ),
                        col={
                            "xs": 12,
                            "sm": 6,
                        },
                        padding=14,
                        bgcolor=PRIMARY_BLUE_SOFT,
                        border_radius=10,
                    ),
                    ft.Container(
                        content=ft.Column(
                            controls=cast(
                                list[ft.Control],
                                [
                                    ft.Text(
                                        "Held Item",
                                        size=13,
                                        color=TEXT_MUTED,
                                    ),
                                    ft.Text(
                                        str(
                                            pokemon.get(
                                                "Held Item"
                                            )
                                            or "—"
                                        ),
                                        size=16,
                                        weight=ft.FontWeight.BOLD,
                                        color=TEXT_PRIMARY,
                                    ),
                                ],
                            ),
                            spacing=4,
                        ),
                        col={
                            "xs": 12,
                            "sm": 6,
                        },
                        padding=14,
                        bgcolor=PRIMARY_BLUE_SOFT,
                        border_radius=10,
                    ),
                ],
            ),
            columns=12,
            spacing=12,
            run_spacing=12,
        )

    @staticmethod
    def _build_progress_note() -> ft.Control:
        """Explain where an established team can be updated."""

        return ft.Container(
            content=ft.Row(
                controls=cast(
                    list[ft.Control],
                    [
                        ft.Icon(
                            ft.Icons.INFO_OUTLINE_ROUNDED,
                            size=22,
                            color=PRIMARY_BLUE,
                        ),
                        ft.Text(
                            (
                                "Already farther into your adventure? "
                                "No problem! After setup, visit My Team "
                                "to update levels, moves, Abilities, "
                                "held items, and add the rest of your "
                                "party."
                            ),
                            size=14,
                            color=TEXT_SECONDARY,
                            expand=True,
                        ),
                    ],
                ),
                spacing=12,
            ),
            width=900,
            padding=16,
            bgcolor=PRIMARY_BLUE_SOFT,
            border_radius=12,
        )

    def _prepare_starter(
        self,
        event: ft.Event[ft.Button],
    ) -> None:
        """
        Validate starter details and return a completed starter record.

        Persistence is owned by the onboarding controller so the existing
        Journey remains untouched until setup is fully completed.
        """

        del event

        gender = self.gender_dropdown.value

        if gender not in {
            "Male",
            "Female",
        }:
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
                    (
                        "Enter a whole-number value for "
                        f"{STAT_LABELS[stat_name]}."
                    )
                )
                return

            if stat_value <= 0:
                self._show_error(
                    (
                        f"{STAT_LABELS[stat_name]} must be "
                        "greater than zero."
                    )
                )
                return

            stats[stat_name] = stat_value

        starter_record = {
            "Pokemon": self.starter_name,
            "Gender": gender,
            "Type1": self.starter_defaults["Type1"],
            "Type2": None,
            "Level": 5,
            **stats,
            "Move1": self.starter_defaults["Move1"],
            "Move2": self.starter_defaults["Move2"],
            "Move3": None,
            "Move4": None,
            "Ability": self.starter_defaults["Ability"],
            "Held Item": None,
            "EffectiveDEF": stats["DEF"],
            "EffectiveSPD": stats["SPD"],
        }

        completed_record = apply_move_metadata(
            starter_record,
            self.moves_data,
        )

        self.save_button.disabled = True
        self.status_text.value = (
            "Preparing your Journey..."
        )
        self.status_text.color = TEXT_MUTED
        self.update()

        self.on_completed(
            completed_record
        )

    def show_save_error(
        self,
        message: str,
    ) -> None:
        """Show a persistence error returned by the controller."""

        self._show_error(
            message
        )

    def _show_error(
        self,
        message: str,
    ) -> None:
        """Display a validation or save error."""

        self.status_text.value = message
        self.status_text.color = "#F87171"
        self.save_button.disabled = False
        self.update()

    def _build_starter_artwork(self) -> ft.Control:
        """Return starter artwork or a fallback placeholder."""

        sprite_path = get_sprite_path(
            self.starter_name,
            use_texture=True,
        )

        if sprite_path is None:
            return ft.Container(
                content=ft.Text(
                    "?",
                    size=48,
                    color=TEXT_MUTED,
                ),
                width=220,
                height=220,
                alignment=ft.Alignment.CENTER,
            )

        return ft.Image(
            src=self._asset_src(
                sprite_path
            ),
            width=220,
            height=220,
            fit=ft.BoxFit.CONTAIN,
            semantics_label=self.starter_name,
        )

    def _build_type_badge(
        self,
        pokemon_type: str,
        *,
        height: int,
    ) -> ft.Control:
        """Return the starter's type badge."""

        badge_path = (
            ASSETS_DIR
            / "type_badges"
            / f"{pokemon_type}.png"
        )

        if badge_path.exists():
            return ft.Image(
                src=self._asset_src(
                    badge_path
                ),
                height=height,
                fit=ft.BoxFit.CONTAIN,
                semantics_label=(
                    f"{pokemon_type} type"
                ),
            )

        return ft.Text(
            pokemon_type,
            color=TEXT_SECONDARY,
        )

    @staticmethod
    def _asset_src(
        file_path: str | Path,
    ) -> str:
        """Convert an asset path to an assets-relative source."""

        path = Path(file_path)

        if not path.is_absolute():
            path = PROJECT_ROOT / path

        return path.resolve().relative_to(
            ASSETS_DIR.resolve()
        ).as_posix()