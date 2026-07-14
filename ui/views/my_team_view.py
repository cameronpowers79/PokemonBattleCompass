"""
My Team view.

Provides a bulk-editable team table and a selected Pokémon detail panel.
Saved changes update the shared in-memory team and the bundled Alpha JSON
file.
"""

from __future__ import annotations

from collections.abc import Callable
from copy import deepcopy
from pathlib import Path
from typing import cast

import flet as ft

from engine.data_loader import save_json
from engine.moves import apply_move_metadata
from ui.constants import TYPE_COLORS
from ui.rendering import get_sprite_path
from ui.theme import (
    BORDER_DEFAULT,
    CARD_PADDING,
    CARD_RADIUS,
    PRIMARY_BLUE,
    PRIMARY_BLUE_SOFT,
    SUCCESS,
    SURFACE,
    SURFACE_RAISED,
    TEXT_MUTED,
    TEXT_PRIMARY,
    TEXT_SECONDARY,
)


PROJECT_ROOT = Path(__file__).resolve().parents[2]
ASSETS_DIR = PROJECT_ROOT / "assets"

EDITABLE_COLUMNS = [
    "Pokemon",
    "Gender",
    "Type1",
    "Type2",
    "Level",
    "HP",
    "ATK",
    "DEF",
    "SPA",
    "SPD",
    "SPE",
    "Move1",
    "Move2",
    "Move3",
    "Move4",
    "Ability",
    "Held Item",
]

NUMERIC_COLUMNS = {
    "Level",
    "HP",
    "ATK",
    "DEF",
    "SPA",
    "SPD",
    "SPE",
}

STAT_COLUMNS = [
    "HP",
    "ATK",
    "DEF",
    "SPA",
    "SPD",
    "SPE",
]

STAT_COLORS = {
    "HP": "#4ADE80",
    "ATK": "#F87171",
    "DEF": "#FBBF24",
    "SPA": "#A78BFA",
    "SPD": "#60A5FA",
    "SPE": "#F472B6",
}

GENDER_OPTIONS = [
    "Male",
    "Female",
    "Genderless",
]


class MyTeamView:
    """Bulk team editor with a selected-Pokémon detail panel."""

    def __init__(
        self,
        page: ft.Page,
        *,
        team_data: list[dict],
        moves_data: list[dict],
        on_team_saved: Callable[[list[dict]], None] | None = None,
    ) -> None:
        self.page = page
        self.team_data = team_data
        self.moves_data = moves_data
        self.on_team_saved = on_team_saved

        self.move_lookup = {
            move["Move"]: move
            for move in moves_data
            if isinstance(move.get("Move"), str)
            and move["Move"]
        }
        self.move_options = sorted(self.move_lookup)
        self.move_suggestions = [
            ft.AutoCompleteSuggestion(
                key=move_name,
                value=move_name,
            )
            for move_name in self.move_options
        ]
        self.working_team = deepcopy(team_data)
        self.editor_controls: dict[
            tuple[int, str],
            ft.TextField | ft.Dropdown | ft.AutoComplete,
        ] = {}

        self.selected_index = 0

        self.detail_selector = ft.Dropdown(
            label="Select Pokémon",
            options=[],
            on_select=self._handle_detail_selection,
            width=320,
        )

        self.detail_host = ft.Container()
        self.save_status = ft.Text(
            "",
            size=14,
            color=SUCCESS,
        )

        self.table_host = ft.Container(
            content=self._build_editor_table(),
        )

        self._refresh_selector()
        self._refresh_detail()

    def build(self) -> ft.Control:
        """Return the complete My Team view."""

        editor_card = ft.Container(
            content=ft.Column(
                controls=cast(
                    list[ft.Control],
                    [
                        ft.Text(
                            "Manage My Team",
                            size=24,
                            weight=ft.FontWeight.BOLD,
                            color=TEXT_PRIMARY,
                        ),
                        ft.Text(
                            (
                                "Edit your current party. Changes are not "
                                "saved until you click Save Team."
                            ),
                            size=14,
                            color=TEXT_SECONDARY,
                        ),
                        self.table_host,
                        ft.Row(
                            controls=cast(
                                list[ft.Control],
                                [
                                    ft.Button(
                                        content="Save Team",
                                        icon=ft.Icons.SAVE_OUTLINED,
                                        bgcolor=PRIMARY_BLUE,
                                        color=TEXT_PRIMARY,
                                        icon_color=TEXT_PRIMARY,
                                        on_click=self._save_team,
                                    ),
                                    self.save_status,
                                ],
                            ),
                            spacing=14,
                            vertical_alignment=(
                                ft.CrossAxisAlignment.CENTER
                            ),
                        ),
                        ft.Text(
                            (
                                "Only modeled held items affect Move Scores. "
                                "If an item should improve a score but does "
                                "not, verify that its name is spelled "
                                "correctly. A blue ⊕ beside the Move Score "
                                "indicates an active held-item bonus."
                            ),
                            size=13,
                            color=TEXT_MUTED,
                        ),
                    ],
                ),
                spacing=16,
            ),
            width=1280,
            padding=CARD_PADDING,
            bgcolor=SURFACE,
            border=ft.Border.all(
                1,
                BORDER_DEFAULT,
            ),
            border_radius=CARD_RADIUS,
        )

        details_card = ft.Container(
            content=ft.Column(
                controls=cast(
                    list[ft.Control],
                    [
                        ft.Text(
                            "Pokémon Details",
                            size=24,
                            weight=ft.FontWeight.BOLD,
                            color=TEXT_PRIMARY,
                        ),
                        self.detail_selector,
                        self.detail_host,
                    ],
                ),
                spacing=16,
            ),
            width=940,
            padding=CARD_PADDING,
            bgcolor=SURFACE,
            border=ft.Border.all(
                1,
                BORDER_DEFAULT,
            ),
            border_radius=CARD_RADIUS,
        )

        return ft.Column(
            controls=cast(
                list[ft.Control],
                [
                    editor_card,
                    details_card,
                ],
            ),
            spacing=24,
            horizontal_alignment=ft.CrossAxisAlignment.CENTER,
        )

    def _build_editor_table(self) -> ft.Control:
        table = ft.DataTable(
            columns=[
                ft.DataColumn(
                    label=ft.Text(
                        column,
                        weight=ft.FontWeight.BOLD,
                        color=TEXT_PRIMARY,
                    )
)
                for column in EDITABLE_COLUMNS
            ],
            rows=[
                self._build_editor_row(
                    row_index,
                    pokemon,
                )
                for row_index, pokemon in enumerate(
                    self.working_team
                )
            ],
            column_spacing=12,
            data_row_min_height=58,
            data_row_max_height=58,
            heading_row_height=46,
            border=ft.Border.all(
                1,
                BORDER_DEFAULT,
            ),
            border_radius=12,
            heading_row_color=SURFACE_RAISED,
        )

        return ft.Row(
            controls=cast(
                list[ft.Control],
                [table],
            ),
            scroll=ft.ScrollMode.AUTO,
        )

    def _build_editor_row(
        self,
        row_index: int,
        pokemon: dict,
    ) -> ft.DataRow:
        return ft.DataRow(
            cells=[
                ft.DataCell(
                    self._build_editor_control(
                        row_index=row_index,
                        column=column,
                        value=pokemon.get(column),
                    )
                )
                for column in EDITABLE_COLUMNS
            ],
        )

    def _build_editor_control(
        self,
        *,
        row_index: int,
        column: str,
        value: object,
    ) -> ft.TextField | ft.Dropdown | ft.AutoComplete:
        if column == "Gender":
            control = ft.Dropdown(
                value=(
                    str(value)
                    if value
                    else None
                ),
                options=[
                    ft.DropdownOption(
                        key=option,
                        text=option,
                    )
                    for option in GENDER_OPTIONS
                ],
                width=125,
                text_size=13,
                dense=True,
                on_select=lambda event, row=row_index, field=column: (
                    self._handle_dropdown_change(
                        event,
                        row,
                        field,
                    )
                ),
            )

        elif column.startswith("Move"):
            control = ft.AutoComplete(
                value=(
                    str(value)
                    if value
                    else ""
                ),
                suggestions=self.move_suggestions,
                suggestions_max_height=240,
                width=165,
                on_change=lambda event, row=row_index, field=column: (
                    self._handle_move_change(
                        event,
                        row,
                        field,
                    )
                ),
            )

        else:
            width = self._column_width(column)

            control = ft.TextField(
                value=(
                    ""
                    if value is None
                    else str(value)
                ),
                width=width,
                text_size=13,
                dense=True,
                text_align=(
                    ft.TextAlign.RIGHT
                    if column in NUMERIC_COLUMNS
                    else ft.TextAlign.LEFT
                ),
                keyboard_type=(
                    ft.KeyboardType.NUMBER
                    if column in NUMERIC_COLUMNS
                    else ft.KeyboardType.TEXT
                ),
                on_change=lambda event, row=row_index, field=column: (
                    self._handle_text_change(
                        event,
                        row,
                        field,
                    )
                ),
            )

        self.editor_controls[
            (row_index, column)
        ] = control

        return control

    @staticmethod
    def _column_width(column: str) -> int:
        if column == "Pokemon":
            return 125

        if column in {"Type1", "Type2"}:
            return 100

        if column in NUMERIC_COLUMNS:
            return 72

        if column == "Ability":
            return 145

        if column == "Held Item":
            return 145

        return 120

    def _handle_text_change(
        self,
        event: ft.Event[ft.TextField],
        row_index: int,
        column: str,
    ) -> None:
        raw_value = event.control.value or ""

        if column in NUMERIC_COLUMNS:
            stripped_value = raw_value.strip()

            if not stripped_value:
                value: object = 0
            else:
                try:
                    value = int(stripped_value)
                except ValueError:
                    return
        else:
            value = raw_value.strip()

        self.working_team[row_index][column] = value
        self.save_status.value = ""

        if column == "Pokemon":
            self._refresh_selector()

        if row_index == self.selected_index:
            self._refresh_detail()

        self.page.update()

    def _handle_dropdown_change(
        self,
        event: ft.Event[ft.Dropdown],
        row_index: int,
        column: str,
    ) -> None:
        self.working_team[row_index][column] = (
            event.control.value
        )
        self.save_status.value = ""

        if row_index == self.selected_index:
            self._refresh_detail()

        self.page.update()

    def _handle_move_change(
        self,
        event: ft.Event[ft.AutoComplete],
        row_index: int,
        column: str,
    ) -> None:
        move_name = (
            event.control.value or ""
        ).strip()

        self.working_team[row_index][column] = move_name
        self.save_status.value = ""

        if row_index == self.selected_index:
            self._refresh_detail()

        self.page.update()

    def _refresh_selector(self) -> None:
        pokemon_names = [
            str(pokemon.get("Pokemon") or f"Team Slot {index + 1}")
            for index, pokemon in enumerate(self.working_team)
        ]

        self.detail_selector.options = [
            ft.DropdownOption(
                key=str(index),
                text=pokemon_name,
            )
            for index, pokemon_name in enumerate(pokemon_names)
        ]

        if self.selected_index >= len(self.working_team):
            self.selected_index = 0

        self.detail_selector.value = str(self.selected_index)

    def _handle_detail_selection(
        self,
        event: ft.Event[ft.Dropdown],
    ) -> None:
        if event.control.value is None:
            return

        try:
            self.selected_index = int(event.control.value)
        except ValueError:
            return

        self._refresh_detail()
        self.page.update()

    def _refresh_detail(self) -> None:
        if not self.working_team:
            self.detail_host.content = ft.Text(
                "No Pokémon loaded.",
                color=TEXT_SECONDARY,
            )
            return

        pokemon = self.working_team[self.selected_index]
        self.detail_host.content = self._build_detail_card(
            pokemon
        )

    def _build_detail_card(
        self,
        pokemon: dict,
    ) -> ft.Control:
        pokemon_name = str(
            pokemon.get("Pokemon") or "Unknown"
        )
        gender = str(
            pokemon.get("Gender") or ""
        ).strip().lower()

        name_controls = cast(
            list[ft.Control],
            [
                ft.Text(
                    pokemon_name,
                    size=32,
                    weight=ft.FontWeight.BOLD,
                    color=TEXT_PRIMARY,
                ),
            ],
        )

        if gender in {"male", "female"}:
            is_female = gender == "female"

            name_controls.append(
                ft.Icon(
                    (
                        ft.Icons.FEMALE
                        if is_female
                        else ft.Icons.MALE
                    ),
                    size=22,
                    color=(
                        "#FF5BA7"
                        if is_female
                        else PRIMARY_BLUE
                    ),
                )
            )

        sprite_path = get_sprite_path(
            pokemon_name,
            gender=pokemon.get("Gender"),
            use_texture=True,
        )

        if sprite_path is None:
            artwork: ft.Control = ft.Container(
                content=ft.Text(
                    "?",
                    size=48,
                    color=TEXT_MUTED,
                ),
                width=170,
                height=170,
                alignment=ft.Alignment.CENTER,
                bgcolor=SURFACE_RAISED,
                border_radius=16,
            )
        else:
            artwork = ft.Image(
                src=self._asset_src(sprite_path),
                width=170,
                height=170,
                fit=ft.BoxFit.CONTAIN,
                semantics_label=pokemon_name,
            )

        header = ft.ResponsiveRow(
            controls=cast(
                list[ft.Control],
                [
                    ft.Container(
                        content=artwork,
                        col={
                            "xs": 12,
                            "sm": 4,
                        },
                        alignment=ft.Alignment.CENTER,
                    ),
                    ft.Container(
                        content=ft.Column(
                            controls=cast(
                                list[ft.Control],
                                [
                                    ft.Row(
                                        controls=name_controls,
                                        spacing=6,
                                        alignment=(
                                            ft.MainAxisAlignment.CENTER
                                        ),
                                        vertical_alignment=(
                                            ft.CrossAxisAlignment.CENTER
                                        ),
                                    ),
                                    self._build_type_badges(pokemon),
                                    ft.Text(
                                        (
                                            f"Lv. "
                                            f"{pokemon.get('Level', '—')}"
                                        ),
                                        size=18,
                                        color=TEXT_SECONDARY,
                                    ),
                                ],
                            ),
                            spacing=10,
                            horizontal_alignment=(
                                ft.CrossAxisAlignment.CENTER
                            ),
                        ),
                        col={
                            "xs": 12,
                            "sm": 8,
                        },
                        alignment=ft.Alignment.CENTER,
                    ),
                ],
            ),
            columns=12,
            spacing=16,
            run_spacing=12,
            vertical_alignment=ft.CrossAxisAlignment.CENTER,
        )

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
                        ft.Text(
                            "Stats",
                            size=19,
                            weight=ft.FontWeight.BOLD,
                            color=TEXT_PRIMARY,
                        ),
                        self._build_stats(pokemon),
                        ft.Text(
                            "Moveset",
                            size=19,
                            weight=ft.FontWeight.BOLD,
                            color=TEXT_PRIMARY,
                        ),
                        self._build_moves(pokemon),
                        self._build_footer(pokemon),
                    ],
                ),
                spacing=16,
            ),
            padding=20,
            bgcolor=SURFACE_RAISED,
            border_radius=16,
        )

    def _build_type_badges(
        self,
        pokemon: dict,
    ) -> ft.Control:
        badges = cast(
            list[ft.Control],
            [],
        )

        for field_name in ("Type1", "Type2"):
            pokemon_type = pokemon.get(field_name)

            if not isinstance(pokemon_type, str):
                continue

            pokemon_type = pokemon_type.strip()

            if not pokemon_type:
                continue

            badge_path = (
                ASSETS_DIR
                / "type_badges"
                / f"{pokemon_type}.png"
            )

            if badge_path.exists():
                badges.append(
                    ft.Image(
                        src=self._asset_src(badge_path),
                        height=24,
                        fit=ft.BoxFit.CONTAIN,
                        semantics_label=f"{pokemon_type} type",
                    )
                )
            else:
                badges.append(
                    ft.Text(
                        pokemon_type,
                        color=TEXT_SECONDARY,
                    )
                )

        return ft.Row(
            controls=badges,
            spacing=8,
            wrap=True,
            alignment=ft.MainAxisAlignment.CENTER,
        )

    def _build_stats(
        self,
        pokemon: dict,
    ) -> ft.Control:
        return ft.Column(
            controls=cast(
                list[ft.Control],
                [
                    self._build_stat_row(
                        stat_name,
                        self._numeric_value(
                            pokemon.get(stat_name)
                        ),
                    )
                    for stat_name in STAT_COLUMNS
                ],
            ),
            spacing=9,
        )

    @staticmethod
    def _numeric_value(value: object) -> int:
        if isinstance(value, bool):
            return int(value)

        if isinstance(value, int):
            return value

        if isinstance(value, float):
            return int(value)

        if isinstance(value, str):
            try:
                return int(value)
            except ValueError:
                return 0

        return 0
    

    @staticmethod
    def _build_stat_row(
        stat_name: str,
        stat_value: int,
    ) -> ft.Control:
        progress_value = min(
            1.0,
            max(
                0.0,
                stat_value / 300,
            ),
        )

        return ft.Row(
            controls=cast(
                list[ft.Control],
                [
                    ft.Text(
                        stat_name,
                        width=44,
                        weight=ft.FontWeight.BOLD,
                        color=TEXT_SECONDARY,
                    ),
                    ft.ProgressBar(
                        value=progress_value,
                        expand=True,
                        height=10,
                        color=STAT_COLORS[stat_name],
                        bgcolor="#22FFFFFF",
                        border_radius=6,
                    ),
                    ft.Text(
                        str(stat_value),
                        width=40,
                        text_align=ft.TextAlign.RIGHT,
                        weight=ft.FontWeight.BOLD,
                        color=TEXT_PRIMARY,
                    ),
                ],
            ),
            spacing=10,
            vertical_alignment=ft.CrossAxisAlignment.CENTER,
        )

    def _build_moves(
        self,
        pokemon: dict,
    ) -> ft.Control:
        move_cards = cast(
            list[ft.Control],
            [
                self._build_move_card(
                    pokemon.get(f"Move{slot}")
                )
                for slot in range(1, 5)
            ],
        )

        return ft.ResponsiveRow(
            controls=move_cards,
            columns=12,
            spacing=12,
            run_spacing=12,
        )

    def _build_move_card(
        self,
        move_name_value: object,
    ) -> ft.Control:
        move_name = (
            str(move_name_value).strip()
            if move_name_value
            else ""
        )

        move = self.move_lookup.get(move_name)
        move_type_value = (
            move.get("Type")
            if move
            else None
        )
        move_type = (
            move_type_value
            if isinstance(move_type_value, str)
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
                        src=self._asset_src(badge_path),
                        height=18,
                        fit=ft.BoxFit.CONTAIN,
                        semantics_label=f"{move_type} type",
                    )
                )

        return ft.Container(
            content=ft.Row(
                controls=card_controls,
                spacing=8,
                vertical_alignment=ft.CrossAxisAlignment.CENTER,
            ),
            col={
                "xs": 12,
                "sm": 6,
            },
            padding=14,
            bgcolor=background,
            border_radius=10,
        )

    @staticmethod
    def _build_footer(
        pokemon: dict,
    ) -> ft.Control:
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
                                            pokemon.get("Ability")
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
                                            pokemon.get("Held Item")
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

    def _save_team(
        self,
        event: ft.Event[ft.Button],
    ) -> None:
        del event

        invalid_moves: list[str] = []

        for pokemon in self.working_team:
            for slot in range(1, 5):
                move_name = str(
                    pokemon.get(f"Move{slot}") or ""
                ).strip()
                if move_name and move_name not in self.move_lookup:
                    invalid_moves.append(move_name)

        if invalid_moves:
            invalid_list = ", ".join(
                sorted(set(invalid_moves))
            )

            self.save_status.value = (
                f"Invalid move selection: {invalid_list}"
            )
            self.save_status.color = "#F87171"
            self.page.update()
            return

        saved_team = [
            apply_move_metadata(
                deepcopy(pokemon),
                self.moves_data,
            )
            for pokemon in self.working_team
        ]

        self.team_data[:] = saved_team
        self.working_team = deepcopy(saved_team)

        save_json(
            "team_data",
            saved_team,
        )

        if self.on_team_saved:
            self.on_team_saved(saved_team)

        self.save_status.value = "Team saved!"
        self.save_status.color = SUCCESS
        self._refresh_detail()
        self.page.update()

    @staticmethod
    def _asset_src(
        file_path: str | Path,
    ) -> str:
        path = Path(file_path)

        if not path.is_absolute():
            path = PROJECT_ROOT / path

        return path.resolve().relative_to(
            ASSETS_DIR.resolve()
        ).as_posix()