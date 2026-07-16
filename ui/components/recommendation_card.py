"""
Recommendation Card component.

Displays the recommended Pokémon, best move, Move Score, matchup
strength, supporting explanation, and structured battle notes.
"""

from __future__ import annotations

from collections.abc import Callable
from typing import Any, cast

import flet as ft

from ui.rendering import get_item_sprite_src

from ui.theme import (
    BORDER_ACCENT,
    BORDER_DEFAULT,
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
        best_move_type_badge_src: str,
        effectiveness_label: str,
        effectiveness_color: str,
        move_score: float,
        item_boosted: bool,
        held_item: str | None,
        item_multiplier: float,
        base_move_score: float | None,
        item_bonus_amount: float,
        matchup_label: str,
        matchup_ratio: float,
        matchup_level: int,
        why_text: str,
        battle_notes: list[tuple[str, str, str]],
        on_full_analysis_click: (
            Callable[[ft.Event[ft.Button]], Any]
        ),
        on_type_badge_click: Callable[[str], None],
    ) -> None:
        self.pokemon_name = pokemon_name
        self.gender_symbol = gender_symbol
        self.artwork_src = artwork_src
        self.type_badges = type_badges

        self.best_move = best_move
        self.best_move_type_badge_src = best_move_type_badge_src
        self.effectiveness_label = effectiveness_label
        self.effectiveness_color = effectiveness_color
        self.move_score = move_score

        self.item_boosted = item_boosted
        self.held_item = held_item or "Held item"
        self.item_multiplier = item_multiplier
        self.base_move_score = (
            base_move_score
            if base_move_score is not None
            else move_score
        )
        self.item_bonus_amount = item_bonus_amount

        self.matchup_label = matchup_label
        self.matchup_ratio = matchup_ratio
        self.matchup_level = matchup_level

        self.why_text = why_text
        self.battle_notes = battle_notes
        self.on_full_analysis_click = (
            on_full_analysis_click
        )
        self.on_type_badge_click = (
            on_type_badge_click
        )

        super().__init__(
            content=self._build_content(),
            expand=True,
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
        title_controls = cast(
            list[ft.Control],
            [
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
        )

        return ft.ResponsiveRow(
            columns=12,
            controls=cast(
                list[ft.Control],
                [
                    ft.Container(
                        content=ft.Row(
                            controls=title_controls,
                            spacing=8,
                            vertical_alignment=(
                                ft.CrossAxisAlignment.CENTER
                            ),
                        ),
                        col={"xs": 12},
                    ),
                ],
            ),
        )

    def _build_identity_section(self) -> ft.Control:
        name_controls = cast(
            list[ft.Control],
            [
                ft.Text(
                    self.pokemon_name,
                    size=40,
                    weight=ft.FontWeight.BOLD,
                    color=TEXT_PRIMARY,
                ),
            ],
        )

        if self.gender_symbol:
            if self.gender_symbol.startswith("♀"):
                gender_icon = ft.Icons.FEMALE
                gender_color = "#FF5BA7"
            else:
                gender_icon = ft.Icons.MALE
                gender_color = PRIMARY_BLUE

            name_controls.append(
                ft.Icon(
                    gender_icon,
                    size=24,
                    color=gender_color,
                )
            )

        badge_controls = cast(
            list[ft.Control],
            [
                ft.GestureDetector(
                    content=ft.Image(
                        src=badge_src,
                        height=24,
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
                        ft.Row(
                            controls=name_controls,
                            spacing=6,
                            alignment=ft.MainAxisAlignment.CENTER,
                            vertical_alignment=ft.CrossAxisAlignment.CENTER,
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
                horizontal_alignment=(
                    ft.CrossAxisAlignment.CENTER
                ),
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
            content=self._build_best_move_panel(),
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

    def _build_best_move_panel(self) -> ft.Control:
        score_controls = cast(
            list[ft.Control],
            [
                ft.Text(
                    f"{self.move_score:.2f}",
                    size=30,
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
                        "Best Move",
                        size=14,
                        color=TEXT_SECONDARY,
                    ),
                    ft.Row(
                        controls=cast(
                            list[ft.Control],
                            [
                                ft.Text(
                                    self.best_move,
                                    size=32,
                                    weight=ft.FontWeight.BOLD,
                                    color=TEXT_PRIMARY,
                                ),
                                ft.Image(
                                    src=self.best_move_type_badge_src,
                                    height=22,
                                    fit=ft.BoxFit.CONTAIN,
                                    semantics_label=(
                                        f"{self.best_move} type"
                                    ),
                                ),
                            ],
                        ),
                        spacing=9,
                        wrap=True,
                        vertical_alignment=(
                            ft.CrossAxisAlignment.CENTER
                        ),
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
                    ft.Text(
                        "Move Score",
                        size=14,
                        color=TEXT_SECONDARY,
                    ),
                    ft.Row(
                        controls=score_controls,
                        spacing=8,
                        vertical_alignment=(
                            ft.CrossAxisAlignment.CENTER
                        ),
                    ),
                ],
            ),
            spacing=9,
        )

    def _build_item_boost_popup(self) -> ft.Control:
        boost_percent = round(
            (self.item_multiplier - 1) * 100
        )

        item_sprite_src = get_item_sprite_src(
                    self.held_item
                )

        item_identity_controls = cast(
            list[ft.Control],
            [],
        )

        if item_sprite_src:
            item_identity_controls.append(
                ft.Image(
                    src=item_sprite_src,
                    width=36,
                    height=36,
                    fit=ft.BoxFit.CONTAIN,
                    semantics_label=self.held_item,
                )
            )

        item_identity_controls.append(
            ft.Column(
                controls=cast(
                    list[ft.Control],
                    [
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
                    ],
                ),
                spacing=2,
                expand=True,
            )
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
                ft.Row(
                    controls=item_identity_controls,
                    spacing=9,
                    vertical_alignment=(
                        ft.CrossAxisAlignment.CENTER
                    ),
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
            bgcolor=SURFACE_RAISED,
            menu_padding=6,
            size_constraints=ft.BoxConstraints(
                min_width=242,
                max_width=242,
            ),
            items=[
                ft.PopupMenuItem(
                    padding=0,
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

    def _build_matchup_meter(self) -> ft.Control:
        segment_colors = [
            "#C84B4B",
            "#D98235",
            "#C9B936",
            "#47B96B",
            "#4F9CFF",
        ]

        active_color = segment_colors[
            self.matchup_level
        ]

        segments = cast(
            list[ft.Control],
            [
                ft.Container(
                    height=15 if index == self.matchup_level else 13,
                    expand=True,
                    bgcolor=color,
                    opacity=(
                        1.0
                        if index == self.matchup_level
                        else 0.16
                    ),
                    border=ft.Border.all(
                        2 if index == self.matchup_level else 1,
                        (
                            "#FFFFFFFF"
                            if index == self.matchup_level
                            else "#18FFFFFF"
                        ),
                    ),
                    border_radius=2,
                    shadow=(
                        ft.BoxShadow(
                            blur_radius=8,
                            spread_radius=1,
                            color=color,
                        )
                        if index == self.matchup_level
                        else None
                    ),
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
                        color=active_color,
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
        full_analysis_prompt = ft.Button(
            content=ft.Row(
                controls=cast(
                    list[ft.Control],
                    [
                        ft.Icon(
                            ft.Icons.ARROW_DOWNWARD_ROUNDED,
                            size=20,
                            color=PRIMARY_BLUE_LIGHT,
                        ),
                        ft.Icon(
                            ft.Icons.INFO_OUTLINE_ROUNDED,
                            size=18,
                            color=PRIMARY_BLUE_LIGHT,
                        ),
                        ft.Text(
                            "Compare the entire team in Full Analysis",
                            size=15,
                            weight=ft.FontWeight.W_500,
                            color=PRIMARY_BLUE_LIGHT,
                            expand=True,
                        ),
                    ],
                ),
                spacing=7,
                vertical_alignment=ft.CrossAxisAlignment.CENTER,
            ),
            style=ft.ButtonStyle(
                padding=ft.Padding.symmetric(
                    horizontal=4,
                    vertical=6,
                ),
                bgcolor="#00000000",
                elevation=0,
                alignment=ft.Alignment.CENTER_LEFT,
            ),
            on_click=self.on_full_analysis_click,
        )

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
                        full_analysis_prompt,
                    ],
                ),
                spacing=9,
                horizontal_alignment=ft.CrossAxisAlignment.STRETCH,
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