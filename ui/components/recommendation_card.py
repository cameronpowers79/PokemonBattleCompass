"""
Recommendation Card component.

Displays the recommended Pokémon, best move, matchup strength,
supporting explanation, and structured battle notes.
"""

from __future__ import annotations

from typing import cast

import flet as ft

from ui.theme import (
    BORDER_ACCENT,
    CARD_PADDING,
    CARD_RADIUS,
    PRIMARY_BLUE,
    PRIMARY_BLUE_LIGHT,
    PRIMARY_BLUE_SOFT,
    SUCCESS,
    SURFACE,
    SURFACE_RAISED,
    TEXT_MUTED,
    TEXT_PRIMARY,
    TEXT_SECONDARY,
    WARNING,
)


class RecommendationCard(ft.Container):
    """Responsive card presenting the primary matchup recommendation."""

    def __init__(
        self,
        *,
        pokemon_name: str,
        gender_symbol: str | None,
        artwork_src: str,
        type_badges: list[tuple[str, str]],
        best_move: str,
        effectiveness_label: str,
        effectiveness_color: str,
        matchup_label: str,
        matchup_ratio: float,
        matchup_level: int,
        why_text: str,
        battle_notes: list[tuple[str, str, str]],
    ) -> None:
        self.pokemon_name = pokemon_name
        self.gender_symbol = gender_symbol
        self.artwork_src = artwork_src
        self.type_badges = type_badges
        self.best_move = best_move
        self.effectiveness_label = effectiveness_label
        self.effectiveness_color = effectiveness_color
        self.matchup_label = matchup_label
        self.matchup_ratio = matchup_ratio
        self.matchup_level = matchup_level
        self.why_text = why_text
        self.battle_notes = battle_notes

        super().__init__(
            content=self._build_content(),
            width=940,
            padding=CARD_PADDING,
            bgcolor=SURFACE,
            border=ft.Border.all(
                1,
                BORDER_ACCENT,
            ),
            border_radius=CARD_RADIUS,
            shadow=ft.BoxShadow(
                blur_radius=22,
                spread_radius=1,
                color="#244F9CFF",
            ),
        )

    def _build_content(self) -> ft.Control:
        controls = cast(
            list[ft.Control],
            [
                self._build_title(),
                self._build_identity_section(),
                ft.Divider(
                    color="#28FFFFFF",
                    height=1,
                ),
                self._build_metrics_section(),
                self._build_why_section(),
                self._build_notes_section(),
            ],
        )

        return ft.Column(
            controls=controls,
            spacing=22,
        )

    @staticmethod
    def _build_title() -> ft.Control:
            return ft.ResponsiveRow(
            columns=12,
            controls=[
                ft.Container(
                    content=ft.Row(
                        controls=[
                            ft.Icon(
                                ft.Icons.STAR_ROUNDED,
                                color=PRIMARY_BLUE,
                                size=26,
                            ),
                            ft.Text(
                                "Recommended Pokémon",
                                size=23,
                                weight=ft.FontWeight.BOLD,
                                color=TEXT_PRIMARY,
                                no_wrap=False,
                                overflow=ft.TextOverflow.VISIBLE,
                                expand=True,
                            ),
                        ],
                        spacing=8,
                        vertical_alignment=ft.CrossAxisAlignment.CENTER,
                    ),
                    col={"xs": 12},
                ),
            ],
        )

    def _build_identity_section(self) -> ft.Control:
        name = self.pokemon_name

        if self.gender_symbol:
            name = f"{name} {self.gender_symbol}"

        badge_controls = cast(
            list[ft.Control],
            [
                ft.Image(
                    src=badge_src,
                    height=24,
                    fit=ft.BoxFit.CONTAIN,
                    semantics_label=f"{pokemon_type} type",
                )
                for pokemon_type, badge_src in self.type_badges
            ],
        )

        artwork_panel = ft.Container(
            content=ft.Image(
                src=self.artwork_src,
                width=180,
                height=180,
                fit=ft.BoxFit.CONTAIN,
                semantics_label=self.pokemon_name,
            ),
            col={
                "xs": 12,
                "sm": 4,
            },
            alignment=ft.Alignment.CENTER,
        )

        identity_panel = ft.Container(
            content=ft.Column(
                controls=cast(
                    list[ft.Control],
                    [
                        ft.Text(
                            name,
                            size=40,
                            weight=ft.FontWeight.BOLD,
                            color=TEXT_PRIMARY,
                            text_align=ft.TextAlign.CENTER,
                        ),
                        ft.Row(
                            controls=badge_controls,
                            spacing=8,
                            wrap=True,
                            alignment=ft.MainAxisAlignment.CENTER,
                        ),
                    ],
                ),
                spacing=12,
                horizontal_alignment=ft.CrossAxisAlignment.CENTER,
            ),
            col={
                "xs": 12,
                "sm": 8,
            },
            alignment=ft.Alignment.CENTER,
        )

        return ft.ResponsiveRow(
            controls=cast(
                list[ft.Control],
                [
                    artwork_panel,
                    identity_panel,
                ],
            ),
            columns=12,
            spacing=16,
            run_spacing=12,
            vertical_alignment=ft.CrossAxisAlignment.CENTER,
        )

    def _build_metrics_section(self) -> ft.Control:
        best_move_panel = ft.Container(
            content=ft.Column(
                controls=cast(
                    list[ft.Control],
                    [
                        ft.Text(
                            "Best Move",
                            size=14,
                            color=TEXT_SECONDARY,
                        ),
                        ft.Text(
                            self.best_move,
                            size=32,
                            weight=ft.FontWeight.BOLD,
                            color=TEXT_PRIMARY,
                        ),
                        ft.Container(
                            content=ft.Text(
                                self.effectiveness_label,
                                size=15,
                                weight=ft.FontWeight.BOLD,
                                color=self.effectiveness_color,
                            ),
                            padding=ft.Padding.symmetric(
                                horizontal=14,
                                vertical=9,
                            ),
                            bgcolor="#182A24",
                            border_radius=10,
                        ),
                    ],
                ),
                spacing=9,
            ),
            col={
                "xs": 12,
                "md": 7,
            },
            padding=16,
            bgcolor=SURFACE_RAISED,
            border_radius=12,
        )

        matchup_panel = ft.Container(
            content=self._build_matchup_meter(),
            col={
                "xs": 12,
                "md": 5,
            },
            padding=16,
            bgcolor=SURFACE_RAISED,
            border_radius=12,
        )

        return ft.ResponsiveRow(
            controls=cast(
                list[ft.Control],
                [
                    best_move_panel,
                    matchup_panel,
                ],
            ),
            columns=12,
            spacing=16,
            run_spacing=16,
        )

    def _build_matchup_meter(self) -> ft.Control:
        segment_colors = [
            "#C84B4B",
            "#D98235",
            "#C9B936",
            "#47B96B",
            "#4F9CFF",
        ]

        segments = cast(
            list[ft.Control],
            [
                ft.Container(
                    height=13,
                    expand=True,
                    bgcolor=color,
                    opacity=1.0 if index == self.matchup_level else 0.28,
                    border=ft.Border.all(
                        1,
                        "#66FFFFFF"
                        if index == self.matchup_level
                        else "#22FFFFFF",
                    ),
                    border_radius=4,
                )
                for index, color in enumerate(segment_colors)
            ],
        )

        return ft.Column(
            controls=cast(
                list[ft.Control],
                [
                    ft.Text(
                        "Matchup Strength",
                        size=14,
                        color=TEXT_SECONDARY,
                    ),
                    ft.Row(
                        controls=segments,
                        spacing=4,
                    ),
                    ft.Text(
                        self.matchup_label,
                        size=21,
                        weight=ft.FontWeight.BOLD,
                        color=SUCCESS,
                    ),
                    ft.Text(
                        f"Ratio {self.matchup_ratio:.2f}",
                        size=13,
                        color=TEXT_MUTED,
                    ),
                ],
            ),
            spacing=8,
        )

    def _build_why_section(self) -> ft.Control:
        return ft.Container(
            content=ft.Column(
                controls=cast(
                    list[ft.Control],
                    [
                        ft.Text(
                            "Why this Pokémon?",
                            size=19,
                            weight=ft.FontWeight.BOLD,
                            color=TEXT_PRIMARY,
                        ),
                        ft.Text(
                            self.why_text,
                            size=15,
                            color="#D7E8FF",
                        ),
                        ft.Text(
                            "ⓘ Compare the entire team in Full Analysis.",
                            size=14,
                            weight=ft.FontWeight.BOLD,
                            color=PRIMARY_BLUE_LIGHT,
                        ),
                    ],
                ),
                spacing=9,
            ),
            padding=16,
            bgcolor=PRIMARY_BLUE_SOFT,
            border=ft.Border.all(
                1,
                "#445F8BC4",
            ),
            border_radius=12,
        )

    def _build_notes_section(self) -> ft.Control:
        note_controls = cast(
            list[ft.Control],
            [
                self._build_note(
                    icon=icon,
                    text=text,
                    category=category,
                )
                for icon, text, category in self.battle_notes
            ],
        )

        controls = cast(
            list[ft.Control],
            [
                ft.Text(
                    "Battle Notes",
                    size=19,
                    weight=ft.FontWeight.BOLD,
                    color=TEXT_PRIMARY,
                ),
                *note_controls,
            ],
        )

        return ft.Column(
            controls=controls,
            spacing=9,
        )

    @staticmethod
    def _build_note(
        *,
        icon: str,
        text: str,
        category: str,
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
                PRIMARY_BLUE_SOFT,
                "#D7E8FF",
            ),
        }

        background, foreground = category_styles.get(
            category,
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
                            icon,
                            size=18,
                        ),
                        ft.Text(
                            text,
                            size=15,
                            color=foreground,
                            expand=True,
                        ),
                    ],
                ),
                spacing=10,
                vertical_alignment=ft.CrossAxisAlignment.START,
            ),
            padding=12,
            bgcolor=background,
            border_radius=10,
        )