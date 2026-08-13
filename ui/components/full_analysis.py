"""
Full Analysis component.

Displays the complete team matchup comparison for the selected opponent.
"""

from __future__ import annotations

from typing import cast

import flet as ft
import flet_datatable2 as fdt

from ui.theme import (
    BORDER_DEFAULT,
    SURFACE,
    SURFACE_RAISED,
    TEXT_MUTED,
    TEXT_PRIMARY,
    TEXT_SECONDARY,
    TEXT_SIZE_CARD_TITLE,
    TEXT_SIZE_DETAIL,
    TEXT_SIZE_CAPTION,
    FONT_FAMILY_HEADER,
)
from ui.viewmodels.battle_compass_vm import MatchupViewModel


FULL_ANALYSIS_SCROLL_KEY = "full-analysis"


class FullAnalysis(ft.Container):
    """Compact, permanently visible full-team matchup comparison."""

    def __init__(
        self,
        *,
        matchups: list[MatchupViewModel],
    ) -> None:
        self.matchups = matchups

        super().__init__(
            key=ft.ScrollKey(
                FULL_ANALYSIS_SCROLL_KEY
            ),
            content=self._build_content(),
            width=940,
            padding=20,
            bgcolor=SURFACE,
            border=ft.Border.all(
                1,
                BORDER_DEFAULT,
            ),
            border_radius=16,
        )

    def _build_content(self) -> ft.Control:
        """Build the complete Full Analysis section."""

        return ft.Column(
            controls=cast(
                list[ft.Control],
                [
                    ft.Text(
                        "Full Analysis",
                        size=TEXT_SIZE_CARD_TITLE,
                        weight=ft.FontWeight.BOLD,
                        font_family=FONT_FAMILY_HEADER,
                        color=TEXT_PRIMARY,
                    ),
                    ft.Text(
                        (
                            "Compare every member of your team "
                            "against the selected opponent."
                        ),
                        size=TEXT_SIZE_DETAIL,
                        color=TEXT_SECONDARY,
                    ),
                    self._build_table_host(),
                ],
            ),
            spacing=12,
        )

    def _build_table_host(self) -> ft.Control:
        """Build a compact, horizontally scrollable analysis table."""

        if not self.matchups:
            return ft.Container(
                content=ft.Text(
                    "No team matchup data is available.",
                    size=14,
                    color=TEXT_MUTED,
                    text_align=ft.TextAlign.CENTER,
                ),
                padding=20,
                alignment=ft.Alignment.CENTER,
                bgcolor=SURFACE_RAISED,
                border_radius=10,
            )

        column_widths = [
            105,
            115,
            112,
            72,
            160,
            150,
            56,
            56,
            300,
        ]

        table = fdt.DataTable2(
            columns=[
                self._column(
                    "Pokémon",
                    fixed_width=column_widths[0],
                ),
                self._column(
                    "Best Move",
                    fixed_width=column_widths[1],
                ),
                self._column(
                    "Type Effectiveness",
                    fixed_width=column_widths[2],
                ),
                self._column(
                    "Move Score",
                    fixed_width=column_widths[3],
                ),
                self._column(
                    "Worst Incoming Move",
                    fixed_width=column_widths[4],
                ),
                self._column(
                    "Incoming Type Effectiveness",
                    fixed_width=column_widths[5],
                ),
                self._column(
                    "IWS",
                    fixed_width=column_widths[6],
                ),
                self._column(
                    "Ratio",
                    fixed_width=column_widths[7],
                ),
                self._column(
                    "Notes",
                    fixed_width=column_widths[8],
                ),
            ],
            rows=[
                self._build_row(matchup)
                for matchup in self.matchups
            ],
            fixed_left_columns=1,
            fixed_top_rows=1,
            fixed_columns_color=SURFACE,
            fixed_corner_color=SURFACE_RAISED,
            min_width=sum(column_widths),
            column_spacing=12,
            horizontal_margin=8,
            data_row_height=82,
            heading_row_height=44,
            heading_row_color=SURFACE_RAISED,
            border=ft.Border.all(
                1,
                BORDER_DEFAULT,
            ),
            border_radius=10,
        )

        return table

    @staticmethod
    def _column(
        label: str,
        *,
        fixed_width: int,
    ) -> fdt.DataColumn2:
        return fdt.DataColumn2(
            label=ft.Text(
                label,
                size=TEXT_SIZE_CAPTION,
                weight=ft.FontWeight.BOLD,
                color=TEXT_PRIMARY,
            ),
            fixed_width=fixed_width,
        )

    def _build_row(
        self,
        matchup: MatchupViewModel,
    ) -> ft.DataRow:
        pokemon_name = str(
            matchup.pokemon.get("Pokemon")
            or "Unknown"
        )
        best_move_name = str(
            matchup.best_move.get("Move")
            or "—"
        )
        worst_move_name = str(
            matchup.worst_move.get("Move")
            or "—"
        )
        worst_move_category = str(
            matchup.worst_move.get("Category")
            or "Unknown"
        )

        return ft.DataRow(
            cells=cast(
                list[ft.DataCell],
                [
                    ft.DataCell(
                        self._text_cell(
                            pokemon_name,
                            width=105,
                            bold=True,
                        )
                    ),
                    ft.DataCell(
                        self._text_cell(
                            best_move_name,
                            width=115,
                            bold=True,
                        )
                    ),
                    ft.DataCell(
                        self._text_cell(
                            f"{matchup.best_move_type_multiplier:g}×",
                            width=112,
                        )
                    ),
                    ft.DataCell(
                        self._number_cell(
                            matchup.best_move_score,
                            width=72,
                        )
                    ),
                    ft.DataCell(
                        self._text_cell(
                            (
                                f"{worst_move_name} "
                                f"({worst_move_category})"
                            ),
                            width=160,
                        )
                    ),
                    ft.DataCell(
                        self._text_cell(
                            f"{matchup.incoming_type_multiplier:g}×",
                            width=150,
                        )
                    ),
                    ft.DataCell(
                        self._number_cell(
                            matchup.incoming_worst_score,
                            width=56,
                        )
                    ),
                    ft.DataCell(
                        self._number_cell(
                            matchup.ratio,
                            width=56,
                        )
                    ),
                    ft.DataCell(
                        self._text_cell(
                            self._notes_text(
                                matchup
                            ),
                            width=300,
                        )
                    ),
                ],
            ),
        )

    @staticmethod
    def _text_cell(
        value: str,
        *,
        width: int,
        bold: bool = False,
    ) -> ft.Control:
        return ft.Container(
            content=ft.Text(
                value,
                size=TEXT_SIZE_CAPTION,
                weight=(
                    ft.FontWeight.BOLD
                    if bold
                    else ft.FontWeight.NORMAL
                ),
                color=(
                    TEXT_PRIMARY
                    if bold
                    else TEXT_SECONDARY
                ),
                no_wrap=False,
            ),
            width=width,
            padding=ft.Padding.symmetric(
                vertical=4,
            ),
        )

    @staticmethod
    def _number_cell(
        value: float,
        *,
        width: int,
    ) -> ft.Control:
        return ft.Container(
            content=ft.Text(
                f"{value:.2f}",
                size=TEXT_SIZE_CAPTION,
                weight=ft.FontWeight.BOLD,
                color=TEXT_PRIMARY,
                text_align=ft.TextAlign.RIGHT,
            ),
            width=width,
            alignment=ft.Alignment.CENTER_RIGHT,
            padding=ft.Padding.symmetric(
                vertical=4,
            ),
        )

    @staticmethod
    def _notes_text(
        matchup: MatchupViewModel,
    ) -> str:
        note_texts = [
            note.text.strip()
            for note in matchup.battle_notes
            if note.text.strip()
        ]

        if not note_texts:
            return "—"

        return " • ".join(
            note_texts
        )