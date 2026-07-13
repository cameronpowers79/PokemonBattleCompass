"""
Opponent Card component.

Displays the selected opponent and summarizes its most dangerous
projected incoming move against the recommended Pokémon.
"""

from __future__ import annotations

from typing import cast

import flet as ft

from ui.theme import (
    BORDER_DEFAULT,
    SURFACE,
    SURFACE_RAISED,
    TEXT_MUTED,
    TEXT_PRIMARY,
    TEXT_SECONDARY,
)


class OpponentCard(ft.Container):
    """Responsive opponent identity and incoming-threat card."""

    def __init__(
        self,
        *,
        pokemon_name: str,
        artwork_src: str,
        level: int | None,
        type_badges: list[tuple[str, str]],
        incoming_worst_score: float,
        worst_incoming_move: str,
        incoming_category: str,
        incoming_type_badge_src: str,
        defensive_effectiveness_label: str,
        defensive_effectiveness_color: str,
        defensive_effectiveness_background: str,
    ) -> None:
        self.pokemon_name = pokemon_name
        self.artwork_src = artwork_src
        self.level = level
        self.type_badges = type_badges

        self.incoming_worst_score = incoming_worst_score
        self.worst_incoming_move = worst_incoming_move
        self.incoming_category = incoming_category
        self.incoming_type_badge_src = (
            incoming_type_badge_src
        )

        self.defensive_effectiveness_label = (
            defensive_effectiveness_label
        )
        self.defensive_effectiveness_color = (
            defensive_effectiveness_color
        )
        self.defensive_effectiveness_background = (
            defensive_effectiveness_background
        )

        super().__init__(
            content=self._build_content(),
            width=940,
            padding=24,
            bgcolor=SURFACE,
            border=ft.Border.all(
                1,
                BORDER_DEFAULT,
            ),
            border_radius=18,
        )

    def _build_content(self) -> ft.Control:
        return ft.Column(
            controls=cast(
                list[ft.Control],
                [
                    ft.Text(
                        "Opponent",
                        size=22,
                        weight=ft.FontWeight.BOLD,
                        color=TEXT_PRIMARY,
                    ),
                    self._build_identity_section(),
                    ft.Divider(
                        color=BORDER_DEFAULT,
                        height=1,
                    ),
                    self._build_threat_section(),
                ],
            ),
            spacing=20,
        )

    def _build_identity_section(self) -> ft.Control:
        badge_controls = cast(
            list[ft.Control],
            [
                ft.Image(
                    src=badge_src,
                    height=22,
                    fit=ft.BoxFit.CONTAIN,
                    semantics_label=f"{pokemon_type} type",
                )
                for pokemon_type, badge_src in self.type_badges
            ],
        )

        return ft.Container(
            content=ft.Column(
                controls=cast(
                    list[ft.Control],
                    [
                        ft.Image(
                            src=self.artwork_src,
                            width=150,
                            height=150,
                            fit=ft.BoxFit.CONTAIN,
                            semantics_label=self.pokemon_name,
                        ),
                        ft.Text(
                            self.pokemon_name,
                            size=34,
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
                        ft.Text(
                            (
                                f"Lv. {self.level}"
                                if self.level is not None
                                else "Lv. —"
                            ),
                            size=15,
                            color=TEXT_MUTED,
                            text_align=ft.TextAlign.CENTER,
                        ),
                    ],
                ),
                spacing=12,
                horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                alignment=ft.MainAxisAlignment.CENTER,
            ),
            alignment=ft.Alignment.CENTER,
            width=float("inf"),
        )

    def _build_threat_section(self) -> ft.Control:
        score_panel = ft.Container(
            content=ft.Column(
                controls=cast(
                    list[ft.Control],
                    [
                        ft.Text(
                            "Incoming Worst Score",
                            size=14,
                            color=TEXT_SECONDARY,
                        ),
                        ft.Text(
                            f"{self.incoming_worst_score:.2f}",
                            size=34,
                            weight=ft.FontWeight.BOLD,
                            color=TEXT_PRIMARY,
                        ),
                    ],
                ),
                spacing=6,
            ),
            col={
                "xs": 12,
                "sm": 4,
            },
            padding=16,
            bgcolor=SURFACE_RAISED,
            border_radius=12,
        )

        move_panel = ft.Container(
            content=ft.Column(
                controls=cast(
                    list[ft.Control],
                    [
                        ft.Text(
                            "Worst Incoming Move",
                            size=14,
                            color=TEXT_SECONDARY,
                        ),
                        ft.Row(
                            controls=cast(
                                list[ft.Control],
                                [
                                    ft.Text(
                                        (
                                            f"{self.worst_incoming_move} "
                                            f"({self.incoming_category})"
                                        ),
                                        size=18,
                                        weight=ft.FontWeight.BOLD,
                                        color=TEXT_PRIMARY,
                                    ),
                                    ft.Image(
                                        src=(
                                            self
                                            .incoming_type_badge_src
                                        ),
                                        height=20,
                                        fit=ft.BoxFit.CONTAIN,
                                        semantics_label=(
                                            "Worst incoming move type"
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
                        ft.Container(
                            content=ft.Text(
                                (
                                    self
                                    .defensive_effectiveness_label
                                ),
                                size=15,
                                weight=ft.FontWeight.BOLD,
                                color=(
                                    self
                                    .defensive_effectiveness_color
                                ),
                            ),
                            padding=ft.Padding.symmetric(
                                horizontal=16,
                                vertical=12,
                            ),
                            bgcolor=(
                                self
                                .defensive_effectiveness_background
                            ),
                            border_radius=10,
                        ),
                    ],
                ),
                spacing=9,
            ),
            col={
                "xs": 12,
                "sm": 8,
            },
            padding=16,
            bgcolor=SURFACE_RAISED,
            border_radius=12,
        )

        return ft.ResponsiveRow(
            controls=cast(
                list[ft.Control],
                [
                    score_panel,
                    move_panel,
                ],
            ),
            columns=12,
            spacing=16,
            run_spacing=16,
        )