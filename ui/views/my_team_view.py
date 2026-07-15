"""
My Team view.

Provides a bulk-editable team table and a selected Pokémon detail panel.
Saved changes update the active persistent Journey.
"""

from __future__ import annotations
from ui.viewmodels.app_state import AppState
from collections.abc import Callable
from copy import deepcopy
from pathlib import Path
from typing import cast

import flet as ft

from engine.item_recommendations import (
    ItemRecommendation,
    recommend_held_items,
)
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
    SUCCESS_SOFT,
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

MOVE_TAG_DESCRIPTIONS = {
    "Pivot": (
        "Switches the user out after the move succeeds."
    ),
    "Protection": (
        "Protects the user from most attacks for one turn."
    ),
    "Recovery": (
        "Restores some of the user's HP."
    ),
    "Drain": (
        "Restores HP based on the damage dealt."
    ),
    "Recoil": (
        "The user takes recoil damage after attacking."
    ),
    "ContactPunisher": (
        "Can punish an opponent for making contact."
    ),
    "Screen": (
        "Reduces damage received by the user's side of the field."
    ),
    "Weather": (
        "Creates or interacts with a weather condition."
    ),
    "Terrain": (
        "Creates or interacts with battlefield terrain."
    ),
}


ACTIVATION_CONDITION_DESCRIPTIONS = {
    "targethasstatus": (
        "if the target has a status condition"
    ),
    "targetstatused": (
        "if the target has a status condition"
    ),
    "targetstatuscondition": (
        "if the target has a status condition"
    ),
    "targetpoisoned": (
        "if the target is poisoned"
    ),
    "targetbadlypoisoned": (
        "if the target is poisoned"
    ),
    "targetburned": (
        "if the target is burned"
    ),
    "targetparalyzed": (
        "if the target is paralyzed"
    ),
    "targetasleep": (
        "if the target is asleep"
    ),
    "targetfrozen": (
        "if the target is frozen"
    ),
    "targetathalfhporless": (
        "if the target is at half HP or less"
    ),
    "targethalfhorless": (
        "if the target is at half HP or less"
    ),
    "targetbelowhalfhealth": (
        "if the target is at half HP or less"
    ),
    "userhasstatus": (
        "while the user is burned, poisoned, or paralyzed"
    ),
    "userstatused": (
        "while the user is burned, poisoned, or paralyzed"
    ),
    "userburnedpoisonedorparalyzed": (
        "while the user is burned, poisoned, or paralyzed"
    ),
    "targetalreadyacted": (
        "if the target has already acted this turn"
    ),
    "usermovesaftertarget": (
        "if the user moves after the target"
    ),
    "userwashit": (
        "if the user was hit earlier in the turn"
    ),
    "userhitbeforemove": (
        "if the user was hit before using the move"
    ),
    "previousmovefailed": (
        "if the user's previous move failed"
    ),
    "previousmovefailedagainsttarget": (
        "if the user's previous move against the target failed"
    ),
    "targetanystatus": (
        "if the target has a status condition"
    ),
    "targetanystatus": (
        "if the target has a status condition"
    ),
    "targetpoisoned": (
        "if the target is poisoned"
    ),
    "userburnpoisonparalysis": (
        "while the user is burned, poisoned, or paralyzed"
    ),
    "requiresuserhit": (
        "if the user was hit earlier in the turn"
    ),
    "UserMovesAfterTarget":(
        "if the user moves after the target"
    )


}


class MyTeamView:
    """Bulk team editor with a selected-Pokémon detail panel."""

    def __init__(
        self,
        page: ft.Page,
        *,
        app_state: AppState,
        moves_data: list[dict],
        on_team_updated: (
            Callable[[list[dict]], None] | None
        ) = None,
    ) -> None:
        self.page = page
        self.app_state = app_state
        self.team_data = app_state.team_data
        self.moves_data = moves_data
        self.items_data = app_state.reference_data["items"]
        self.on_team_updated = on_team_updated

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
        self.working_team = deepcopy(self.team_data)
        self.saved_team_snapshot = deepcopy(self.team_data)

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

        self.save_button = ft.Button(
            content="Save Team",
            icon=ft.Icons.SAVE_OUTLINED,
            disabled=True,
            on_click=self._save_team,
            style=ft.ButtonStyle(
                bgcolor={
                    ft.ControlState.DEFAULT: PRIMARY_BLUE,
                    ft.ControlState.DISABLED: "#334155",
                },
                color={
                    ft.ControlState.DEFAULT: TEXT_PRIMARY,
                    ft.ControlState.DISABLED: TEXT_MUTED,
                },
                icon_color={
                    ft.ControlState.DEFAULT: TEXT_PRIMARY,
                    ft.ControlState.DISABLED: TEXT_MUTED,
                },
                elevation={
                    ft.ControlState.DEFAULT: 1,
                    ft.ControlState.DISABLED: 0,
                },
            ),
        )

        self.table_host = ft.Container(
            content=self._build_editor_table(),
        )

        self._refresh_selector()
        self._refresh_detail()

    @property
    def has_unsaved_changes(self) -> bool:
        """Return whether the working editor differs from the saved team."""

        return self.working_team != self.saved_team_snapshot

    def discard_unsaved_changes(self) -> None:
        """Restore the editor to the most recently saved team."""

        self.working_team = deepcopy(
            self.saved_team_snapshot
        )
        self.editor_controls.clear()

        self.table_host.content = (
            self._build_editor_table()
        )

        self.save_status.value = ""
        self.save_status.color = SUCCESS
        self.save_button.disabled = True

        self._refresh_selector()
        self._refresh_detail()

    def _update_dirty_state(self) -> None:
        """Synchronize save controls with the current dirty state."""

        is_dirty = self.has_unsaved_changes

        self.save_button.disabled = not is_dirty

        if is_dirty:
            self.save_status.value = ""
            self.save_status.color = SUCCESS

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
                                "Did someone level up? Learn a new move? "
                                "Get a new item? Tell the Battle Compass "
                                "about it here. Then, take a quick moment "
                                "to ensure your team's information is "
                                "accurate before saving. The Battle Compass "
                                "relies on these details to recommend your "
                                "strongest matchups."
                            ),
                            size=14,
                            color=TEXT_SECONDARY,
                        ),
                        self.table_host,
                        ft.Row(
                            controls=cast(
                                list[ft.Control],
                                [
                                    self.save_button,
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
        self._update_dirty_state()

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
        self._update_dirty_state()

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
        self._update_dirty_state()

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
                        ft.Column(
                            controls=cast(
                                list[ft.Control],
                                [
                                    ft.Text(
                                        "Moves",
                                        size=19,
                                        weight=ft.FontWeight.BOLD,
                                        color=TEXT_PRIMARY,
                                    ),
                                    ft.Text(
                                        "Select a move to view its details.",
                                        size=13,
                                        color=TEXT_MUTED,
                                    ),
                                ],
                            ),
                            spacing=3,
                            tight=True,
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
                    color=(
                        "#FFFFFFFF"
                        if move
                        else TEXT_SECONDARY
                    ),
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
                        src=self._asset_src(
                            badge_path
                        ),
                        height=18,
                        fit=ft.BoxFit.CONTAIN,
                        semantics_label=(
                            f"{move_type} type"
                        ),
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
            height=52,
            padding=14,
            alignment=ft.Alignment.CENTER_LEFT,
            bgcolor=background,
            opacity=1.0 if move else 0.55,
            border_radius=10,
            clip_behavior=ft.ClipBehavior.ANTI_ALIAS,
            
            on_click=(
                (
                    lambda event, selected_move=move:
                    self._show_move_details(
                        event,
                        selected_move,
                    )
                )
                if move
                else None
            ),
        )

    def _show_move_details(
        self,
        event: ft.Event[ft.Container],
        move: dict,
    ) -> None:
        """Show player-facing details for a selected move."""

        del event

        move_name = str(
            move.get("Move")
            or "Unknown Move"
        )

        self.page.show_dialog(
            ft.AlertDialog(
                modal=True,
                title=ft.Text(
                    move_name,
                    size=23,
                    weight=ft.FontWeight.BOLD,
                    color=TEXT_PRIMARY,
                ),
                content=ft.Container(
                    content=self._build_move_detail_content(
                        move
                    ),
                    width=540,
                ),
                actions=cast(
                    list[ft.Control],
                    [
                        ft.Button(
                            content="Close",
                            on_click=(
                                self._close_move_details
                            ),
                        ),
                    ],
                ),
                actions_alignment=(
                    ft.MainAxisAlignment.END
                ),
            )
        )


    def _build_move_detail_content(
        self,
        move: dict,
    ) -> ft.Control:
        """Build the scrollable move-detail dialog."""

        move_type = self._clean_text(
            move.get("Type")
        ) or "Unknown"

        category = self._clean_text(
            move.get("Category")
        ) or "Unknown"

        type_category_controls = cast(
            list[ft.Control],
            [],
        )

        badge_path = (
            ASSETS_DIR
            / "type_badges"
            / f"{move_type}.png"
        )

        if badge_path.exists():
            type_category_controls.append(
                ft.Image(
                    src=self._asset_src(
                        badge_path
                    ),
                    height=24,
                    fit=ft.BoxFit.CONTAIN,
                    semantics_label=(
                        f"{move_type} type"
                    ),
                )
            )
        else:
            type_category_controls.append(
                ft.Text(
                    move_type,
                    size=15,
                    weight=ft.FontWeight.BOLD,
                    color=TEXT_PRIMARY,
                )
            )

        type_category_controls.append(
            ft.Container(
                content=ft.Text(
                    category,
                    size=13,
                    weight=ft.FontWeight.BOLD,
                    color=TEXT_PRIMARY,
                ),
                padding=ft.Padding.symmetric(
                    horizontal=11,
                    vertical=6,
                ),
                bgcolor=PRIMARY_BLUE_SOFT,
                border_radius=8,
            )
        )

        effect_lines = (
            self._move_effect_descriptions(
                move
            )
        )

        navigation_aids = (
            self._move_navigation_aids(
                move
            )
        )

        controls = cast(
            list[ft.Control],
            [
                ft.Row(
                    controls=type_category_controls,
                    spacing=10,
                    wrap=True,
                    vertical_alignment=(
                        ft.CrossAxisAlignment.CENTER
                    ),
                ),
                self._build_move_stat_summary(
                    move
                ),
                ft.Divider(
                    color=BORDER_DEFAULT,
                    height=1,
                ),
                ft.Text(
                    "Effect",
                    size=17,
                    weight=ft.FontWeight.BOLD,
                    color=TEXT_PRIMARY,
                ),
                *[
                    ft.Text(
                        line,
                        size=15,
                        color=TEXT_SECONDARY,
                    )
                    for line in effect_lines
                ],
            ],
        )

        if navigation_aids:
            controls.extend(
                [
                    ft.Divider(
                        color=BORDER_DEFAULT,
                        height=1,
                    ),
                    ft.Text(
                        "Additional Navigation Aids",
                        size=17,
                        weight=ft.FontWeight.BOLD,
                        color=TEXT_PRIMARY,
                    ),
                    *[
                        self._build_navigation_aid(
                            aid
                        )
                        for aid in navigation_aids
                    ],
                ]
            )

        return ft.Column(
            controls=controls,
            spacing=13,
            tight=True,
        )


    def _build_move_stat_summary(
        self,
        move: dict,
    ) -> ft.Control:
        """Build the Power, Accuracy, and Priority summary."""

        category = self._clean_text(
            move.get("Category")
        )

        power_value = self._numeric_move_value(
            move.get("Power")
        )

        power = (
            "—"
            if (
                category
                and category.lower() == "status"
            )
            or power_value is None
            or power_value <= 0
            else self._format_number(
                power_value
            )
        )

        accuracy_value = (
            self._numeric_move_value(
                move.get("Accuracy")
            )
        )

        accuracy = (
            f"{self._format_number(accuracy_value)}%"
            if accuracy_value is not None
            else "—"
        )

        priority_value = (
            self._numeric_move_value(
                move.get("Priority")
            )
        )

        priority = self._priority_label(
            priority_value
        )

        return ft.ResponsiveRow(
            controls=cast(
                list[ft.Control],
                [
                    self._build_move_stat_box(
                        "Power",
                        power,
                    ),
                    self._build_move_stat_box(
                        "Accuracy",
                        accuracy,
                    ),
                    self._build_move_stat_box(
                        "Priority",
                        priority,
                    ),
                ],
            ),
            columns=12,
            spacing=10,
            run_spacing=10,
        )


    @staticmethod
    def _build_move_stat_box(
        label: str,
        value: str,
    ) -> ft.Control:
        """Build one compact move-stat box."""

        return ft.Container(
            content=ft.Column(
                controls=cast(
                    list[ft.Control],
                    [
                        ft.Text(
                            label,
                            size=12,
                            color=TEXT_MUTED,
                        ),
                        ft.Text(
                            value,
                            size=18,
                            weight=ft.FontWeight.BOLD,
                            color=TEXT_PRIMARY,
                        ),
                    ],
                ),
                spacing=3,
            ),
            col={
                "xs": 12,
                "sm": 4,
            },
            padding=12,
            bgcolor=SURFACE_RAISED,
            border_radius=10,
        )


    @staticmethod
    def _build_navigation_aid(
        text: str,
    ) -> ft.Control:
        """Build one player-facing navigation aid."""

        return ft.Row(
            controls=cast(
                list[ft.Control],
                [
                    ft.Icon(
                        ft.Icons.EXPLORE_OUTLINED,
                        size=17,
                        color=PRIMARY_BLUE,
                    ),
                    ft.Text(
                        text,
                        size=14,
                        color=TEXT_SECONDARY,
                        expand=True,
                    ),
                ],
            ),
            spacing=8,
            vertical_alignment=(
                ft.CrossAxisAlignment.START
            ),
        )


    def _move_effect_descriptions(
        self,
        move: dict,
    ) -> list[str]:
        """Translate structured move data into concise effect text."""

        descriptions: list[str] = []

        category = self._clean_text(
            move.get("Category")
        )

        power = self._numeric_move_value(
            move.get("Power")
        )

        damage_method = self._clean_text(
            move.get("DamageMethod")
        )

        if (
            damage_method
            and damage_method.lower() == "ohko"
        ):
            descriptions.append(
                (
                    "Knocks out the target in one hit "
                    "when the move succeeds."
                )
            )
        elif (
            damage_method
            and damage_method.lower() == "fixed"
        ):
            descriptions.append(
                "Deals a fixed amount of damage."
            )
        elif power is not None and power > 0:
            descriptions.append(
                "Deals damage."
            )

        multiplier = self._numeric_move_value(
            move.get(
                "ActivationPowerMultiplier"
            )
        )

        condition = self._clean_text(
            move.get("ActivationCondition")
        )

        condition_description = (
            self._activation_condition_description(
                condition
            )
        )

        if (
            multiplier is not None
            and multiplier > 1
            and condition_description
        ):
            descriptions.append(
                self._multiplier_description(
                    multiplier,
                    condition_description,
                )
            )

        status_description = (
            self._status_effect_description(
                move.get("StatusEffect"),
                is_status_move=(
                    category is not None
                    and category.lower() == "status"
                ),
            )
        )

        if status_description:
            descriptions.append(
                status_description
            )

        descriptions.extend(
            self._stat_stage_effect_descriptions(
                move
            )
        )

        if not descriptions:
            descriptions.append(
                (
                    "Additional effects for this move "
                    "are still being added to the "
                    "Battle Compass."
                )
            )

        return descriptions


    def _stat_stage_effect_descriptions(
        self,
        move: dict,
    ) -> list[str]:
        """Translate modeled stat-stage changes into plain English."""

        stat_fields = [
            (
                "AtkStageChange",
                "Attack",
            ),
            (
                "DefStageChange",
                "Defense",
            ),
            (
                "SpAStageChange",
                "Special Attack",
            ),
            (
                "SpDStageChange",
                "Special Defense",
            ),
            (
                "SpeStageChange",
                "Speed",
            ),
        ]

        changes: list[tuple[str, int]] = []

        for field_name, stat_name in stat_fields:
            raw_change = self._numeric_move_value(
                move.get(field_name)
            )

            if raw_change is None:
                continue

            stage_change = int(raw_change)

            if stage_change == 0:
                continue

            changes.append(
                (
                    stat_name,
                    stage_change,
                )
            )

        if not changes:
            return []

        raw_tags = move.get(
            "MechanicsTags"
        )

        tags = (
            {
                tag
                for tag in raw_tags
                if isinstance(tag, str)
            }
            if isinstance(raw_tags, list)
            else set()
        )

        is_setup_move = any(
            tag.endswith("Setup")
            for tag in tags
        )

        grouped_changes: dict[
            tuple[str, int, str],
            list[str],
        ] = {}

        for stat_name, stage_change in changes:
            if is_setup_move:
                subject = "user"
            elif stage_change > 0:
                subject = "user"
            else:
                subject = "target"

            direction = (
                "raises"
                if stage_change > 0
                else "lowers"
            )

            magnitude = abs(
                stage_change
            )

            group_key = (
                direction,
                magnitude,
                subject,
            )

            grouped_changes.setdefault(
                group_key,
                [],
            ).append(
                stat_name
            )

        descriptions: list[str] = []

        for (
            direction,
            magnitude,
            subject,
        ), stat_names in grouped_changes.items():
            subject_text = (
                "the user's"
                if subject == "user"
                else "the target's"
            )

            combined_stats = (
                self._combine_stat_names(
                    stat_names
                )
            )

            stage_word = (
                "stage"
                if magnitude == 1
                else "stages"
            )

            each_text = (
                " each"
                if len(stat_names) > 1
                else ""
            )

            descriptions.append(
                (
                    f"{direction.capitalize()} "
                    f"{subject_text} "
                    f"{combined_stats} by "
                    f"{magnitude} {stage_word}"
                    f"{each_text}."
                )
            )

        return descriptions


    @staticmethod
    def _combine_stat_names(
        stat_names: list[str],
    ) -> str:
        """Join stat names using natural English punctuation."""

        if not stat_names:
            return ""

        if len(stat_names) == 1:
            return stat_names[0]

        if len(stat_names) == 2:
            return (
                f"{stat_names[0]} and "
                f"{stat_names[1]}"
            )

        return (
            ", ".join(
                stat_names[:-1]
            )
            + f", and {stat_names[-1]}"
        )


    def _move_navigation_aids(
        self,
        move: dict,
    ) -> list[str]:
        """Translate relevant mechanics into player-facing notes."""

        aids: list[str] = []

        if bool(move.get("UseDEF")):
            aids.append(
                (
                    "Uses the user's Defense instead of "
                    "Attack when calculating damage."
                )
            )

        if bool(move.get("TargetDEFasSPD")):
            aids.append(
                (
                    "Targets the opponent's Defense instead "
                    "of Special Defense."
                )
            )

        if bool(move.get("TargetATK")):
            aids.append(
                (
                    "Uses the target's Attack instead of "
                    "the user's Attack when calculating damage."
                )
            )

        if bool(move.get("MakesContact")):
            aids.append(
                (
                    "Makes contact, so it can trigger "
                    "contact-based abilities and effects."
                )
            )

        hits = self._numeric_move_value(
            move.get("Hits")
        )

        if hits is not None and hits > 1:
            hit_count = self._format_number(
                hits
            )

            aids.append(
                f"Hits {hit_count} times."
            )

        priority = self._numeric_move_value(
            move.get("Priority")
        )

        if priority is not None:
            if priority > 0:
                priority_text = (
                    f"+{self._format_number(priority)}"
                )

                aids.append(
                    (
                        f"Has {priority_text} priority, so it "
                        "usually moves before standard-priority moves."
                    )
                )
            elif priority < 0:
                aids.append(
                    (
                        f"Has {self._format_number(priority)} priority, "
                        "so it usually moves after standard-priority moves."
                    )
                )

        raw_tags = move.get(
            "MechanicsTags"
        )

        tags = (
            raw_tags
            if isinstance(raw_tags, list)
            else []
        )

        for tag in tags:
            if not isinstance(tag, str):
                continue

            description = (
                MOVE_TAG_DESCRIPTIONS.get(
                    tag
                )
            )

            if (
                description
                and description not in aids
            ):
                aids.append(
                    description
                )

        return aids


    @staticmethod
    def _activation_condition_description(
        condition: str | None,
    ) -> str | None:
        """Translate a modeled activation condition."""

        if not condition:
            return None

        normalized = "".join(
            character
            for character in condition.lower()
            if character.isalnum()
        )

        if normalized == "always":
            return None

        return (
            ACTIVATION_CONDITION_DESCRIPTIONS.get(
                normalized
            )
        )


    @classmethod
    def _multiplier_description(
        cls,
        multiplier: float,
        condition_description: str,
    ) -> str:
        """Describe an exact conditional damage multiplier."""

        if multiplier == 2:
            return (
                "Damage is doubled "
                f"{condition_description}."
            )

        if multiplier == 3:
            return (
                "Damage is tripled "
                f"{condition_description}."
            )

        increase_percent = round(
            (multiplier - 1) * 100
        )

        if increase_percent > 0:
            return (
                f"Damage increases by {increase_percent}% "
                f"{condition_description}."
            )

        return (
            "Damage is multiplied by "
            f"{cls._format_number(multiplier)}× "
            f"{condition_description}."
        )


    @classmethod
    def _status_effect_description(
        cls,
        status_effect: object,
        *,
        is_status_move: bool,
    ) -> str | None:
        """Translate available status-effect metadata."""

        if not status_effect:
            return None

        if isinstance(status_effect, str):
            normalized_status = (
                status_effect.strip().lower()
            )

            if not normalized_status:
                return None

            guaranteed_effects = {
                "burn": "Burns the target.",
                "burned": "Burns the target.",
                "paralysis": "Paralyzes the target.",
                "paralyze": "Paralyzes the target.",
                "paralyzed": "Paralyzes the target.",
                "poison": "Poisons the target.",
                "poisoned": "Poisons the target.",
                "badly poison": (
                    "Badly poisons the target."
                ),
                "badly poisoned": (
                    "Badly poisons the target."
                ),
                "sleep": (
                    "Puts the target to sleep."
                ),
                "asleep": (
                    "Puts the target to sleep."
                ),
                "freeze": "Freezes the target.",
                "frozen": "Freezes the target.",
                "confusion": "Confuses the target.",
                "confused": "Confuses the target.",
                "flinch": (
                    "Makes the target flinch."
                ),
            }

            guaranteed_description = (
                guaranteed_effects.get(
                    normalized_status
                )
            )

            if (
                is_status_move
                and guaranteed_description
            ):
                return guaranteed_description

            possible_effects = {
                "burn": (
                    "Can burn the target."
                ),
                "burned": (
                    "Can burn the target."
                ),
                "paralysis": (
                    "Can paralyze the target."
                ),
                "paralyze": (
                    "Can paralyze the target."
                ),
                "paralyzed": (
                    "Can paralyze the target."
                ),
                "poison": (
                    "Can poison the target."
                ),
                "poisoned": (
                    "Can poison the target."
                ),
                "badly poison": (
                    "Can badly poison the target."
                ),
                "badly poisoned": (
                    "Can badly poison the target."
                ),
                "sleep": (
                    "Can put the target to sleep."
                ),
                "asleep": (
                    "Can put the target to sleep."
                ),
                "freeze": (
                    "Can freeze the target."
                ),
                "frozen": (
                    "Can freeze the target."
                ),
                "confusion": (
                    "Can confuse the target."
                ),
                "confused": (
                    "Can confuse the target."
                ),
                "flinch": (
                    "Can make the target flinch."
                ),
            }

            return possible_effects.get(
                normalized_status,
                (
                    "Can apply "
                    f"{normalized_status} to the target."
                ),
            )

        if not isinstance(
            status_effect,
            dict,
        ):
            return None

        status_name = cls._clean_text(
            status_effect.get("Status")
            or status_effect.get("Effect")
            or status_effect.get("Name")
        )

        if not status_name:
            return None

        chance = cls._numeric_move_value(
            status_effect.get("Chance")
            or status_effect.get("Percent")
        )

        if chance is not None:
            return (
                f"Has a {cls._format_number(chance)}% chance "
                f"to apply {status_name.lower()} "
                "to the target."
            )

        if is_status_move:
            return (
                f"Applies {status_name.lower()} "
                "to the target."
            )

        return (
            f"Can apply {status_name.lower()} "
            "to the target."
        )


    @staticmethod
    def _priority_label(
        priority: float | None,
    ) -> str:
        """Return a concise player-facing priority label."""

        if priority is None or priority == 0:
            return "Normal"

        if priority > 0:
            return (
                f"+{MyTeamView._format_number(priority)}"
            )

        return MyTeamView._format_number(
            priority
        )


    @classmethod
    def _display_move_value(
        cls,
        value: object,
    ) -> str:
        """Format Power or a similar move value."""

        numeric_value = (
            cls._numeric_move_value(
                value
            )
        )

        if numeric_value is None:
            return "—"

        return cls._format_number(
            numeric_value
        )


    @staticmethod
    def _numeric_move_value(
        value: object,
    ) -> float | None:
        """Safely convert a move metadata value to a number."""

        if isinstance(value, bool):
            return float(
                int(value)
            )

        if isinstance(value, int | float):
            return float(value)

        if isinstance(value, str):
            normalized = value.strip()

            if not normalized:
                return None

            try:
                return float(
                    normalized
                )
            except ValueError:
                return None

        return None


    @staticmethod
    def _format_number(
        value: float,
    ) -> str:
        """Display whole numbers without a trailing decimal."""

        if value.is_integer():
            return str(
                int(value)
            )

        return f"{value:g}"


    @staticmethod
    def _clean_text(
        value: object,
    ) -> str | None:
        """Return a stripped string or None."""

        if not isinstance(value, str):
            return None

        cleaned = value.strip()

        return cleaned or None


    def _close_move_details(
        self,
        event: ft.Event[ft.Button],
    ) -> None:
        """Close the move-detail dialog."""

        del event
        self.page.pop_dialog()
        self.page.update()
        

    def _build_footer(
        self,
        pokemon: dict,
    ) -> ft.Control:
        """Build Ability and Held Item cards."""

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
                                        size=18,
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
                        height=80,
                        padding=14,
                        bgcolor=PRIMARY_BLUE_SOFT,
                        border_radius=10,
                    ),
                    ft.Container(
                        content=ft.Column(
                            controls=cast(
                                list[ft.Control],
                                [
                                    ft.Row(
                                        controls=cast(
                                            list[ft.Control],
                                            [
                                                ft.Text(
                                                    "Held Item",
                                                    size=13,
                                                    color=TEXT_MUTED,
                                                    expand=True,
                                                ),
                                                ft.IconButton(
                                                    icon=ft.Icons.HELP_OUTLINE_ROUNDED,
                                                    icon_size=18,
                                                    icon_color=SUCCESS_SOFT,
                                                    tooltip="View held item recommendations",
                                                    width=20,
                                                    height=20,
                                                    style=ft.ButtonStyle(
                                                        padding=0,
                                                        shape=ft.RoundedRectangleBorder(radius=4),
                                                    ),
                                                    on_click=lambda event: (
                                                        self._show_item_recommendations(
                                                            event,
                                                            pokemon,
                                                        )
                                                    ),
                                                ),
                                            ],
                                        ),
                                        spacing=6,
                                        vertical_alignment=(
                                            ft.CrossAxisAlignment.CENTER
                                        ),
                                    ),
                                    ft.Text(
                                        str(
                                            pokemon.get("Held Item")
                                            or "—"
                                        ),
                                        size=18,
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
                        height=80,
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

    def _show_item_recommendations(
        self,
        event: ft.Event[ft.IconButton],
        pokemon: dict,
    ) -> None:
        """Show modeled held items that fit the selected Pokémon."""

        del event

        recommendations = recommend_held_items(
            pokemon=pokemon,
            moves_data=self.moves_data,
            items_data=self.items_data,
        )

        pokemon_name = str(
            pokemon.get("Pokemon")
            or "this Pokémon"
        )

        self.page.show_dialog(
            ft.AlertDialog(
                modal=True,
                title=ft.Text(
                    "Suggested Held Items",
                    weight=ft.FontWeight.BOLD,
                    color=TEXT_PRIMARY,
                ),
                content=ft.Container(
                    content=self._build_item_recommendation_content(
                        pokemon_name,
                        recommendations,
                    ),
                    width=560,
                    height=480,
                ),
                actions=cast(
                    list[ft.Control],
                    [
                        ft.Button(
                            content="Close",
                            on_click=self._close_item_recommendations,
                        ),
                    ],
                ),
                actions_alignment=ft.MainAxisAlignment.END,
            )
        )

    def _build_item_recommendation_content(
        self,
        pokemon_name: str,
        recommendations: list[ItemRecommendation],
    ) -> ft.Control:
        """Build the scrollable recommendation-dialog content."""

        controls = cast(
            list[ft.Control],
            [
                ft.Text(
                    (
                        "These modeled items fit "
                        f"{pokemon_name}'s current build. "
                        "They are presented as options, not ranked "
                        "from best to worst."
                    ),
                    size=14,
                    color=TEXT_SECONDARY,
                ),
            ],
        )

        if not recommendations:
            controls.append(
                ft.Container(
                    content=ft.Text(
                        (
                            "No currently modeled held items match "
                            "this build yet."
                        ),
                        size=15,
                        color=TEXT_SECONDARY,
                        text_align=ft.TextAlign.CENTER,
                    ),
                    padding=24,
                    bgcolor=SURFACE_RAISED,
                    border_radius=12,
                    alignment=ft.Alignment.CENTER,
                )
            )
        else:
            controls.extend(
                self._build_item_recommendation_card(
                    recommendation
                )
                for recommendation in recommendations
            )

        return ft.Column(
            controls=controls,
            spacing=14,
            scroll=ft.ScrollMode.AUTO,
        )

    @staticmethod
    def _build_item_recommendation_card(
        recommendation: ItemRecommendation,
    ) -> ft.Control:
        """Build one unranked held-item recommendation card."""

        reason_controls = cast(
            list[ft.Control],
            [
                ft.Row(
                    controls=cast(
                        list[ft.Control],
                        [
                            ft.Icon(
                                ft.Icons.CHECK_CIRCLE_OUTLINE_ROUNDED,
                                size=17,
                                color=SUCCESS,
                            ),
                            ft.Text(
                                reason,
                                size=14,
                                color=TEXT_SECONDARY,
                                expand=True,
                            ),
                        ],
                    ),
                    spacing=8,
                    vertical_alignment=ft.CrossAxisAlignment.START,
                )
                for reason in recommendation.reasons
            ],
        )

        return ft.Container(
            content=ft.Column(
                controls=cast(
                    list[ft.Control],
                    [
                        ft.Text(
                            recommendation.item,
                            size=19,
                            weight=ft.FontWeight.BOLD,
                            color=TEXT_PRIMARY,
                        ),
                        ft.Text(
                            recommendation.description,
                            size=14,
                            color=TEXT_SECONDARY,
                        ),
                        ft.Text(
                            "Why this item?",
                            size=14,
                            weight=ft.FontWeight.BOLD,
                            color=TEXT_PRIMARY,
                        ),
                        *reason_controls,
                    ],
                ),
                spacing=9,
            ),
            padding=16,
            bgcolor=PRIMARY_BLUE_SOFT,
            border=ft.Border.all(
                1,
                BORDER_DEFAULT,
            ),
            border_radius=12,
        )

    def _close_item_recommendations(
        self,
        event: ft.Event[ft.Button],
    ) -> None:
        """Close the held-item recommendation dialog."""

        del event
        self.page.pop_dialog()
        self.page.update()

    async def _save_team(
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

                if (
                    move_name
                    and move_name not in self.move_lookup
                ):
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

        try:
            save_succeeded = await self.app_state.save_team(
                saved_team
            )
        except (RuntimeError, ValueError) as error:
            self.save_status.value = (
                f"Team could not be saved: {error}"
            )
            self.save_status.color = "#F87171"
            self.page.update()
            return

        if not save_succeeded:
            self.save_status.value = (
                "Team could not be saved."
            )
            self.save_status.color = "#F87171"
            self.page.update()
            return

        self.team_data = self.app_state.team_data
        self.working_team = deepcopy(
            self.app_state.team_data
        )
        self.saved_team_snapshot = deepcopy(
            self.app_state.team_data
        )
        self.save_button.disabled = True

        if self.on_team_updated:
            self.on_team_updated(
                self.app_state.team_data
            )

        self.save_status.value = "Team saved."
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
