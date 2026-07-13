"""
Battle Snapshot component.

Displays offensive and defensive matchup scores, the worst incoming
move, its category and type, defensive effectiveness, and any active
held-item bonus applied to Move Score.
"""

from __future__ import annotations

from typing import cast

import flet as ft

from ui.theme import (
    BORDER_DEFAULT,
    PRIMARY_BLUE,
    PRIMARY_BLUE_SOFT,
    SURFACE,
    TEXT_MUTED,
    TEXT_PRIMARY,
    TEXT_SECONDARY,
)


class BattleSnapshot(ft.Container):
    """Responsive summary matching the proven Streamlit layout."""

    def __init__(
        self,
        *,
        move_score: float,
        incoming_worst_score: float,
        worst_incoming_move: str,
        incoming_category: str,
        incoming_type_badge_src: str,
        defensive_effectiveness_label: str,
        defensive_effectiveness_color: str,
        defensive_effectiveness_background: str,
        item_boosted: bool = False,
        held_item: str | None = None,
        item_multiplier: float = 1.0,
        base_move_score: float | None = None,
        item_bonus_amount: float = 0.0,
    ) -> None:
        self.move_score = move_score
        self.incoming_worst_score = incoming_worst_score
        self.worst_incoming_move = worst_incoming_move
        self.incoming_category = incoming_category
        self.incoming_type_badge_src = incoming_type_badge_src

        self.defensive_effectiveness_label = (
            defensive_effectiveness_label
        )
        self.defensive_effectiveness_color = (
            defensive_effectiveness_color
        )
        self.defensive_effectiveness_background = (
            defensive_effectiveness_background
        )

        self.item_boosted = item_boosted
        self.held_item = held_item or "Held item"
        self.item_multiplier = item_multiplier
        self.base_move_score = (
            base_move_score
            if base_move_score is not None
            else move_score
        )
        self.item_bonus_amount = item_bonus_amount

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
                ft.Text(
                    "Battle Snapshot",
                    size=22,
                    weight=ft.FontWeight.BOLD,
                    color=TEXT_PRIMARY,
                ),
                self._build_score_grid(),
                self._build_worst_move_section(),
                self._build_effectiveness_banner(),
            ],
        )

        return ft.Column(
            controls=controls,
            spacing=22,
        )

    def _build_score_grid(self) -> ft.Control:
        return ft.ResponsiveRow(
            controls=cast(
                list[ft.Control],
                [
                    ft.Container(
                        content=self._build_move_score(),
                        col={
                            "xs": 12,
                            "sm": 6,
                        },
                    ),
                    ft.Container(
                        content=self._build_score_metric(
                            label="Incoming Worst",
                            value=self.incoming_worst_score,
                        ),
                        col={
                            "xs": 12,
                            "sm": 6,
                        },
                    ),
                ],
            ),
            columns=12,
            spacing=18,
            run_spacing=18,
        )

    def _build_move_score(self) -> ft.Control:
        score_controls = cast(
            list[ft.Control],
            [
                ft.Text(
                    f"{self.move_score:.2f}",
                    size=34,
                    weight=ft.FontWeight.BOLD,
                    color=TEXT_PRIMARY,
                ),
            ],
        )

        if self.item_boosted:
            score_controls.append(
                self._build_item_boost_popup()
            )

        return ft.Column(
            controls=cast(
                list[ft.Control],
                [
                    ft.Text(
                        "Move Score",
                        size=14,
                        color=TEXT_SECONDARY,
                    ),
                    ft.Row(
                        controls=score_controls,
                        spacing=8,
                        vertical_alignment=ft.CrossAxisAlignment.CENTER,
                    ),
                ],
            ),
            spacing=6,
        )

    @staticmethod
    def _build_score_metric(
        *,
        label: str,
        value: float,
    ) -> ft.Control:
        return ft.Column(
            controls=cast(
                list[ft.Control],
                [
                    ft.Text(
                        label,
                        size=14,
                        color=TEXT_SECONDARY,
                    ),
                    ft.Text(
                        f"{value:.2f}",
                        size=34,
                        weight=ft.FontWeight.BOLD,
                        color=TEXT_PRIMARY,
                    ),
                ],
            ),
            spacing=6,
        )

    def _build_item_boost_popup(self) -> ft.Control:
        boost_percent = round(
            (self.item_multiplier - 1) * 100
        )

        popup_controls = cast(
            list[ft.Control],
            [
                ft.Text(
                    "Held Item Bonus Active!",
                    size=15,
                    weight=ft.FontWeight.BOLD,
                    color=TEXT_PRIMARY,
                ),
                ft.Text(
                    self.held_item,
                    size=14,
                    weight=ft.FontWeight.BOLD,
                    color=PRIMARY_BLUE,
                ),
                ft.Text(
                    f"Move bonus: +{boost_percent}%",
                    size=13,
                    color=TEXT_SECONDARY,
                ),
                ft.Divider(
                    color=BORDER_DEFAULT,
                    height=1,
                ),
                ft.Text(
                    f"Base score: {self.base_move_score:.2f}",
                    size=13,
                    color=TEXT_SECONDARY,
                ),
                ft.Text(
                    f"Item boost: +{self.item_bonus_amount:.2f}",
                    size=13,
                    color=TEXT_SECONDARY,
                ),
                ft.Text(
                    f"Final score: {self.move_score:.2f}",
                    size=13,
                    weight=ft.FontWeight.BOLD,
                    color=TEXT_PRIMARY,
                ),
            ],
        )

        return ft.PopupMenuButton(
            icon=ft.Icons.ADD_CIRCLE_OUTLINE,
            icon_color=PRIMARY_BLUE,
            tooltip="View held item bonus",
            items=[
                ft.PopupMenuItem(
                    content=ft.Container(
                        content=ft.Column(
                            controls=popup_controls,
                            spacing=7,
                        ),
                        width=230,
                        padding=10,
                        bgcolor=PRIMARY_BLUE_SOFT,
                        border_radius=10,
                    ),
                ),
            ],
        )

    def _build_worst_move_section(self) -> ft.Control:
        move_line_controls = cast(
            list[ft.Control],
            [
                ft.Text(
                    (
                        f"{self.worst_incoming_move} "
                        f"({self.incoming_category})"
                    ),
                    size=16,
                    color=TEXT_PRIMARY,
                    weight=ft.FontWeight.W_500,
                ),
                ft.Image(
                    src=self.incoming_type_badge_src,
                    height=20,
                    fit=ft.BoxFit.CONTAIN,
                    semantics_label="Worst incoming move type",
                ),
            ],
        )

        return ft.Column(
            controls=cast(
                list[ft.Control],
                [
                    ft.Text(
                        "Worst incoming move",
                        size=14,
                        color=TEXT_SECONDARY,
                    ),
                    ft.Row(
                        controls=move_line_controls,
                        spacing=8,
                        wrap=True,
                        vertical_alignment=ft.CrossAxisAlignment.CENTER,
                    ),
                ],
            ),
            spacing=7,
        )

    def _build_effectiveness_banner(self) -> ft.Control:
        return ft.Container(
            content=ft.Text(
                self.defensive_effectiveness_label,
                size=15,
                weight=ft.FontWeight.BOLD,
                color=self.defensive_effectiveness_color,
            ),
            padding=ft.Padding.symmetric(
                horizontal=16,
                vertical=13,
            ),
            bgcolor=self.defensive_effectiveness_background,
            border_radius=12,
            width=float("inf"),
        )