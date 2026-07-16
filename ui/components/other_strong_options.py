"""
Other Strong Options component.

Displays ranked alternative Pokémon recommendations with sprites,
types, matchup strength, best moves, and relevant battle notes.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import cast

import flet as ft

from ui.theme import (
    BORDER_DEFAULT,
    PRIMARY_BLUE,
    SURFACE,
    SURFACE_RAISED,
    TEXT_MUTED,
    TEXT_PRIMARY,
    TEXT_SECONDARY,
)


@dataclass(frozen=True)
class StrongOptionNote:
    """One note associated with an alternative recommendation."""

    icon: str
    text: str
    category: str = "info"


@dataclass(frozen=True)
class StrongOptionData:
    """Display data for one ranked alternative recommendation."""

    rank: int
    pokemon_name: str
    sprite_src: str
    type_badges: list[tuple[str, str]]
    matchup_label: str
    matchup_ratio: float
    best_move: str
    best_move_type_badge_src: str
    notes: list[StrongOptionNote]


class OtherStrongOptions(ft.Container):
    """Responsive collection of ranked alternative recommendations."""

    def __init__(
        self,
        *,
        options: list[StrongOptionData],
        on_type_badge_click: Callable[[str], None],
    ) -> None:
        self.options = options
        self.on_type_badge_click = (
            on_type_badge_click
        )

        super().__init__(
            content=self._build_content(),
            width=940,
        )

    def _build_content(self) -> ft.Control:
        if not self.options:
            return ft.Column(
                controls=cast(
                    list[ft.Control],
                    [
                        ft.Text(
                            "Other Strong Options",
                            size=26,
                            weight=ft.FontWeight.BOLD,
                            color=TEXT_PRIMARY,
                        ),
                        ft.Container(
                            content=ft.Column(
                                controls=cast(
                                    list[ft.Control],
                                    [
                                        ft.Text(
                                            "Catch a few more Pokémon!",
                                            size=20,
                                            weight=ft.FontWeight.BOLD,
                                            color=TEXT_PRIMARY,
                                            text_align=ft.TextAlign.CENTER,
                                        ),
                                        ft.Text(
                                            (
                                                "As your team grows, your other "
                                                "strongest matchup recommendations "
                                                "will appear here."
                                            ),
                                            size=15,
                                            color=TEXT_SECONDARY,
                                            text_align=ft.TextAlign.CENTER,
                                        ),
                                    ],
                                ),
                                spacing=10,
                                horizontal_alignment=(
                                    ft.CrossAxisAlignment.CENTER
                                ),
                            ),
                            padding=28,
                            bgcolor=SURFACE,
                            border=ft.Border.all(
                                1,
                                BORDER_DEFAULT,
                            ),
                            border_radius=16,
                            alignment=ft.Alignment.CENTER,
                        ),
                    ],
                ),
                spacing=16,
            )

        option_cards = cast(
            list[ft.Control],
            [
                ft.Container(
                    content=self._build_option_card(option),
                    col={
                        "xs": 12,
                        "md": 6,
                    },
                )
                for option in self.options
            ],
        )

        return ft.Column(
            controls=cast(
                list[ft.Control],
                [
                    ft.Text(
                        "Other Strong Options",
                        size=26,
                        weight=ft.FontWeight.BOLD,
                        color=TEXT_PRIMARY,
                    ),
                    ft.ResponsiveRow(
                        controls=option_cards,
                        columns=12,
                        spacing=16,
                        run_spacing=16,
                    ),
                ],
            ),
            spacing=16,
        )

        return ft.Column(
            controls=cast(
                list[ft.Control],
                [
                    ft.Text(
                        "Other Strong Options",
                        size=26,
                        weight=ft.FontWeight.BOLD,
                        color=TEXT_PRIMARY,
                    ),
                    ft.ResponsiveRow(
                        controls=option_cards,
                        columns=12,
                        spacing=16,
                        run_spacing=16,
                    ),
                ],
            ),
            spacing=16,
        )

    def _build_option_card(
        self,
        option: StrongOptionData,
    ) -> ft.Control:
        badge_controls = cast(
            list[ft.Control],
            [
                ft.GestureDetector(
                    content=ft.Image(
                        src=badge_src,
                        height=20,
                        fit=ft.BoxFit.CONTAIN,
                        semantics_label=(
                            f"{pokemon_type} type"
                        ),
                    ),
                    mouse_cursor=ft.MouseCursor.CLICK,
                    on_tap=(
                        lambda event,
                        selected_type=pokemon_type:
                        self.on_type_badge_click(
                            selected_type
                        )
                    ),
                )
                for pokemon_type, badge_src
                in option.type_badges
            ],
        )

        header = ft.Row(
            controls=cast(
                list[ft.Control],
                [
                    ft.Text(
                        f"{option.rank}.",
                        size=28,
                        weight=ft.FontWeight.BOLD,
                        color=TEXT_PRIMARY,
                    ),
                    ft.Image(
                        src=option.sprite_src,
                        width=58,
                        height=58,
                        fit=ft.BoxFit.CONTAIN,
                        semantics_label=option.pokemon_name,
                    ),
                    ft.Column(
                        controls=cast(
                            list[ft.Control],
                            [
                                ft.Text(
                                    option.pokemon_name,
                                    size=25,
                                    weight=ft.FontWeight.BOLD,
                                    color=TEXT_PRIMARY,
                                ),
                                ft.Row(
                                    controls=badge_controls,
                                    spacing=6,
                                    wrap=True,
                                ),
                            ],
                        ),
                        spacing=6,
                        expand=True,
                    ),
                ],
            ),
            spacing=10,
            vertical_alignment=ft.CrossAxisAlignment.CENTER,
        )

        matchup_color = self._get_matchup_color(
            option.matchup_label
        )

        matchup = ft.Row(
            controls=cast(
                list[ft.Control],
                [
                    ft.Text(
                        option.matchup_label,
                        size=17,
                        weight=ft.FontWeight.BOLD,
                        color=matchup_color,
                    ),
                    ft.Text(
                        f"Matchup Ratio: {option.matchup_ratio:.2f}",
                        size=13,
                        color=TEXT_MUTED,
                    ),
                ],
            ),
            spacing=8,
            wrap=True,
            vertical_alignment=ft.CrossAxisAlignment.CENTER,
        )

        best_move = ft.Column(
            controls=cast(
                list[ft.Control],
                [
                    ft.Text(
                        "Best Move",
                        size=13,
                        color=TEXT_SECONDARY,
                    ),
                    ft.Row(
                        controls=cast(
                            list[ft.Control],
                            [
                                ft.Text(
                                    option.best_move,
                                    size=19,
                                    weight=ft.FontWeight.BOLD,
                                    color=TEXT_PRIMARY,
                                ),
                                ft.Image(
                                    src=(
                                        option
                                        .best_move_type_badge_src
                                    ),
                                    height=20,
                                    fit=ft.BoxFit.CONTAIN,
                                    semantics_label=(
                                        f"{option.best_move} type"
                                    ),
                                ),
                            ],
                        ),
                        spacing=8,
                        wrap=True,
                        vertical_alignment=(
                            ft.CrossAxisAlignment.CENTER
                        ),
                    ),
                ],
            ),
            spacing=6,
        )

        notes = self._build_notes(option.notes)

        return ft.Container(
            content=ft.Column(
                controls=cast(
                    list[ft.Control],
                    [
                        header,
                        ft.Divider(
                            color=BORDER_DEFAULT,
                            height=1,
                        ),
                        matchup,
                        best_move,
                        notes,
                    ],
                ),
                spacing=15,
            ),
            padding=20,
            bgcolor=SURFACE,
            border=ft.Border.all(
                1,
                BORDER_DEFAULT,
            ),
            border_radius=16,
        )

    def _build_notes(
        self,
        notes: list[StrongOptionNote],
    ) -> ft.Control:
        if not notes:
            return ft.Text(
                "No special notes.",
                size=14,
                color=TEXT_MUTED,
            )

        note_controls = cast(
            list[ft.Control],
            [
                self._build_note(note)
                for note in notes
            ],
        )

        return ft.Column(
            controls=note_controls,
            spacing=8,
        )

    @staticmethod
    def _build_note(
        note: StrongOptionNote,
    ) -> ft.Control:
        category_styles = {
            "success": (
                "#173828",
                "#C9F7D7",
            ),
            "warning": (
                "#3B3017",
                "#FFE5A3",
            ),
            "info": (
                "#182A43",
                "#D7E8FF",
            ),
        }

        background, foreground = category_styles.get(
            note.category,
            (
                SURFACE_RAISED,
                TEXT_SECONDARY,
            ),
        )

        return ft.Container(
            content=ft.Row(
                controls=cast(
                    list[ft.Control],
                    [
                        ft.Text(
                            note.icon,
                            size=17,
                        ),
                        ft.Text(
                            note.text,
                            size=14,
                            color=foreground,
                            expand=True,
                        ),
                    ],
                ),
                spacing=9,
                vertical_alignment=ft.CrossAxisAlignment.START,
            ),
            padding=10,
            bgcolor=background,
            border_radius=9,
        )

    @staticmethod
    def _get_matchup_color(
        matchup_label: str,
    ) -> str:
        colors = {
            "Challenging": "#F87171",
            "Competitive": "#FB923C",
            "Favorable": "#C9D94A",
            "Comfortable": "#4ADE80",
            "Immune": PRIMARY_BLUE,
        }

        return colors.get(
            matchup_label,
            TEXT_SECONDARY,
        )