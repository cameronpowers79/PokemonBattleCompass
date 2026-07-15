"""
Opponent Card component.

Displays the selected trainer and opponent Pokémon, then summarizes the
opponent's most dangerous projected incoming move against the
recommended Pokémon.
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
    """Responsive trainer, opponent, and incoming-threat card."""

    def __init__(
        self,
        *,
        trainer_name: str | None,
        trainer_artwork_src: str | None,
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
        self.trainer_name = trainer_name
        self.trainer_artwork_src = trainer_artwork_src

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

    @property
    def has_trainer(self) -> bool:
        """Return whether this encounter has a displayed trainer."""

        return bool(
            self.trainer_name
            and self.trainer_artwork_src
        )

    def _build_content(self) -> ft.Control:
        """Build the complete opponent card."""

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

    def _build_identity_section(
        self,
    ) -> ft.Control:
        """Build a responsive trainer and opponent identity area."""

        if not self.has_trainer:
            return ft.Container(
                content=self._build_pokemon_identity(),
                alignment=ft.Alignment.CENTER,
                width=float("inf"),
            )

        return ft.ResponsiveRow(
            controls=cast(
                list[ft.Control],
                [
                    ft.Container(
                        content=self._build_trainer_identity(),
                        col={
                            "xs": 12,
                            "md": 3,
                        },
                        alignment=ft.Alignment.CENTER,
                    ),
                    ft.Container(
                        content=self._build_pokemon_identity(),
                        col={
                            "xs": 12,
                            "md": 6,
                        },
                        alignment=ft.Alignment.CENTER,
                    ),
                    ft.Container(
                        col={
                            "xs": 0,
                            "md": 3,
                        },
                    ),
                ],
            ),
            columns=12,
            spacing=18,
            run_spacing=18,
            vertical_alignment=(
                ft.CrossAxisAlignment.CENTER
            ),
        )

    def _build_trainer_identity(
        self,
    ) -> ft.Control:
        """Build the smaller trainer portrait and name block."""

        if (
            self.trainer_name is None
            or self.trainer_artwork_src is None
        ):
            return ft.Container()

        return ft.Column(
            controls=cast(
                list[ft.Control],
                [
                    ft.Image(
                        src=self.trainer_artwork_src,
                        width=108,
                        height=108,
                        fit=ft.BoxFit.CONTAIN,
                        semantics_label=(
                            f"Trainer {self.trainer_name}"
                        ),
                    ),
                    ft.Text(
                        self.trainer_name,
                        size=17,
                        weight=ft.FontWeight.BOLD,
                        color=TEXT_SECONDARY,
                        text_align=ft.TextAlign.CENTER,
                    ),
                ],
            ),
            spacing=8,
            horizontal_alignment=(
                ft.CrossAxisAlignment.CENTER
            ),
            alignment=ft.MainAxisAlignment.CENTER,
        )

    def _build_pokemon_identity(
        self,
    ) -> ft.Control:
        """Build the visually dominant opponent Pokémon block."""

        badge_controls = cast(
            list[ft.Control],
            [
                ft.Image(
                    src=badge_src,
                    height=22,
                    fit=ft.BoxFit.CONTAIN,
                    semantics_label=(
                        f"{pokemon_type} type"
                    ),
                )
                for pokemon_type, badge_src
                in self.type_badges
            ],
        )

        return ft.Column(
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
                        alignment=(
                            ft.MainAxisAlignment.CENTER
                        ),
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
            horizontal_alignment=(
                ft.CrossAxisAlignment.CENTER
            ),
            alignment=ft.MainAxisAlignment.CENTER,
        )

    def _build_threat_section(
        self,
    ) -> ft.Control:
        """Build incoming score and move panels."""

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
                                        src=self.incoming_type_badge_src,
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
                                self.defensive_effectiveness_label,
                                size=15,
                                weight=ft.FontWeight.BOLD,
                                color=self.defensive_effectiveness_color,
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

        centered_threat_row = ft.Container(
            content=ft.ResponsiveRow(
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
            ),
            width=780,
        )

        return ft.Container(
            content=centered_threat_row,
            width=float("inf"),
            alignment=ft.Alignment.CENTER,
        )