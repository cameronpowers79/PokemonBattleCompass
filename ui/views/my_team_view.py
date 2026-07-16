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
from ui.constants import POKEMON_TYPES, TYPE_COLORS
from ui.rendering import (
    get_item_sprite_src,
    get_sprite_path,
)
from ui.components.reference_dialogs import (
    show_ability_dialog,
    show_item_dialog,
    show_type_matchup_dialog,
)
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
    "RecoveryMove": (
        "Restores some of the user's HP."
    ),
    "Drain": (
        "Restores HP based on the damage dealt."
    ),
    "HPStealingMove": (
        "Restores HP based on the damage dealt."
    ),
    "Recoil": (
        "The user takes recoil damage after attacking."
    ),
    "RecoilMove": (
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
    "requiresuserhit": (
        "if the user was hit earlier in the turn"
    ),
    "userburnpoisonparalysis": (
        "while the user is burned, poisoned, or paralyzed"
    ),
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
        self.type_chart = cast(
            dict,
            app_state.reference_data["type_chart"],
        )
        self.ability_rules = (
            app_state.reference_data["ability_rules"]
        )
        self.ability_descriptions = {
            row["Ability"]: row["Description"]
            for row in app_state.reference_data.get(
                "ability_descriptions",
                [],
            )
            if isinstance(row, dict)
            and isinstance(row.get("Ability"), str)
            and isinstance(row.get("Description"), str)
        }

        raw_pokemon_validation = (
            app_state.reference_data.get(
                "pokemon_validation",
                [],
            )
        )

        self.pokemon_options = sorted(
            {
                pokemon_name.strip()
                for pokemon_name in raw_pokemon_validation
                if isinstance(pokemon_name, str)
                and pokemon_name.strip()
            }
        )

        self.pokemon_lookup = set(
            self.pokemon_options
        )

        self.pokemon_suggestions = [
            ft.AutoCompleteSuggestion(
                key=pokemon_name,
                value=pokemon_name,
            )
            for pokemon_name in self.pokemon_options
        ]

        self.type_options = list(
            POKEMON_TYPES
        )
        self.type_lookup = set(
            self.type_options
        )

        raw_item_validation = (
            app_state.reference_data.get(
                "item_validation",
                [],
            )
        )

        self.item_options = sorted(
            {
                item_name.strip()
                for item_name in raw_item_validation
                if isinstance(item_name, str)
                and item_name.strip()
            }
            | {"None"}
        )

        self.item_lookup = set(
            self.item_options
        )

        self.item_suggestions = [
            ft.AutoCompleteSuggestion(
                key=item_name,
                value=item_name,
            )
            for item_name in self.item_options
        ]
        raw_abilities = app_state.reference_data.get(
            "abilities",
            [],
        )

        self.ability_options = sorted(
            ability
            for ability in raw_abilities
            if isinstance(ability, str)
            and ability.strip()
        )

        self.ability_lookup = set(
            self.ability_options
        )

        self.ability_suggestions = [
            ft.AutoCompleteSuggestion(
                key=ability_name,
                value=ability_name,
            )
            for ability_name in self.ability_options
        ]
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
        self.party_management_selected_index: int | None = None

        self.party_management_host = ft.Container()
        self.box_pokemon_button: ft.Button | None = None
        self.release_pokemon_button: ft.Button | None = None

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

        self.add_pokemon_button = ft.Button(
            content="Add Pokémon",
            icon=ft.Icons.ADD_ROUNDED,
            disabled=(
                len(self.working_team) >= 6
            ),
            on_click=self._add_pokemon,
            style=ft.ButtonStyle(
                bgcolor=SUCCESS_SOFT,
                color=TEXT_PRIMARY,
                icon_color=TEXT_PRIMARY,
                elevation=1,
            ),
        )

        self.manage_party_button = ft.Button(
            content="Box / Release Pokémon",
            icon=ft.Icons.ARCHIVE_OUTLINED,
            disabled=not self.working_team,
            on_click=self._show_party_management_dialog,
            style=ft.ButtonStyle(
                bgcolor=SURFACE_RAISED,
                color=TEXT_PRIMARY,
                icon_color=TEXT_SECONDARY,
                elevation=1,
            ),
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
        self._sync_team_management_buttons()

    def _add_pokemon(
        self,
        event: ft.Event[ft.Button],
    ) -> None:
        """Add a blank Pokémon slot to the working team."""

        del event

        if len(self.working_team) >= 6:
            self._sync_team_management_buttons()
            self.page.update()
            return

        self.working_team.append(
            self._blank_pokemon_record()
        )

        self.selected_index = (
            len(self.working_team) - 1
        )

        self.editor_controls.clear()

        self.table_host.content = (
            self._build_editor_table()
        )

        self._refresh_selector()
        self._refresh_detail()
        self._update_dirty_state()
        self._sync_team_management_buttons()

        self.page.update()

    @staticmethod
    def _blank_pokemon_record() -> dict:
        """Return a new editable Pokémon team record."""

        return {
            "Pokemon": "",
            "Gender": "",
            "Type1": "",
            "Type2": "",
            "Level": 1,
            "HP": 0,
            "ATK": 0,
            "DEF": 0,
            "SPA": 0,
            "SPD": 0,
            "SPE": 0,
            "Move1": "",
            "Move2": "",
            "Move3": "",
            "Move4": "",
            "Ability": "",
            "Held Item": "",
        }

    def _sync_team_management_buttons(
        self,
    ) -> None:
        """Synchronize party-composition action buttons."""

        self.add_pokemon_button.disabled = (
            len(self.working_team) >= 6
        )
        self.manage_party_button.disabled = (
            not self.working_team
        )

    def _show_party_management_dialog(
        self,
        event: ft.Event[ft.Button],
    ) -> None:
        """Open the active-party management dialog."""

        del event

        self.party_management_selected_index = None

        self.box_pokemon_button = ft.Button(
            content="Box Pokémon",
            icon=ft.Icons.ARCHIVE_OUTLINED,
            disabled=True,
            on_click=self._request_box_selected_pokemon,
        )

        self.release_pokemon_button = ft.Button(
            content="Release Pokémon",
            icon=ft.Icons.DELETE_OUTLINE_ROUNDED,
            disabled=True,
            color="#FCA5A5",
            icon_color="#FCA5A5",
            on_click=self._request_release_selected_pokemon,
        )

        self.party_management_host.content = (
            self._build_party_management_content()
        )

        self.page.show_dialog(
            ft.AlertDialog(
                modal=True,
                title=ft.Text(
                    "Box / Release Pokémon",
                    weight=ft.FontWeight.BOLD,
                    color=TEXT_PRIMARY,
                ),
                content=ft.Container(
                    content=self.party_management_host,
                    width=520,
                ),
                actions=cast(
                    list[ft.Control],
                    [
                        ft.Button(
                            content="Cancel",
                            on_click=self._close_party_management_dialog,
                        ),
                        self.box_pokemon_button,
                        self.release_pokemon_button,
                    ],
                ),
                actions_alignment=ft.MainAxisAlignment.END,
            )
        )

    def _build_party_management_content(
        self,
    ) -> ft.Control:
        """Build the selectable active-party list."""

        controls = cast(
            list[ft.Control],
            [
                ft.Text(
                    (
                        "Choose a Pokémon from your active party. "
                        "Boxing or releasing it removes it from the "
                        "current team after confirmation."
                    ),
                    size=14,
                    color=TEXT_SECONDARY,
                ),
            ],
        )

        controls.extend(
            self._build_party_member_row(
                index,
                pokemon,
            )
            for index, pokemon in enumerate(
                self.working_team
            )
        )

        if len(self.working_team) <= 1:
            controls.append(
                ft.Container(
                    content=ft.Text(
                        (
                            "Your Journey must always contain at "
                            "least one Pokémon."
                        ),
                        size=14,
                        color="#FFE5A3",
                        text_align=ft.TextAlign.CENTER,
                    ),
                    padding=12,
                    bgcolor="#3B3017",
                    border_radius=10,
                    alignment=ft.Alignment.CENTER,
                )
            )

        return ft.Column(
            controls=controls,
            spacing=10,
            tight=True,
        )

    def _build_party_member_row(
        self,
        index: int,
        pokemon: dict,
    ) -> ft.Control:
        """Build one selectable Pokémon row."""

        pokemon_name = str(
            pokemon.get("Pokemon")
            or f"Team Slot {index + 1}"
        )

        sprite_path = get_sprite_path(
            pokemon_name,
            gender=pokemon.get("Gender"),
            use_texture=False,
        )

        if sprite_path is None:
            sprite: ft.Control = ft.Container(
                content=ft.Icon(
                    ft.Icons.HELP_OUTLINE_ROUNDED,
                    size=24,
                    color=TEXT_MUTED,
                ),
                width=46,
                height=46,
                alignment=ft.Alignment.CENTER,
            )
        else:
            sprite = ft.Image(
                src=self._asset_src(sprite_path),
                width=46,
                height=46,
                fit=ft.BoxFit.CONTAIN,
                semantics_label=pokemon_name,
            )

        is_selected = (
            index
            == self.party_management_selected_index
        )

        return ft.Container(
            content=ft.Row(
                controls=cast(
                    list[ft.Control],
                    [
                        sprite,
                        ft.Column(
                            controls=cast(
                                list[ft.Control],
                                [
                                    ft.Text(
                                        pokemon_name,
                                        size=17,
                                        weight=ft.FontWeight.BOLD,
                                        color=TEXT_PRIMARY,
                                    ),
                                    ft.Text(
                                        (
                                            f"Lv. "
                                            f"{pokemon.get('Level', '—')}"
                                        ),
                                        size=13,
                                        color=TEXT_MUTED,
                                    ),
                                ],
                            ),
                            spacing=2,
                            expand=True,
                        ),
                        ft.Icon(
                            (
                                ft.Icons.CHECK_CIRCLE_ROUNDED
                                if is_selected
                                else ft.Icons.CIRCLE_OUTLINED
                            ),
                            size=22,
                            color=(
                                PRIMARY_BLUE
                                if is_selected
                                else TEXT_MUTED
                            ),
                        ),
                    ],
                ),
                spacing=12,
                vertical_alignment=ft.CrossAxisAlignment.CENTER,
            ),
            padding=12,
            bgcolor=(
                PRIMARY_BLUE_SOFT
                if is_selected
                else SURFACE_RAISED
            ),
            border=ft.Border.all(
                1,
                (
                    PRIMARY_BLUE
                    if is_selected
                    else BORDER_DEFAULT
                ),
            ),
            border_radius=12,
            on_click=(
                lambda event, selected_index=index:
                self._select_party_member(
                    event,
                    selected_index,
                )
            ),
        )

    def _select_party_member(
        self,
        event: ft.Event[ft.Container],
        selected_index: int,
    ) -> None:
        """Select one Pokémon for boxing or release."""

        del event

        self.party_management_selected_index = (
            selected_index
        )

        self.party_management_host.content = (
            self._build_party_management_content()
        )

        actions_enabled = (
            len(self.working_team) > 1
        )

        if self.box_pokemon_button is not None:
            self.box_pokemon_button.disabled = (
                not actions_enabled
            )

        if self.release_pokemon_button is not None:
            self.release_pokemon_button.disabled = (
                not actions_enabled
            )

        self.page.update()

    def _request_box_selected_pokemon(
        self,
        event: ft.Event[ft.Button],
    ) -> None:
        """Ask for confirmation before boxing the selected Pokémon."""

        del event
        self._show_remove_confirmation(
            action="box",
        )

    def _request_release_selected_pokemon(
        self,
        event: ft.Event[ft.Button],
    ) -> None:
        """Ask for confirmation before releasing the selected Pokémon."""

        del event
        self._show_remove_confirmation(
            action="release",
        )

    def _show_remove_confirmation(
        self,
        *,
        action: str,
    ) -> None:
        """Show a confirmation dialog for a party-removal action."""

        selected_index = (
            self.party_management_selected_index
        )

        if (
            selected_index is None
            or selected_index < 0
            or selected_index >= len(self.working_team)
            or len(self.working_team) <= 1
        ):
            return

        pokemon_name = str(
            self.working_team[
                selected_index
            ].get("Pokemon")
            or f"Team Slot {selected_index + 1}"
        )

        self.page.pop_dialog()

        if action == "box":
            title = f"Box {pokemon_name}?"
            message = (
                f"{pokemon_name} will be removed from your "
                "active party. Boxed Pokémon will be available "
                "again once PC storage is added."
            )
            confirm_label = "Box Pokémon"
            confirm_icon = ft.Icons.ARCHIVE_OUTLINED
            confirm_color = PRIMARY_BLUE
        else:
            title = f"Release {pokemon_name}?"
            message = (
                f"This removes {pokemon_name} from your Journey. "
                "This action cannot currently be undone after "
                "the team is saved."
            )
            confirm_label = "Release Pokémon"
            confirm_icon = ft.Icons.DELETE_OUTLINE_ROUNDED
            confirm_color = "#B94A55"

        self.page.show_dialog(
            ft.AlertDialog(
                modal=True,
                title=ft.Text(
                    title,
                    weight=ft.FontWeight.BOLD,
                    color=TEXT_PRIMARY,
                ),
                content=ft.Text(
                    message,
                    size=15,
                    color=TEXT_SECONDARY,
                ),
                actions=cast(
                    list[ft.Control],
                    [
                        ft.Button(
                            content="Cancel",
                            on_click=self._cancel_remove_confirmation,
                        ),
                        ft.Button(
                            content=confirm_label,
                            icon=confirm_icon,
                            bgcolor=confirm_color,
                            color=TEXT_PRIMARY,
                            icon_color=TEXT_PRIMARY,
                            on_click=self._confirm_remove_pokemon,
                        ),
                    ],
                ),
                actions_alignment=ft.MainAxisAlignment.END,
            )
        )

    def _confirm_remove_pokemon(
        self,
        event: ft.Event[ft.Button],
    ) -> None:
        """Remove the selected Pokémon from the working party."""

        del event

        selected_index = (
            self.party_management_selected_index
        )

        if (
            selected_index is None
            or selected_index < 0
            or selected_index >= len(self.working_team)
            or len(self.working_team) <= 1
        ):
            self.page.pop_dialog()
            self.page.update()
            return

        self.working_team.pop(
            selected_index
        )

        self.selected_index = min(
            self.selected_index,
            len(self.working_team) - 1,
        )

        self.party_management_selected_index = None
        self.editor_controls.clear()

        self.table_host.content = (
            self._build_editor_table()
        )

        self._refresh_selector()
        self._refresh_detail()
        self._update_dirty_state()
        self._sync_team_management_buttons()

        self.page.pop_dialog()
        self.page.update()

    def _cancel_remove_confirmation(
        self,
        event: ft.Event[ft.Button],
    ) -> None:
        """Cancel a pending box or release action."""

        del event

        self.party_management_selected_index = None
        self.page.pop_dialog()
        self.page.update()

    def _close_party_management_dialog(
        self,
        event: ft.Event[ft.Button],
    ) -> None:
        """Close the party-management dialog."""

        del event

        self.party_management_selected_index = None
        self.page.pop_dialog()
        self.page.update()

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
                                    self.add_pokemon_button,
                                    self.manage_party_button,
                                    self.save_button,
                                    self.save_status,
                                ],
                            ),
                            spacing=14,
                            wrap=True,
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
        if column == "Pokemon":
            control = ft.AutoComplete(
                value=(
                    str(value)
                    if value
                    else ""
                ),
                suggestions=self.pokemon_suggestions,
                suggestions_max_height=240,
                width=165,
                on_change=(
                    lambda event,
                    row=row_index,
                    field=column:
                    self._handle_pokemon_change(
                        event,
                        row,
                        field,
                    )
                ),
            )
        elif column == "Gender":
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
        elif column in {"Type1", "Type2"}:
            control = ft.AutoComplete(
                value=(
                    str(value)
                    if value
                    else ""
                ),
                suggestions=[
                    ft.AutoCompleteSuggestion(
                        key=pokemon_type,
                        value=pokemon_type,
                    )
                    for pokemon_type in self.type_options
                ],
                suggestions_max_height=240,
                width=125,
                on_change=(
                    lambda event,
                    row=row_index,
                    field=column:
                    self._handle_type_change(
                        event,
                        row,
                        field,
                    )
                ),
            )
        elif column == "Ability":
            control = ft.AutoComplete(
                value=(
                    str(value)
                    if value
                    else ""
                ),
                suggestions=self.ability_suggestions,
                suggestions_max_height=240,
                width=165,
                on_change=(
                    lambda event,
                    row=row_index,
                    field=column:
                    self._handle_ability_change(
                        event,
                        row,
                        field,
                    )
                ),
            )
        elif column == "Held Item":
            control = ft.AutoComplete(
                value=(
                    str(value)
                    if value
                    else ""
                ),
                suggestions=self.item_suggestions,
                suggestions_max_height=240,
                width=165,
                on_change=(
                    lambda event,
                    row=row_index,
                    field=column:
                    self._handle_item_change(
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

    def _handle_pokemon_change(
        self,
        event: ft.Event[ft.AutoComplete],
        row_index: int,
        column: str,
    ) -> None:
        """Update an edited Pokémon name."""

        pokemon_name = (
            event.control.value or ""
        ).strip()

        self.working_team[
            row_index
        ][column] = pokemon_name

        self._update_dirty_state()
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

    def _handle_ability_change(
        self,
        event: ft.Event[ft.AutoComplete],
        row_index: int,
        column: str,
    ) -> None:
        """Update an edited Ability value."""

        ability_name = (
            event.control.value or ""
        ).strip()

        self.working_team[
            row_index
        ][column] = ability_name

        self._update_dirty_state()

        if row_index == self.selected_index:
            self._refresh_detail()

        self.page.update()

    def _handle_item_change(
        self,
        event: ft.Event[ft.AutoComplete],
        row_index: int,
        column: str,
    ) -> None:
        """Update an edited held-item value."""

        item_name = (
        event.control.value or ""
        ).strip()

        self.working_team[
            row_index
        ][column] = item_name

        self._update_dirty_state()

        if row_index == self.selected_index:
            self._refresh_detail()

        self.page.update()

    def _handle_type_change(
        self,
        event: ft.Event[ft.AutoComplete],
        row_index: int,
        column: str,
    ) -> None:
        """Update an edited Pokémon type."""

        pokemon_type = (
            event.control.value or ""
        ).strip()

        self.working_team[
            row_index
        ][column] = pokemon_type

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
                                        expand=True,
                                    ),
                                ],
                            ),
                            spacing=3,
                            
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
                badge_control: ft.Control = ft.Image(
                    src=self._asset_src(badge_path),
                    height=24,
                    fit=ft.BoxFit.CONTAIN,
                    semantics_label=f"{pokemon_type} type",
                )
            else:
                badge_control = ft.Text(
                    pokemon_type,
                    color=TEXT_SECONDARY,
                )

            badges.append(
                ft.GestureDetector(
                    content=badge_control,
                    mouse_cursor=ft.MouseCursor.CLICK,
                    on_tap=(
                        lambda event,
                        selected_type=pokemon_type:
                        self._show_type_matchups(
                            event,
                            selected_type,
                        )
                    ),
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

        card = ft.Container(
            content=ft.Row(
                controls=card_controls,
                spacing=8,
                vertical_alignment=(
                    ft.CrossAxisAlignment.CENTER
                ),
            ),
            padding=14,
            bgcolor=background,
            opacity=1.0 if move else 0.55,
            border_radius=10,
            tooltip=(
                f"View details for {move_name}"
                if move
                else None
            ),
        )

        clickable_card: ft.Control = card

        if move is not None:
            clickable_card = ft.GestureDetector(
                content=card,
                mouse_cursor=ft.MouseCursor.CLICK,
                on_tap=(
                    lambda event, selected_move=move:
                    self._show_move_details(
                        event,
                        selected_move,
                    )
                ),
            )

        return ft.Container(
            content=clickable_card,
            col={
                "xs": 12,
                "sm": 6,
            },
        )

    def _show_move_details(
        self,
        event: ft.TapEvent[ft.GestureDetector],
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
        """Return the audited player-facing move description."""

        effect_description = self._clean_text(
            move.get("EffectDescription")
        )

        if effect_description:
            return [
                line.strip()
                for line in effect_description.splitlines()
                if line.strip()
            ]

        return [
            (
                "This move's full effect is not yet "
                "documented in the Battle Compass."
            )
        ]


    @classmethod
    def _stage_change_descriptions(
        cls,
        move: dict,
    ) -> list[str]:
        """Translate available stat-stage metadata for Status moves."""

        stat_fields = (
            ("AtkStageChange", "Attack"),
            ("DefStageChange", "Defense"),
            ("SpAStageChange", "Special Attack"),
            ("SpDStageChange", "Special Defense"),
            ("SpeStageChange", "Speed"),
        )

        descriptions: list[str] = []

        for field_name, stat_name in stat_fields:
            stage_change = cls._numeric_move_value(
                move.get(field_name)
            )

            if (
                stage_change is None
                or stage_change == 0
            ):
                continue

            stage_count = abs(
                int(stage_change)
            )

            stage_text = (
                "one stage"
                if stage_count == 1
                else f"{stage_count} stages"
            )

            if stage_change > 0:
                descriptions.append(
                    (
                        f"Raises the user's {stat_name} "
                        f"by {stage_text}."
                    )
                )
            else:
                descriptions.append(
                    (
                        f"Lowers the target's {stat_name} "
                        f"by {stage_text}."
                    )
                )

        return descriptions


    def _move_navigation_aids(
        self,
        move: dict,
    ) -> list[str]:
        """Translate relevant mechanics into player-facing notes."""

        aids: list[str] = []

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
        
    @staticmethod
    def _build_item_identity(
        item_name_value: object,
        *,
        sprite_size: int = 32,
        text_size: int = 18,
    ) -> ft.Control:
        """Build an item name with its bundled sprite when available."""

        item_name = str(
            item_name_value
            or "—"
        )

        controls = cast(
            list[ft.Control],
            [],
        )

        sprite_src = get_item_sprite_src(
            item_name_value
        )

        if sprite_src:
            controls.append(
                ft.Image(
                    src=sprite_src,
                    width=sprite_size,
                    height=sprite_size,
                    fit=ft.BoxFit.CONTAIN,
                    semantics_label=item_name,
                )
            )

        controls.append(
            ft.Text(
                item_name,
                size=text_size,
                weight=ft.FontWeight.BOLD,
                color=TEXT_PRIMARY,
                expand=True,
            )
        )

        return ft.Row(
            controls=controls,
            spacing=9,
            vertical_alignment=(
                ft.CrossAxisAlignment.CENTER
            ),
        )

    def _build_footer(
        self,
        pokemon: dict,
    ) -> ft.Control:
        """Build Ability and Held Item cards."""

        ability_name = str(
            pokemon.get("Ability")
            or "—"
        )

        ability_card = ft.Container(
            content=ft.Column(
                controls=cast(
                    list[ft.Control],
                    [
                        ft.Row(
                            controls=cast(
                                list[ft.Control],
                                [
                                    ft.Text(
                                        "Ability",
                                        size=13,
                                        color=TEXT_MUTED,
                                        expand=True,
                                    ),
                                    ft.Icon(
                                        ft.Icons.HELP_OUTLINE_ROUNDED,
                                        size=18,
                                        color=PRIMARY_BLUE,
                                    ),
                                ],
                            ),
                            spacing=6,
                        ),
                        ft.Text(
                            ability_name,
                            size=18,
                            weight=ft.FontWeight.BOLD,
                            color=TEXT_PRIMARY,
                        ),
                    ],
                ),
                spacing=4,
            ),
            height=80,
            padding=14,
            bgcolor=PRIMARY_BLUE_SOFT,
            border_radius=10,
        )

        clickable_ability: ft.Control = ability_card

        if ability_name != "—":
            clickable_ability = ft.GestureDetector(
                content=ability_card,
                mouse_cursor=ft.MouseCursor.CLICK,
                on_tap=(
                    lambda event:
                    self._show_ability_details(
                        event,
                        ability_name,
                    )
                ),
            )

        return ft.ResponsiveRow(
            controls=cast(
                list[ft.Control],
                [
                    ft.Container(
                        content=clickable_ability,
                        col={
                            "xs": 12,
                            "sm": 6,
                        },
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
                                                    icon_size=22,
                                                    icon_color=SUCCESS_SOFT,
                                                    tooltip="View held item recommendations",
                                                    width=20,
                                                    height=20,
                                                    style=ft.ButtonStyle(
                                                        padding=0,
                                                        shape=ft.RoundedRectangleBorder(
                                                            radius=4
                                                        ),
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
                                    self._build_clickable_item_identity(
                                        pokemon.get(
                                            "Held Item"
                                        ),
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

    def _build_clickable_item_identity(
        self,
        item_name_value: object,
    ) -> ft.Control:
        """Build the current-item identity with an information action."""

        item_name = (
            str(item_name_value).strip()
            if item_name_value
            else ""
        )

        identity = self._build_item_identity(
            item_name_value
        )

        if (
            not item_name
            or item_name == "None"
        ):
            return identity

        return ft.GestureDetector(
            content=identity,
            mouse_cursor=ft.MouseCursor.CLICK,
            on_tap=(
                lambda event:
                self._show_current_item_details(
                    event,
                    item_name,
                )
            ),
        )

    def _show_current_item_details(
        self,
        event: ft.TapEvent[ft.GestureDetector],
        item_name: str,
    ) -> None:
        """Show details for the Pokémon's currently held item."""

        del event

        show_item_dialog(
            page=self.page,
            item_name=item_name,
            items=self.items_data,
            item_sprite_src=(
                get_item_sprite_src(
                    item_name
                )
            ),
        )

    def _show_type_matchups(
        self,
        event: ft.TapEvent[ft.GestureDetector],
        pokemon_type: str,
    ) -> None:
        """Show defensive single-type matchup information."""

        del event

        show_type_matchup_dialog(
            page=self.page,
            pokemon_type=pokemon_type,
            type_chart=self.type_chart,
        )

    def _show_ability_details(
        self,
        event: ft.TapEvent[ft.GestureDetector],
        ability_name: str,
    ) -> None:
        """Show player-facing details for one Ability."""

        del event

        show_ability_dialog(
            page=self.page,
            ability_name=ability_name,
            ability_descriptions=(
                self.ability_descriptions
            ),
            ability_rules=self.ability_rules,
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
                        MyTeamView._build_item_identity(
                            recommendation.item,
                            sprite_size=38,
                            text_size=19,
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

        invalid_pokemon: list[str] = []
        invalid_types: list[str] = []
        invalid_moves: list[str] = []
        invalid_abilities: list[str] = []
        invalid_items: list[str] = []

        for pokemon in self.working_team:
            pokemon_name = str(
                pokemon.get("Pokemon") or ""
            ).strip()

            if (
                not pokemon_name
                or pokemon_name
                not in self.pokemon_lookup
            ):
                invalid_pokemon.append(
                    pokemon_name or "(blank)"
                )

            type1 = str(
                pokemon.get("Type1") or ""
            ).strip()

            type2 = str(
                pokemon.get("Type2") or ""
            ).strip()

            if (
                not type1
                or type1 not in self.type_lookup
            ):
                invalid_types.append(
                    type1 or "(blank Type1)"
                )

            if (
                type2
                and type2 not in self.type_lookup
            ):
                invalid_types.append(
                    type2
                )

            ability_name = str(
                pokemon.get("Ability") or ""
            ).strip()

            if (
                ability_name
                and ability_name
                not in self.ability_lookup
            ):
                invalid_abilities.append(
                    ability_name
                )

            item_name = str(
                pokemon.get("Held Item") or ""
            ).strip()

            if (
                item_name
                and item_name not in self.item_lookup
            ):
                invalid_items.append(
                    item_name
                )
            for slot in range(1, 5):
                move_name = str(
                    pokemon.get(f"Move{slot}") or ""
                ).strip()

                if (
                    move_name
                    and move_name not in self.move_lookup
                ):
                    invalid_moves.append(move_name)

        if invalid_pokemon:
            invalid_list = ", ".join(
                sorted(
                    set(
                        invalid_pokemon
                    )
                )
            )

            self.save_status.value = (
                "Invalid Pokémon selection: "
                f"{invalid_list}"
            )
            self.save_status.color = "#F87171"
            self.page.update()
            return

        if invalid_types:
            invalid_list = ", ".join(
                sorted(
                    set(
                        invalid_types
                    )
                )
            )

            self.save_status.value = (
                "Invalid type selection: "
                f"{invalid_list}"
            )
            self.save_status.color = "#F87171"
            self.page.update()
            return

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
        
        if invalid_items:
            invalid_list = ", ".join(
                sorted(
                    set(
                        invalid_items
                    )
                )
            )

            self.save_status.value = (
                "Invalid held-item selection: "
                f"{invalid_list}"
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

        if invalid_abilities:
            invalid_list = ", ".join(
                sorted(
                    set(
                        invalid_abilities
                    )
                )
            )

            self.save_status.value = (
                "Invalid Ability selection: "
                f"{invalid_list}"
            )
            self.save_status.color = "#F87171"
            self.page.update()
            return

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

        self.save_status.value = "Team is up to date."
        self.save_status.color = SUCCESS

        self._refresh_selector()
        self._refresh_detail()
        self._sync_team_management_buttons()

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