"""
Battle Snapshot component.

Summarizes the most important offensive and defensive matchup details,
including any modeled held-item bonus affecting the recommended move.
"""

from __future__ import annotations

from typing import cast

import flet as ft

from ui.theme import (
    BORDER_DEFAULT,
    PRIMARY_BLUE,
    PRIMARY_BLUE_SOFT,
    SURFACE,
    SURFACE_RAISED,
    TEXT_MUTED,
    TEXT_PRIMARY,
    TEXT_SECONDARY,
)


class BattleSnapshot(ft.Container):
    """Responsive summary of the selected battle matchup."""

    def __init__(
        self,
        *,
        opponent_name: str,
        best_move: str,
        move_score: float,
        held_item: str | None,
        held_item_bonus_active: bool,
        worst_incoming_move: str,
        incoming_category: str,
        incoming_score: float,
    ) -> None:
        self.opponent_name = opponent_name
        self.best_move = best_move
        self.move_score = move_score
        self.held_item = held_item
        self.held_item_bonus_active = held_item_bonus_active
        self.worst_incoming_move = worst_incoming_move
        self.incoming_category = incoming_category
        self.incoming_score = incoming_score

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
        controls = cast(
            list[ft.Control],
            [
                self._build_title(),
                ft.Divider(
                    color=BORDER_DEFAULT,
                    height=1,
                ),
                self._build_metrics(),
            ],
        )

        return ft.Column(
            controls=controls,
            spacing=18,
        )

    @staticmethod
    def _build_title() -> ft.Control:
        return ft.Row(
            controls=cast(
                list[ft.Control],
                [
                    ft.Icon(
                        ft.Icons.ANALYTICS_OUTLINED,
                        color=PRIMARY_BLUE,
                        size=24,
                    ),
                    ft.Text(
                        "Battle Snapshot",
                        size=22,
                        weight=ft.FontWeight.BOLD,
                        color=TEXT_PRIMARY,
                    ),
                ],
            ),
            spacing=8,
            vertical_alignment=ft.CrossAxisAlignment.CENTER,
        )

    def _build_metrics(self) -> ft.Control:
        metric_controls = cast(
            list[ft.Control],
            [
                self._build_metric(
                    label="Opponent",
                    value=self.opponent_name,
                    icon=ft.Icons.CATCHING_POKEMON_OUTLINED,
                ),
                self._build_metric(
                    label="Best Move",
                    value=self.best_move,
                    supporting_text=f"Move Score {self.move_score:.2f}",
                    icon=ft.Icons.FLASH_ON_OUTLINED,
                ),
                self._build_held_item_metric(),
                self._build_metric(
                    label="Worst Incoming Move",
                    value=self.worst_incoming_move,
                    supporting_text=(
                        f"{self.incoming_category} · "
                        f"IWS {self.incoming_score:.2f}"
                    ),
                    icon=ft.Icons.WARNING_AMBER_ROUNDED,
                ),
            ],
        )

        return ft.ResponsiveRow(
            controls=metric_controls,
            columns=12,
            spacing=14,
            run_spacing=14,
        )

    @staticmethod
    def _build_metric(
        *,
        label: str,
        value: str,
        icon: ft.IconData,
        supporting_text: str | None = None,
    ) -> ft.Control:
        text_controls = cast(
            list[ft.Control],
            [
                ft.Text(
                    label,
                    size=13,
                    color=TEXT_SECONDARY,
                ),
                ft.Text(
                    value,
                    size=20,
                    weight=ft.FontWeight.BOLD,
                    color=TEXT_PRIMARY,
                    no_wrap=False,
                ),
            ],
        )

        if supporting_text:
            text_controls.append(
                ft.Text(
                    supporting_text,
                    size=12,
                    color=TEXT_MUTED,
                )
            )

        return ft.Container(
            content=ft.Row(
                controls=cast(
                    list[ft.Control],
                    [
                        ft.Icon(
                            icon,
                            color=PRIMARY_BLUE,
                            size=26,
                        ),
                        ft.Column(
                            controls=text_controls,
                            spacing=4,
                            expand=True,
                        ),
                    ],
                ),
                spacing=12,
                vertical_alignment=ft.CrossAxisAlignment.CENTER,
            ),
            col={
                "xs": 12,
                "sm": 6,
            },
            padding=16,
            bgcolor=SURFACE_RAISED,
            border_radius=12,
        )

    def _build_held_item_metric(self) -> ft.Control:
        held_item_name = self.held_item or "None"

        indicator = (
            "⊕ Active Move Bonus"
            if self.held_item_bonus_active
            else "No modeled move bonus"
        )

        indicator_color = (
            PRIMARY_BLUE
            if self.held_item_bonus_active
            else TEXT_MUTED
        )

        return ft.Container(
            content=ft.Row(
                controls=cast(
                    list[ft.Control],
                    [
                        ft.Icon(
                            ft.Icons.BACKPACK_OUTLINED,
                            color=PRIMARY_BLUE,
                            size=26,
                        ),
                        ft.Column(
                            controls=cast(
                                list[ft.Control],
                                [
                                    ft.Text(
                                        "Held Item",
                                        size=13,
                                        color=TEXT_SECONDARY,
                                    ),
                                    ft.Text(
                                        held_item_name,
                                        size=20,
                                        weight=ft.FontWeight.BOLD,
                                        color=TEXT_PRIMARY,
                                    ),
                                    ft.Container(
                                        content=ft.Text(
                                            indicator,
                                            size=12,
                                            weight=ft.FontWeight.BOLD,
                                            color=indicator_color,
                                        ),
                                        padding=ft.Padding.symmetric(
                                            horizontal=9,
                                            vertical=5,
                                        ),
                                        bgcolor=(
                                            PRIMARY_BLUE_SOFT
                                            if self.held_item_bonus_active
                                            else "#12FFFFFF"
                                        ),
                                        border_radius=8,
                                    ),
                                ],
                            ),
                            spacing=5,
                            expand=True,
                        ),
                    ],
                ),
                spacing=12,
                vertical_alignment=ft.CrossAxisAlignment.CENTER,
            ),
            col={
                "xs": 12,
                "sm": 6,
            },
            padding=16,
            bgcolor=SURFACE_RAISED,
            border_radius=12,
        )