"""
Opponent Card component.

Displays the selected trainer and opponent Pokémon, then summarizes the
opponent's most dangerous projected incoming move against the
recommended Pokémon.
"""

from __future__ import annotations

from collections.abc import Callable
from typing import cast

import flet as ft

from ui.components.reference_dialogs import (
    show_ability_dialog,
    show_move_dialog,
)
from ui.constants import TYPE_COLORS
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


class OpponentCard(ft.Container):
    """Responsive trainer, opponent, and incoming-threat card."""

    def __init__(
        self,
        *,
        page: ft.Page,
        trainer_name: str | None,
        trainer_artwork_src: str | None,
        pokemon_name: str,
        artwork_src: str,
        level: int | None,
        type_badges: list[tuple[str, str]],
        opponent_moves: list[dict],
        ability_name: str | None,
        ability_descriptions: dict[str, str],
        ability_rules: list[dict],
        incoming_worst_score: float,
        worst_incoming_move: str,
        incoming_category: str,
        incoming_move_type: str,
        incoming_type_badge_src: str,
        defensive_effectiveness_label: str,
        defensive_effectiveness_color: str,
        defensive_effectiveness_background: str,
        on_type_badge_click: Callable[[str], None],
        on_move_type_badge_click: Callable[[str], None],
    ) -> None:
        self.app_page = page
        self.trainer_name = trainer_name
        self.trainer_artwork_src = trainer_artwork_src

        self.pokemon_name = pokemon_name
        self.artwork_src = artwork_src
        self.level = level
        self.type_badges = type_badges
        self.opponent_moves = opponent_moves
        self.ability_name = (
            ability_name.strip()
            if isinstance(ability_name, str)
            and ability_name.strip()
            else None
        )
        self.ability_descriptions = ability_descriptions
        self.ability_rules = ability_rules

        self.incoming_worst_score = incoming_worst_score
        self.worst_incoming_move = worst_incoming_move
        self.incoming_category = incoming_category
        self.incoming_move_type = incoming_move_type
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
        self.on_type_badge_click = (
            on_type_badge_click
        )
        self.on_move_type_badge_click = (
            on_move_type_badge_click
        )

        super().__init__(
            content=self._build_content(),
            expand=True,
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
        """Build the trainer, opponent, and compact moveset area."""

        controls = cast(
            list[ft.Control],
            [],
        )

        if self.has_trainer:
            controls.append(
                ft.Container(
                    content=self._build_trainer_identity(),
                    col={
                        "xs": 12,
                        "md": 3,
                    },
                    alignment=ft.Alignment.CENTER,
                )
            )

        controls.extend(
            cast(
                list[ft.Control],
                [
                    ft.Container(
                        content=self._build_pokemon_identity(),
                        col={
                            "xs": 12,
                            "md": (
                                6
                                if self.has_trainer
                                else 7
                            ),
                        },
                        alignment=ft.Alignment.CENTER,
                    ),
                    ft.Container(
                        content=self._build_moveset(),
                        col={
                            "xs": 12,
                            "md": (
                                3
                                if self.has_trainer
                                else 5
                            ),
                        },
                        alignment=ft.Alignment.CENTER,
                    ),
                ],
            )
        )

        return ft.ResponsiveRow(
            controls=controls,
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
                ft.GestureDetector(
                    content=ft.Image(
                        src=badge_src,
                        height=22,
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

    def _build_moveset(
        self,
    ) -> ft.Control:
        """Build compact opponent move and Ability reference cards."""

        sections = cast(
            list[ft.Control],
            [],
        )

        if self.opponent_moves:
            move_cards = cast(
                list[ft.Control],
                [
                    self._build_move_card(move)
                    for move in self.opponent_moves
                ],
            )
            sections.extend(
                cast(
                    list[ft.Control],
                    [
                        ft.Text(
                            "Moves",
                            size=16,
                            weight=ft.FontWeight.BOLD,
                            color=TEXT_PRIMARY,
                        ),
                        ft.ResponsiveRow(
                            controls=move_cards,
                            columns=12,
                            spacing=8,
                            run_spacing=8,
                        ),
                    ],
                )
            )

        if self.ability_name:
            sections.extend(
                cast(
                    list[ft.Control],
                    [
                        ft.Text(
                            "Ability",
                            size=16,
                            weight=ft.FontWeight.BOLD,
                            color=TEXT_PRIMARY,
                        ),
                        self._build_ability_card(),
                    ],
                )
            )

        if not sections:
            return ft.Container()

        return ft.Column(
            controls=sections,
            spacing=9,
            horizontal_alignment=(
                ft.CrossAxisAlignment.STRETCH
            ),
        )

    def _build_ability_card(
        self,
    ) -> ft.Control:
        """Build the compact clickable opponent Ability card."""

        if self.ability_name is None:
            return ft.Container()

        card = ft.Container(
            content=ft.Row(
                controls=cast(
                    list[ft.Control],
                    [
                        ft.Text(
                            self.ability_name,
                            size=13,
                            weight=ft.FontWeight.BOLD,
                            color=TEXT_PRIMARY,
                            expand=True,
                            max_lines=1,
                            overflow=ft.TextOverflow.ELLIPSIS,
                        ),
                        ft.Icon(
                            ft.Icons.HELP_OUTLINE_ROUNDED,
                            size=17,
                            color=PRIMARY_BLUE,
                        ),
                    ],
                ),
                spacing=6,
                vertical_alignment=(
                    ft.CrossAxisAlignment.CENTER
                ),
            ),
            height=42,
            padding=ft.Padding.symmetric(
                horizontal=10,
                vertical=7,
            ),
            bgcolor=PRIMARY_BLUE_SOFT,
            border=ft.Border.all(
                1,
                "#405A8DFF",
            ),
            border_radius=10,
            tooltip=f"View details for {self.ability_name}",
        )

        return ft.GestureDetector(
            content=card,
            mouse_cursor=ft.MouseCursor.CLICK,
            on_tap=self._show_ability_details,
        )

    def _show_ability_details(
        self,
        event: ft.TapEvent[ft.GestureDetector],
    ) -> None:
        """Show details for the opponent's Ability."""

        del event

        if self.ability_name is None:
            return

        show_ability_dialog(
            page=self.app_page,
            ability_name=self.ability_name,
            ability_descriptions=self.ability_descriptions,
            ability_rules=self.ability_rules,
        )


    def _build_move_card(
        self,
        move: dict,
    ) -> ft.Control:
        """Build one tappable compact opponent move card."""

        move_name = str(
            move.get("Move")
            or "Unknown Move"
        )
        move_type = str(
            move.get("Type")
            or "Unknown"
        )
        badge_src = str(
            move.get("BadgeSrc")
            or ""
        )

        background = TYPE_COLORS.get(
            move_type,
            "#4B5563",
        )

        card = ft.Container(
            content=ft.Column(
                controls=cast(
                    list[ft.Control],
                    [
                        ft.Text(
                            move_name,
                            size=12,
                            weight=ft.FontWeight.BOLD,
                            color="#FFFFFFFF",
                            max_lines=2,
                            overflow=ft.TextOverflow.ELLIPSIS,
                        ),
                        ft.Row(
                            controls=cast(
                                list[ft.Control],
                                [
                                    ft.GestureDetector(
                                        content=ft.Image(
                                            src=badge_src,
                                            height=12,
                                            fit=ft.BoxFit.CONTAIN,
                                            semantics_label=(
                                                f"{move_type} move type"
                                            ),
                                        ),
                                        mouse_cursor=ft.MouseCursor.CLICK,
                                        on_tap=(
                                            lambda event,
                                            selected_type=move_type:
                                            self.on_move_type_badge_click(
                                                selected_type
                                            )
                                        ),
                                    ),
                                ],
                            ),
                            alignment=ft.MainAxisAlignment.END,
                        ),
                    ],
                ),
                spacing=2,
                tight=True,
            ),
            height=42,
            padding=ft.Padding.symmetric(
                horizontal=8,
                vertical=6,
            ),
            bgcolor=background,
            border=ft.Border.all(
                1,
                "#40FFFFFF",
            ),
            border_radius=10,
            tooltip=f"View details for {move_name}",
        )

        return ft.Container(
            content=ft.GestureDetector(
                content=card,
                mouse_cursor=ft.MouseCursor.CLICK,
                on_tap=(
                    lambda event:
                    self._show_move_details(
                        event,
                        move,
                    )
                ),
            ),
            col={
                "xs": 12,
                "sm": 6,
                "md": 12,
            },
        )

    def _show_move_details(
        self,
        event: ft.TapEvent[ft.GestureDetector],
        move: dict,
    ) -> None:
        """Show details for an opponent move."""

        del event

        show_move_dialog(
            page=self.app_page,
            move=move,
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
                                    ft.GestureDetector(
                                        content=ft.Image(
                                            src=self.incoming_type_badge_src,
                                            height=20,
                                            fit=ft.BoxFit.CONTAIN,
                                            semantics_label=(
                                                f"{self.incoming_move_type} move type"
                                            ),
                                        ),
                                        mouse_cursor=ft.MouseCursor.CLICK,
                                        on_tap=(
                                            lambda event:
                                            self.on_move_type_badge_click(
                                                self.incoming_move_type
                                            )
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