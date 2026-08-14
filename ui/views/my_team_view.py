
"""
My Team view.

Provides a bulk-editable team table and a selected Pokémon detail panel.
Saved changes update the active persistent Journey.
"""

from __future__ import annotations

import asyncio
import json
from importlib.metadata import PackageNotFoundError, version

from ui.viewmodels.app_state import AppState
from ui.storage.journey_storage import (
    journey_export_filename,
    parse_journey_export,
    serialize_journey_export,
)
from collections.abc import Awaitable, Callable
from copy import deepcopy
from pathlib import Path
from typing import cast

import flet as ft
import flet_datatable2 as fdt

from engine.item_recommendations import (
    ItemRecommendation,
    recommend_held_items,
)
from engine.moves import apply_move_metadata
from ui.constants import POKEMON_TYPES, TYPE_COLORS
from ui.rendering import (
    asset_exists,
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
    TEXT_SIZE_CAPTION,
    TEXT_SIZE_DETAIL,
    TEXT_SIZE_BODY,
    TEXT_SIZE_FEATURED_TITLE,
    FONT_FAMILY_DISPLAY,
    FONT_FAMILY_HEADER,
)


PROJECT_ROOT = Path(__file__).resolve().parents[2]
ASSETS_DIR = PROJECT_ROOT / "assets"
DATA_DIR = PROJECT_ROOT / "data"

AUTOCOMPLETE_DEBOUNCE_SECONDS = 0.45
AUTOCOMPLETE_SUGGESTION_LIMIT = 30

# My Team action-button colors.
ADD_BUTTON_ACTIVE = "#4DA56A"
ADD_BUTTON_DISABLED = "#315F42"

MANAGE_BUTTON_ACTIVE = "#73508A"
MANAGE_BUTTON_DISABLED = "#4B355A"

SAVE_BUTTON_ACTIVE = PRIMARY_BLUE
SAVE_BUTTON_DISABLED = "#355E99"

DISCARD_BUTTON_ACTIVE = "#8B5A5A"
DISCARD_BUTTON_DISABLED = "#553A3A"

EXPORT_BUTTON_ACTIVE = "#3C93B6"
EXPORT_BUTTON_DISABLED = "#295E73"

LOAD_BUTTON_ACTIVE = "#9A7A39"
LOAD_BUTTON_DISABLED = "#655126"

BUTTON_DISABLED_TEXT = "#B8C1CF"

EDITABLE_COLUMNS = [
    "Pokemon",
    "Gender",
    "Nature",
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

DISPLAY_COLUMN_LABELS = {
    "Type1": "Primary Type",
    "Type2": "Secondary Type",
    "Move1": "Move 1",
    "Move2": "Move 2",
    "Move3": "Move 3",
    "Move4": "Move 4",
}

NUMERIC_COLUMNS = {
    "Level",
    "HP",
    "ATK",
    "DEF",
    "SPA",
    "SPD",
    "SPE",
}

NUMERIC_FOCUS_ORDER = [
    "Level",
    "HP",
    "ATK",
    "DEF",
    "SPA",
    "SPD",
    "SPE",
]

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

NATURE_EFFECTS: dict[str, tuple[str | None, str | None]] = {
    "Hardy": (None, None),
    "Lonely": ("ATK", "DEF"),
    "Brave": ("ATK", "SPE"),
    "Adamant": ("ATK", "SPA"),
    "Naughty": ("ATK", "SPD"),
    "Bold": ("DEF", "ATK"),
    "Docile": (None, None),
    "Relaxed": ("DEF", "SPE"),
    "Impish": ("DEF", "SPA"),
    "Lax": ("DEF", "SPD"),
    "Timid": ("SPE", "ATK"),
    "Hasty": ("SPE", "DEF"),
    "Serious": (None, None),
    "Jolly": ("SPE", "SPA"),
    "Naive": ("SPE", "SPD"),
    "Modest": ("SPA", "ATK"),
    "Mild": ("SPA", "DEF"),
    "Quiet": ("SPA", "SPE"),
    "Bashful": (None, None),
    "Rash": ("SPA", "SPD"),
    "Calm": ("SPD", "ATK"),
    "Gentle": ("SPD", "DEF"),
    "Sassy": ("SPD", "SPE"),
    "Careful": ("SPD", "SPA"),
    "Quirky": (None, None),
}

NATURE_OPTIONS = list(NATURE_EFFECTS)

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


def _app_version() -> str:
    """Return the installed application version."""

    try:
        return version("pokemon-battle-compass")
    except PackageNotFoundError:
        return "0.1.1"


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
        on_journey_loaded: (
            Callable[[], None] | None
        ) = None,
        on_journey_updated: (
            Callable[[], None] | None
        ) = None,
        on_scroll_to: (
            Callable[..., Awaitable[None]] | None
        ) = None,
    ) -> None:
        self.page = page
        self.app_state = app_state
        self.on_scroll_to = on_scroll_to
        self.team_data = app_state.team_data
        self.box_data = app_state.box_data
        self.moves_data = moves_data
        self.items_data = app_state.reference_data["items"]
        self.type_chart = cast(
            dict,
            app_state.reference_data["type_chart"],
        )
        self.evolutions = cast(
            dict[str, dict],
            app_state.reference_data.get(
                "evolutions",
                {},
            ),
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

        self.on_team_updated = on_team_updated
        self.on_journey_loaded = on_journey_loaded
        self.on_journey_updated = on_journey_updated
        self.pending_import_journey: dict | None = None


        self.move_lookup = {
            move["Move"]: move
            for move in moves_data
            if isinstance(move.get("Move"), str)
            and move["Move"]
        }
        self.move_options = sorted(self.move_lookup)
        self.working_team = deepcopy(self.team_data)
        self.saved_team_snapshot = deepcopy(self.team_data)
        self.working_box = deepcopy(self.box_data)
        self.saved_box_snapshot = deepcopy(self.box_data)

        self.editor_controls: dict[
            tuple[int, str],
            ft.TextField | ft.Dropdown | ft.AutoComplete,
        ] = {}
        self._active_numeric_field: tuple[int, str] | None = None
        self._previous_keyboard_handler = None

        self._autocomplete_edit_versions: dict[
            tuple[int, str],
            int,
        ] = {}

        self.selected_index = 0
        self.selected_source = "party"
        self.party_management_selected_index: int | None = None
        self.pending_party_action: str | None = None
        self.pending_box_index: int | None = None
        self.pending_swap_party_index: int | None = None
        self._recommendation_target_source: str | None = None
        self._recommendation_target_index: int | None = None
        self._pending_recommended_item: str | None = None

        try:
            raw_journey_items = json.loads(
                (DATA_DIR / "journey_items.json").read_text(
                    encoding="utf-8"
                )
            )
        except (OSError, UnicodeError, json.JSONDecodeError):
            raw_journey_items = []

        self.journey_item_by_name = {
            self._normalize_item_name(
                str(item.get("name", ""))
            ): item
            for item in raw_journey_items
            if isinstance(item, dict)
            and str(item.get("name", "")).strip()
            and str(item.get("id", "")).strip()
        }

        try:
            raw_journey_pokemon = json.loads(
                (DATA_DIR / "journey_pokemon.json").read_text(
                    encoding="utf-8"
                )
            )
        except (OSError, UnicodeError, json.JSONDecodeError):
            raw_journey_pokemon = []

        self.pokemon_type_lookup: dict[str, tuple[str, str]] = {}
        for family in raw_journey_pokemon:
            if not isinstance(family, dict):
                continue
            stage_types = family.get("types", {})
            if not isinstance(stage_types, dict):
                continue
            for pokemon_name, pokemon_types in stage_types.items():
                if (
                    not isinstance(pokemon_name, str)
                    or not isinstance(pokemon_types, list)
                    or not pokemon_types
                ):
                    continue
                type1 = str(pokemon_types[0] or "").strip()
                type2 = (
                    str(pokemon_types[1] or "").strip()
                    if len(pokemon_types) > 1
                    else ""
                )
                if type1:
                    self.pokemon_type_lookup[pokemon_name.strip()] = (
                        type1,
                        type2,
                    )

        self.box_table_host = ft.Container()
        self.move_to_party_button: ft.Button | None = None
        self.release_boxed_button: ft.Button | None = None

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
        self.detail_notice = ft.Container(
            content=ft.Column(
                controls=cast(
                    list[ft.Control],
                    [
                        ft.Text(
                            "Unsaved team changes",
                            size=15,
                            weight=ft.FontWeight.BOLD,
                            color="#FFE5A3",
                        ),
                        ft.Text(
                            (
                                "Pokémon Details and Battle Compass will "
                                "update after you save."
                            ),
                            size=13,
                            color=TEXT_SECONDARY,
                        ),
                    ],
                ),
                spacing=3,
                tight=True,
            ),
            padding=12,
            bgcolor="#3B3017",
            border_radius=10,
            visible=False,
        )
        self.save_status = ft.Text(
            "",
            size=14,
            color=SUCCESS,
        )

        self.add_pokemon_button = ft.Button(
            content="Add Pokémon",
            icon=ft.Icons.ADD_ROUNDED,
            disabled=len(self.working_team) >= 6,
            on_click=self._add_pokemon,
            style=ft.ButtonStyle(
                bgcolor={
                    ft.ControlState.DEFAULT: ADD_BUTTON_ACTIVE,
                    ft.ControlState.DISABLED: ADD_BUTTON_DISABLED,
                },
                color={
                    ft.ControlState.DEFAULT: TEXT_PRIMARY,
                    ft.ControlState.DISABLED: BUTTON_DISABLED_TEXT,
                },
                icon_color={
                    ft.ControlState.DEFAULT: TEXT_PRIMARY,
                    ft.ControlState.DISABLED: BUTTON_DISABLED_TEXT,
                },
                elevation={
                    ft.ControlState.DEFAULT: 1,
                    ft.ControlState.DISABLED: 0,
                },
            ),
        )

        self.manage_party_button = ft.Button(
            content="Box / Release Pokémon",
            icon=ft.Icons.ARCHIVE_OUTLINED,
            disabled=not self.working_team,
            on_click=self._show_party_management_dialog,
            style=ft.ButtonStyle(
                bgcolor={
                    ft.ControlState.DEFAULT: MANAGE_BUTTON_ACTIVE,
                    ft.ControlState.DISABLED: MANAGE_BUTTON_DISABLED,
                },
                color={
                    ft.ControlState.DEFAULT: TEXT_PRIMARY,
                    ft.ControlState.DISABLED: BUTTON_DISABLED_TEXT,
                },
                icon_color={
                    ft.ControlState.DEFAULT: TEXT_PRIMARY,
                    ft.ControlState.DISABLED: BUTTON_DISABLED_TEXT,
                },
                elevation={
                    ft.ControlState.DEFAULT: 1,
                    ft.ControlState.DISABLED: 0,
                },
            ),
        )

        self.save_button = ft.Button(
            content="Save Team",
            icon=ft.Icons.SAVE_OUTLINED,
            disabled=True,
            on_click=self._save_team,
            style=ft.ButtonStyle(
                bgcolor={
                    ft.ControlState.DEFAULT: SAVE_BUTTON_ACTIVE,
                    ft.ControlState.DISABLED: SAVE_BUTTON_DISABLED,
                },
                color={
                    ft.ControlState.DEFAULT: TEXT_PRIMARY,
                    ft.ControlState.DISABLED: BUTTON_DISABLED_TEXT,
                },
                icon_color={
                    ft.ControlState.DEFAULT: TEXT_PRIMARY,
                    ft.ControlState.DISABLED: BUTTON_DISABLED_TEXT,
                },
                elevation={
                    ft.ControlState.DEFAULT: 1,
                    ft.ControlState.DISABLED: 0,
                },
            ),
        )

        self.discard_button = ft.Button(
            content="Discard Changes",
            icon=ft.Icons.UNDO_ROUNDED,
            disabled=True,
            on_click=self._discard_changes,
            style=ft.ButtonStyle(
                bgcolor={
                    ft.ControlState.DEFAULT: DISCARD_BUTTON_ACTIVE,
                    ft.ControlState.DISABLED: DISCARD_BUTTON_DISABLED,
                },
                color={
                    ft.ControlState.DEFAULT: TEXT_PRIMARY,
                    ft.ControlState.DISABLED: BUTTON_DISABLED_TEXT,
                },
                icon_color={
                    ft.ControlState.DEFAULT: TEXT_PRIMARY,
                    ft.ControlState.DISABLED: BUTTON_DISABLED_TEXT,
                },
                elevation={
                    ft.ControlState.DEFAULT: 1,
                    ft.ControlState.DISABLED: 0,
                },
            ),
        )

        self.export_button = ft.Button(
            content="Export Journey",
            icon=ft.Icons.DOWNLOAD_OUTLINED,
            disabled=False,
            on_click=self._export_journey,
            style=ft.ButtonStyle(
                bgcolor={
                    ft.ControlState.DEFAULT: EXPORT_BUTTON_ACTIVE,
                    ft.ControlState.DISABLED: EXPORT_BUTTON_DISABLED,
                },
                color={
                    ft.ControlState.DEFAULT: TEXT_PRIMARY,
                    ft.ControlState.DISABLED: BUTTON_DISABLED_TEXT,
                },
                icon_color={
                    ft.ControlState.DEFAULT: TEXT_PRIMARY,
                    ft.ControlState.DISABLED: BUTTON_DISABLED_TEXT,
                },
                elevation={
                    ft.ControlState.DEFAULT: 1,
                    ft.ControlState.DISABLED: 0,
                },
            ),
        )

        self.load_button = ft.Button(
            content="Load Journey",
            icon=ft.Icons.UPLOAD_FILE_OUTLINED,
            disabled=False,
            on_click=self._select_journey_file,
            style=ft.ButtonStyle(
                bgcolor={
                    ft.ControlState.DEFAULT: LOAD_BUTTON_ACTIVE,
                    ft.ControlState.DISABLED: LOAD_BUTTON_DISABLED,
                },
                color={
                    ft.ControlState.DEFAULT: TEXT_PRIMARY,
                    ft.ControlState.DISABLED: BUTTON_DISABLED_TEXT,
                },
                icon_color={
                    ft.ControlState.DEFAULT: TEXT_PRIMARY,
                    ft.ControlState.DISABLED: BUTTON_DISABLED_TEXT,
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
        self.box_table_host.content = self._build_box_table()

        self._refresh_selector()
        self._refresh_detail()

    @property
    def has_unsaved_changes(self) -> bool:
        """Return whether the working editor differs from the saved team."""

        return (
            self.working_team != self.saved_team_snapshot
            or self.working_box != self.saved_box_snapshot
        )

    def discard_unsaved_changes(self) -> None:
        """Restore the editor to the most recently saved team and Box."""

        self.working_team = deepcopy(
            self.saved_team_snapshot
        )
        self.working_box = deepcopy(
            self.saved_box_snapshot
        )

        self.pending_party_action = None
        self.pending_box_index = None
        self.pending_swap_party_index = None
        self.party_management_selected_index = None

        self.editor_controls.clear()
        self._autocomplete_edit_versions.clear()

        self.table_host.content = (
            self._build_editor_table()
        )
        self.box_table_host.content = self._build_box_table()

        self.save_status.value = "Team is up to date."
        self.save_status.color = SUCCESS
        self.save_button.disabled = True
        self.discard_button.disabled = True
        self.export_button.disabled = False
        self.detail_notice.visible = False

        self._refresh_selector()
        self._refresh_detail()
        self._sync_team_management_buttons()
        self._sync_box_buttons()
        self.page.update()

    def _discard_changes(
        self,
        event: ft.Event[ft.Button],
    ) -> None:
        """Discard all unsaved Team Editor and Box changes."""

        del event
        self.discard_unsaved_changes()

    def _apply_known_pokemon_types(
        self,
        record: dict,
        pokemon_name: str,
    ) -> bool:
        """Populate Type1/Type2 when the selected Pokémon is known."""

        known_types = self.pokemon_type_lookup.get(
            pokemon_name.strip()
        )
        if known_types is None:
            return False

        record["Type1"] = known_types[0]
        record["Type2"] = known_types[1]
        return True

    def begin_prefilled_pokemon_entry(
        self,
        pokemon_name: str,
    ) -> None:
        """Open a new Team Editor row with the Pokémon name pre-populated."""

        normalized_name = pokemon_name.strip()
        if not normalized_name:
            return

        if len(self.working_team) < 6:
            record = self._blank_pokemon_record()
            record["Pokemon"] = normalized_name
            self._apply_known_pokemon_types(
                record,
                normalized_name,
            )
            self.working_team.append(record)
            self._refresh_after_prefilled_entry()
            return

        controls: list[ft.Control] = [
            ft.Text(
                (
                    f"Your active party is full. Choose a party Pokémon to "
                    f"move to My Box so {normalized_name} can be added to "
                    "the Team Editor."
                ),
                color=TEXT_SECONDARY,
            )
        ]

        for index, pokemon in enumerate(self.working_team):
            party_name = str(
                pokemon.get("Pokemon")
                or f"Team Slot {index + 1}"
            )
            controls.append(
                ft.Button(
                    content=(
                        f"{party_name} · "
                        f"Lv. {pokemon.get('Level', '—')}"
                    ),
                    on_click=(
                        lambda event, party_index=index, name=normalized_name:
                        self._prefill_after_boxing_party_member(
                            event,
                            party_index,
                            name,
                        )
                    ),
                )
            )

        dialog = ft.AlertDialog()
        dialog.modal = True
        dialog.title = ft.Text(
            "Choose a Party Pokémon",
            weight=ft.FontWeight.BOLD,
        )
        dialog.content = ft.Column(
            controls=controls,
            spacing=10,
            tight=True,
        )
        dialog.actions = [
            ft.Button(
                content="Cancel",
                on_click=lambda: self.page.pop_dialog(),
            )
        ]
        dialog.actions_alignment = ft.MainAxisAlignment.END
        self.page.show_dialog(dialog)

    def _prefill_after_boxing_party_member(
        self,
        event: ft.Event[ft.Button],
        party_index: int,
        pokemon_name: str,
    ) -> None:
        """Box one party member and add a prefilled editor row."""

        del event

        if party_index < 0 or party_index >= len(self.working_team):
            return

        outgoing = self.working_team[party_index]
        record = self._blank_pokemon_record()
        record["Pokemon"] = pokemon_name
        self._apply_known_pokemon_types(
            record,
            pokemon_name,
        )

        self.working_team[party_index] = record
        self.working_box.append(outgoing)

        self.page.pop_dialog()
        self._refresh_after_prefilled_entry()

    def _refresh_after_prefilled_entry(self) -> None:
        """Refresh the Team Editor after creating a prefilled row."""

        self.editor_controls.clear()
        self._autocomplete_edit_versions.clear()
        self.table_host.content = self._build_editor_table()
        self.box_table_host.content = self._build_box_table()
        self._update_dirty_state()
        self._sync_team_management_buttons()
        self._sync_box_buttons()
        self._refresh_selector()
        self._refresh_detail()
        self.page.update()
        self.page.run_task(self._scroll_to_team_editor)

    async def _scroll_to_team_editor(
        self,
        *,
        offset: float = 0,
        delay: float = 0.10,
    ) -> None:
        """Place the Team Editor in view using the AppShell scroll host."""

        if self.on_scroll_to is None:
            return

        # Give AppShell one frame to finish any view/dialog transition before
        # moving the shell-owned scroll host.
        await asyncio.sleep(delay)
        await self.on_scroll_to(
            offset=offset,
            duration=360,
            curve=ft.AnimationCurve.EASE_OUT_CUBIC,
        )

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

        self.editor_controls.clear()
        self._autocomplete_edit_versions.clear()

        self.table_host.content = (
            self._build_editor_table()
        )
        self.box_table_host.content = self._build_box_table()

        self._update_dirty_state()
        self._sync_team_management_buttons()

        self.page.update()

    @staticmethod
    def _blank_pokemon_record() -> dict:
        """Return a new editable Pokémon team record."""

        return {
            "Pokemon": "",
            "Gender": "",
            "Nature": "",
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
                    width=560,
                    height=690,
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
            scroll=ft.ScrollMode.AUTO,
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

        self.pending_party_action = action

        if action == "box":
            title = f"Box {pokemon_name}?"
            message = (
                f"{pokemon_name} will move from your active party "
                "to My Box when you save the team."
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

        pokemon = self.working_team.pop(selected_index)
        if self.pending_party_action == "box":
            self.working_box.append(pokemon)

        self.pending_party_action = None
        self.party_management_selected_index = None
        self.editor_controls.clear()
        self._autocomplete_edit_versions.clear()

        self.table_host.content = (
            self._build_editor_table()
        )

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
        self.pending_party_action = None
        self.page.pop_dialog()
        self.page.update()

    def _close_party_management_dialog(
        self,
        event: ft.Event[ft.Button],
    ) -> None:
        """Close the party-management dialog."""

        del event

        self.party_management_selected_index = None
        self.pending_party_action = None
        self.page.pop_dialog()
        self.page.update()

    def _update_dirty_state(self) -> None:
        """Synchronize controls with the current dirty state."""

        is_dirty = self.has_unsaved_changes

        self.save_button.disabled = not is_dirty
        self.discard_button.disabled = not is_dirty
        self.export_button.disabled = is_dirty
        self.detail_notice.visible = is_dirty
        self._sync_box_buttons()

        if is_dirty:
            self.save_status.value = "Unsaved changes"
            self.save_status.color = "#FFE5A3"
        else:
            self.save_status.value = "Team is up to date."
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
                            size=TEXT_SIZE_FEATURED_TITLE,
                            weight=ft.FontWeight.BOLD,
                            font_family=FONT_FAMILY_HEADER,
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
                            size=TEXT_SIZE_BODY,
                            color=TEXT_SECONDARY,
                        ),
                        ft.Text(
                            "Swipe left or right to view more columns.",
                            size=TEXT_SIZE_CAPTION,
                            color=TEXT_MUTED,
                            italic=True,
                        ),
                        self.table_host,
                        ft.Row(
                            controls=cast(
                                list[ft.Control],
                                [
                                    self.add_pokemon_button,
                                    self.manage_party_button,
                                    self.save_button,
                                    self.discard_button,
                                    self.export_button,
                                    self.load_button,
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
                            size=TEXT_SIZE_DETAIL,
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
                            size=TEXT_SIZE_FEATURED_TITLE,
                            weight=ft.FontWeight.BOLD,
                            font_family=FONT_FAMILY_HEADER,
                            color=TEXT_PRIMARY,
                        ),
                        self.detail_notice,
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

        box_card = self._build_box_card()

        return ft.Column(
            controls=cast(
                list[ft.Control],
                [
                    editor_card,
                    details_card,
                    box_card,
                ],
            ),
            spacing=24,
            horizontal_alignment=ft.CrossAxisAlignment.CENTER,
        )

    def _build_box_card(self) -> ft.Control:
        self.move_to_party_button = ft.Button(
            content="Move to Party",
            icon=ft.Icons.SWAP_HORIZ_ROUNDED,
            on_click=self._request_move_boxed_to_party,
        )
        self.release_boxed_button = ft.Button(
            content="Release",
            icon=ft.Icons.DELETE_OUTLINE_ROUNDED,
            color="#FCA5A5",
            icon_color="#FCA5A5",
            on_click=self._request_release_boxed,
        )
        self._sync_box_buttons()

        return ft.Container(
            content=ft.Column(
                controls=cast(
                    list[ft.Control],
                    [
                        ft.Text(
                            "My Box",
                            size=TEXT_SIZE_FEATURED_TITLE,
                            weight=ft.FontWeight.BOLD,
                            font_family=FONT_FAMILY_HEADER,
                            color=TEXT_PRIMARY,
                        ),
                        ft.Text(
                            (
                                "Boxed Pokémon remain part of your Journey. "
                                "Use the controls below to move or release one; "
                                "use Pokémon Details only when you want to inspect it."
                            ),
                            size=TEXT_SIZE_BODY,
                            color=TEXT_SECONDARY,
                        ),
                        self.box_table_host,
                        ft.Row(
                            controls=cast(
                                list[ft.Control],
                                [
                                    self.move_to_party_button,
                                    self.release_boxed_button,
                                ],
                            ),
                            spacing=14,
                            wrap=True,
                        ),
                    ],
                ),
                spacing=16,
            ),
            width=940,
            padding=CARD_PADDING,
            bgcolor=SURFACE,
            border=ft.Border.all(1, BORDER_DEFAULT),
            border_radius=CARD_RADIUS,
        )

    def _build_box_table(self) -> ft.Control:
        if not self.working_box:
            return ft.Container(
                content=ft.Text(
                    "No Pokémon are currently boxed.",
                    color=TEXT_MUTED,
                    italic=True,
                ),
                padding=16,
                bgcolor=SURFACE_RAISED,
                border_radius=12,
            )

        rows: list[ft.DataRow] = []
        for pokemon in self.working_box:
            pokemon_name = str(pokemon.get("Pokemon") or "Unknown")
            sprite_path = get_sprite_path(
                pokemon_name,
                gender=pokemon.get("Gender"),
                use_texture=False,
            )
            if sprite_path is None:
                sprite: ft.Control = ft.Icon(
                    ft.Icons.HELP_OUTLINE_ROUNDED,
                    size=34,
                    color=TEXT_MUTED,
                )
            else:
                sprite = ft.Image(
                    src=self._asset_src(sprite_path),
                    width=48,
                    height=48,
                    fit=ft.BoxFit.CONTAIN,
                    semantics_label=pokemon_name,
                )
            rows.append(
                ft.DataRow(
                    cells=[
                        ft.DataCell(sprite),
                        ft.DataCell(
                            ft.Text(
                                pokemon_name,
                                color=TEXT_PRIMARY,
                                weight=ft.FontWeight.W_600,
                            )
                        ),
                        ft.DataCell(
                            ft.Text(
                                str(pokemon.get("Level", "—")),
                                color=TEXT_SECONDARY,
                            )
                        ),
                    ]
                )
            )

        table = ft.DataTable(
            columns=[
                ft.DataColumn(label=ft.Text("", weight=ft.FontWeight.BOLD)),
                ft.DataColumn(label=ft.Text("Pokémon", weight=ft.FontWeight.BOLD)),
                ft.DataColumn(label=ft.Text("Level", weight=ft.FontWeight.BOLD)),
            ],
            rows=rows,
            border=ft.Border.all(1, BORDER_DEFAULT),
            border_radius=12,
            heading_row_color=SURFACE_RAISED,
            column_spacing=24,
            data_row_min_height=58,
            data_row_max_height=58,
        )
        return ft.Row(controls=cast(list[ft.Control], [table]))

    def _sync_box_buttons(self) -> None:
        """Enable Box controls whenever at least one Pokémon is boxed."""

        has_boxed_pokemon = bool(self.working_box)

        if self.move_to_party_button is not None:
            self.move_to_party_button.disabled = not has_boxed_pokemon

        if self.release_boxed_button is not None:
            self.release_boxed_button.disabled = not has_boxed_pokemon

    def _request_move_boxed_to_party(self) -> None:
        """Ask which boxed Pokémon should move to the active party."""

        if not self.working_box:
            return

        self.pending_box_index = None
        self.pending_swap_party_index = None

        controls: list[ft.Control] = [
            ft.Text(
                "Choose the boxed Pokémon you want to move to the active party.",
                color=TEXT_SECONDARY,
            )
        ]

        for index, pokemon in enumerate(self.working_box):
            pokemon_name = str(
                pokemon.get("Pokemon")
                or f"Box Slot {index + 1}"
            )
            controls.append(
                ft.Button(
                    content=(
                        f"{pokemon_name} · "
                        f"Lv. {pokemon.get('Level', '—')}"
                    ),
                    on_click=(
                        lambda event, box_index=index:
                        self._select_boxed_for_party(
                            event,
                            box_index,
                        )
                    ),
                )
            )

        dialog = ft.AlertDialog()
        dialog.modal = True
        dialog.title = ft.Text(
            "Move to Party",
            weight=ft.FontWeight.BOLD,
        )
        dialog.content = ft.Column(
            controls=controls,
            spacing=10,
            tight=True,
        )
        dialog.actions = [
            ft.Button(
                content="Cancel",
                on_click=self._cancel_box_action,
            )
        ]
        dialog.actions_alignment = ft.MainAxisAlignment.END
        self.page.show_dialog(dialog)

    def _select_boxed_for_party(
        self,
        event: ft.Event[ft.Button],
        box_index: int,
    ) -> None:
        """Continue the move flow after a boxed Pokémon is chosen."""

        del event

        if box_index < 0 or box_index >= len(self.working_box):
            return

        self.pending_box_index = box_index
        self.page.pop_dialog()

        if len(self.working_team) < 6:
            self._show_open_slot_move_confirmation()
            return

        self._show_party_swap_selection()

    def _show_open_slot_move_confirmation(self) -> None:
        """Confirm moving a boxed Pokémon into an open party slot."""

        if self.pending_box_index is None:
            return

        pokemon_name = str(
            self.working_box[self.pending_box_index].get("Pokemon")
            or "this Pokémon"
        )

        dialog = ft.AlertDialog()
        dialog.modal = True
        dialog.title = ft.Text(
            f"Move {pokemon_name} to the party?",
            weight=ft.FontWeight.BOLD,
        )
        dialog.content = ft.Text(
            (
                f"{pokemon_name} will move from My Box to the active party "
                "when you save the team."
            ),
            color=TEXT_SECONDARY,
        )
        dialog.actions = [
            ft.Button(
                content="Cancel",
                on_click=self._cancel_box_action,
            ),
            ft.Button(
                content="Move to Party",
                icon=ft.Icons.SWAP_HORIZ_ROUNDED,
                bgcolor=PRIMARY_BLUE,
                color=TEXT_PRIMARY,
                icon_color=TEXT_PRIMARY,
                on_click=self._confirm_move_to_open_slot,
            ),
        ]
        dialog.actions_alignment = ft.MainAxisAlignment.END
        self.page.show_dialog(dialog)

    def _confirm_move_to_open_slot(
        self,
        event: ft.Event[ft.Button],
    ) -> None:
        """Move the chosen boxed Pokémon into the working party."""

        del event

        if self.pending_box_index is None:
            self.page.pop_dialog()
            return

        if (
            self.pending_box_index < 0
            or self.pending_box_index >= len(self.working_box)
            or len(self.working_team) >= 6
        ):
            self._cancel_box_action()
            return

        pokemon = self.working_box.pop(self.pending_box_index)
        self.working_team.append(pokemon)

        self.pending_box_index = None
        self.pending_swap_party_index = None
        self.page.pop_dialog()
        self._refresh_after_box_action()

    def _show_party_swap_selection(self) -> None:
        """Ask which party Pokémon should be boxed during a full-party swap."""

        if self.pending_box_index is None:
            return

        incoming_name = str(
            self.working_box[self.pending_box_index].get("Pokemon")
            or "this Pokémon"
        )

        controls: list[ft.Control] = [
            ft.Text(
                (
                    f"Your party is full. Choose the party Pokémon that should "
                    f"move to My Box so {incoming_name} can join."
                ),
                color=TEXT_SECONDARY,
            )
        ]

        for index, pokemon in enumerate(self.working_team):
            pokemon_name = str(
                pokemon.get("Pokemon")
                or f"Team Slot {index + 1}"
            )
            controls.append(
                ft.Button(
                    content=(
                        f"{pokemon_name} · "
                        f"Lv. {pokemon.get('Level', '—')}"
                    ),
                    on_click=(
                        lambda event, party_index=index:
                        self._select_party_swap_target(
                            event,
                            party_index,
                        )
                    ),
                )
            )

        dialog = ft.AlertDialog()
        dialog.modal = True
        dialog.title = ft.Text(
            "Choose a party Pokémon",
            weight=ft.FontWeight.BOLD,
        )
        dialog.content = ft.Column(
            controls=controls,
            spacing=10,
            tight=True,
        )
        dialog.actions = [
            ft.Button(
                content="Cancel",
                on_click=self._cancel_box_action,
            )
        ]
        dialog.actions_alignment = ft.MainAxisAlignment.END
        self.page.show_dialog(dialog)

    def _select_party_swap_target(
        self,
        event: ft.Event[ft.Button],
        party_index: int,
    ) -> None:
        """Show a final confirmation for a Box/party swap."""

        del event

        if (
            self.pending_box_index is None
            or party_index < 0
            or party_index >= len(self.working_team)
        ):
            return

        self.pending_swap_party_index = party_index
        self.page.pop_dialog()

        incoming_name = str(
            self.working_box[self.pending_box_index].get("Pokemon")
            or "the boxed Pokémon"
        )
        outgoing_name = str(
            self.working_team[party_index].get("Pokemon")
            or "the party Pokémon"
        )

        dialog = ft.AlertDialog()
        dialog.modal = True
        dialog.title = ft.Text(
            f"Swap {incoming_name} and {outgoing_name}?",
            weight=ft.FontWeight.BOLD,
        )
        dialog.content = ft.Text(
            (
                f"{incoming_name} will join the active party and "
                f"{outgoing_name} will move to My Box when you save the team."
            ),
            color=TEXT_SECONDARY,
        )
        dialog.actions = [
            ft.Button(
                content="Cancel",
                on_click=self._cancel_box_action,
            ),
            ft.Button(
                content="Confirm Swap",
                icon=ft.Icons.SWAP_HORIZ_ROUNDED,
                bgcolor=PRIMARY_BLUE,
                color=TEXT_PRIMARY,
                icon_color=TEXT_PRIMARY,
                on_click=self._confirm_box_party_swap,
            ),
        ]
        dialog.actions_alignment = ft.MainAxisAlignment.END
        self.page.show_dialog(dialog)

    def _confirm_box_party_swap(
        self,
        event: ft.Event[ft.Button],
    ) -> None:
        """Apply the confirmed Box/party swap to the working state."""

        del event

        if (
            self.pending_box_index is None
            or self.pending_swap_party_index is None
            or self.pending_box_index < 0
            or self.pending_box_index >= len(self.working_box)
            or self.pending_swap_party_index < 0
            or self.pending_swap_party_index >= len(self.working_team)
        ):
            self._cancel_box_action()
            return

        incoming = self.working_box[self.pending_box_index]
        outgoing = self.working_team[self.pending_swap_party_index]

        self.working_team[self.pending_swap_party_index] = incoming
        self.working_box[self.pending_box_index] = outgoing

        self.pending_box_index = None
        self.pending_swap_party_index = None
        self.page.pop_dialog()
        self._refresh_after_box_action()

    def _request_release_boxed(self) -> None:
        """Ask which boxed Pokémon should be released."""

        if not self.working_box:
            return

        self.pending_box_index = None
        self.pending_swap_party_index = None

        controls: list[ft.Control] = [
            ft.Text(
                "Choose the boxed Pokémon you want to release.",
                color=TEXT_SECONDARY,
            )
        ]

        for index, pokemon in enumerate(self.working_box):
            pokemon_name = str(
                pokemon.get("Pokemon")
                or f"Box Slot {index + 1}"
            )
            controls.append(
                ft.Button(
                    content=(
                        f"{pokemon_name} · "
                        f"Lv. {pokemon.get('Level', '—')}"
                    ),
                    on_click=(
                        lambda event, box_index=index:
                        self._select_boxed_for_release(
                            event,
                            box_index,
                        )
                    ),
                )
            )

        dialog = ft.AlertDialog()
        dialog.modal = True
        dialog.title = ft.Text(
            "Release a Boxed Pokémon",
            weight=ft.FontWeight.BOLD,
        )
        dialog.content = ft.Column(
            controls=controls,
            spacing=10,
            tight=True,
        )
        dialog.actions = [
            ft.Button(
                content="Cancel",
                on_click=self._cancel_box_action,
            )
        ]
        dialog.actions_alignment = ft.MainAxisAlignment.END
        self.page.show_dialog(dialog)

    def _select_boxed_for_release(
        self,
        event: ft.Event[ft.Button],
        box_index: int,
    ) -> None:
        """Confirm release after a boxed Pokémon is chosen."""

        del event

        if box_index < 0 or box_index >= len(self.working_box):
            return

        self.pending_box_index = box_index
        self.page.pop_dialog()

        pokemon_name = str(
            self.working_box[box_index].get("Pokemon")
            or "this Pokémon"
        )

        dialog = ft.AlertDialog()
        dialog.modal = True
        dialog.title = ft.Text(
            f"Release {pokemon_name}?",
            weight=ft.FontWeight.BOLD,
        )
        dialog.content = ft.Text(
            (
                f"This removes {pokemon_name} from the current Journey when "
                "you save the team. This cannot be undone after saving."
            ),
            color=TEXT_SECONDARY,
        )
        dialog.actions = [
            ft.Button(
                content="Cancel",
                on_click=self._cancel_box_action,
            ),
            ft.Button(
                content="Release",
                icon=ft.Icons.DELETE_OUTLINE_ROUNDED,
                bgcolor="#B94A55",
                color=TEXT_PRIMARY,
                icon_color=TEXT_PRIMARY,
                on_click=self._confirm_release_boxed,
            ),
        ]
        dialog.actions_alignment = ft.MainAxisAlignment.END
        self.page.show_dialog(dialog)

    def _confirm_release_boxed(
        self,
        event: ft.Event[ft.Button],
    ) -> None:
        """Remove the confirmed Pokémon from the working Box."""

        del event

        if (
            self.pending_box_index is None
            or self.pending_box_index < 0
            or self.pending_box_index >= len(self.working_box)
        ):
            self._cancel_box_action()
            return

        self.working_box.pop(self.pending_box_index)
        self.pending_box_index = None
        self.pending_swap_party_index = None
        self.page.pop_dialog()
        self._refresh_after_box_action()

    def _cancel_box_action(
        self,
        event: ft.Event[ft.Button] | None = None,
    ) -> None:
        """Cancel any pending Box move, swap, or release action."""

        del event
        self.pending_box_index = None
        self.pending_swap_party_index = None
        self.page.pop_dialog()
        self.page.update()

    def _refresh_after_box_action(self) -> None:
        """Refresh the working party and Box after a confirmed action."""

        self.editor_controls.clear()
        self._autocomplete_edit_versions.clear()
        self.table_host.content = self._build_editor_table()
        self.box_table_host.content = self._build_box_table()
        self._update_dirty_state()
        self._sync_team_management_buttons()
        self._sync_box_buttons()
        self._refresh_selector()
        self._refresh_detail()
        self.page.update()

    def _close_simple_dialog(self) -> None:
        self.page.pop_dialog()
        self.page.update()

    async def _persist_team_and_box_change(
        self,
        team: list[dict],
        box: list[dict],
        *,
        selected_source: str,
        selected_index: int,
    ) -> None:
        try:
            succeeded = await self.app_state.save_team_and_box(team, box)
        except (RuntimeError, ValueError) as error:
            self.save_status.value = f"Pokémon could not be moved: {error}"
            self.save_status.color = "#F87171"
            self.page.update()
            return
        if not succeeded:
            self.save_status.value = "Pokémon could not be moved."
            self.save_status.color = "#F87171"
            self.page.update()
            return

        self.team_data = self.app_state.team_data
        self.box_data = self.app_state.box_data
        self.working_team = deepcopy(self.team_data)
        self.saved_team_snapshot = deepcopy(self.team_data)
        self.working_box = deepcopy(self.box_data)
        self.saved_box_snapshot = deepcopy(self.box_data)
        self.selected_source = selected_source
        self.selected_index = selected_index
        self.editor_controls.clear()
        self._autocomplete_edit_versions.clear()
        self.table_host.content = self._build_editor_table()
        self.box_table_host.content = self._build_box_table()
        self._refresh_selector()
        self._refresh_detail()
        self._sync_team_management_buttons()
        self.save_status.value = "Party and Box are up to date."
        self.save_status.color = SUCCESS
        if self.on_team_updated:
            self.on_team_updated(self.app_state.team_data)
        self.page.update()

    def _autocomplete_options_for_column(
        self,
        column: str,
    ) -> list[str]:
        """Return the validation catalog used by one autocomplete column."""

        if column == "Pokemon":
            return self.pokemon_options
        if column in {"Type1", "Type2"}:
            return self.type_options
        if column == "Ability":
            return self.ability_options
        if column == "Held Item":
            return self.item_options
        if column.startswith("Move"):
            return self.move_options
        return []

    def _filtered_autocomplete_suggestions(
        self,
        column: str,
        query: str,
    ) -> list[ft.AutoCompleteSuggestion]:
        """Build a small suggestion list instead of attaching a full catalog."""

        normalized_query = query.strip().casefold()
        if not normalized_query:
            return []

        options = self._autocomplete_options_for_column(column)

        prefix_matches: list[str] = []
        contains_matches: list[str] = []

        for option in options:
            normalized_option = option.casefold()
            if normalized_option.startswith(normalized_query):
                prefix_matches.append(option)
            elif normalized_query in normalized_option:
                contains_matches.append(option)

            if (
                len(prefix_matches) + len(contains_matches)
                >= AUTOCOMPLETE_SUGGESTION_LIMIT * 2
            ):
                break

        matches = (
            prefix_matches + contains_matches
        )[:AUTOCOMPLETE_SUGGESTION_LIMIT]

        return [
            ft.AutoCompleteSuggestion(
                key=option,
                value=option,
            )
            for option in matches
        ]

    def _refresh_autocomplete_suggestions(
        self,
        control: ft.AutoComplete,
        column: str,
        query: str,
    ) -> None:
        """Refresh only the edited autocomplete's compact suggestion list."""

        control.suggestions = self._filtered_autocomplete_suggestions(
            column,
            query,
        )
        control.update()

    def _build_editor_table(self) -> ft.Control:
        """Build the editor as one horizontally scrollable table with Pokémon sticky."""

        column_widths = {
            "Pokemon": 134,
            "Gender": 120,
            "Nature": 130,
            "Type1": 116,
            "Type2": 116,
            "Level": 76,
            "HP": 76,
            "ATK": 76,
            "DEF": 76,
            "SPA": 76,
            "SPD": 76,
            "SPE": 76,
            "Move1": 166,
            "Move2": 166,
            "Move3": 166,
            "Move4": 166,
            "Ability": 166,
            "Held Item": 166,
        }

        table_min_width = sum(
            column_widths[column]
            for column in EDITABLE_COLUMNS
        )

        # DataTable2 owns the horizontal scrolling. Keeping every column in
        # one table means a swipe can begin anywhere on the table while the
        # Pokémon column stays pinned on the left.
        return fdt.DataTable2(
            columns=[
                fdt.DataColumn2(
                    label=ft.Text(
                        DISPLAY_COLUMN_LABELS.get(column, column),
                        size=14,
                        weight=ft.FontWeight.BOLD,
                        color=TEXT_PRIMARY,
                    ),
                    fixed_width=column_widths[column],
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
            fixed_left_columns=1,
            fixed_top_rows=1,
            fixed_columns_color=SURFACE,
            fixed_corner_color=SURFACE_RAISED,
            min_width=table_min_width,
            column_spacing=8,
            horizontal_margin=8,
            data_row_height=58,
            heading_row_height=46,
            border=ft.Border.all(
                1,
                BORDER_DEFAULT,
            ),
            border_radius=12,
            heading_row_color=SURFACE_RAISED,
        )

    def _build_editor_row(
        self,
        row_index: int,
        pokemon: dict,
    ) -> ft.DataRow:
        cells: list[ft.DataCell] = []

        for column in EDITABLE_COLUMNS:
            editor_control = self._build_editor_control(
                row_index=row_index,
                column=column,
                value=pokemon.get(column),
            )

            if column == "Pokemon":
                cell_content: ft.Control = ft.Container(
                    content=editor_control,
                    padding=ft.Padding.only(right=7),
                    border=ft.Border.only(
                        right=ft.BorderSide(
                            1,
                            BORDER_DEFAULT,
                        )
                    ),
                )
            else:
                cell_content = editor_control

            cells.append(
                ft.DataCell(cell_content)
            )

        return ft.DataRow(cells=cells)

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
                suggestions=self._filtered_autocomplete_suggestions(
                    column,
                    str(value) if value else "",
                ),
                suggestions_max_height=240,
                width=134,
                on_change=(
                    lambda event,
                    row=row_index,
                    field=column:
                    self._handle_autocomplete_change(
                        event,
                        row,
                        field,
                    )
                ),
                on_select=(
                    lambda event,
                    row=row_index,
                    field=column:
                    self._handle_autocomplete_select(
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
                width=115,
                text_size=12,
                dense=True,
                on_select=lambda event, row=row_index, field=column: (
                    self._handle_dropdown_change(
                        event,
                        row,
                        field,
                    )
                ),
            )
        elif column == "Nature":
            control = ft.Dropdown(
                value=(
                    str(value)
                    if value in NATURE_EFFECTS
                    else None
                ),
                options=[
                    ft.DropdownOption(
                        key=nature,
                        text=nature,
                    )
                    for nature in NATURE_OPTIONS
                ],
                width=115,
                text_size=12,
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
            control = ft.TextField(
                value=(
                    str(value)
                    if value
                    else ""
                ),
                width=105,
                text_size=12,
                dense=True,
                read_only=True,
            )
        elif column == "Ability":
            control = ft.AutoComplete(
                value=(
                    str(value)
                    if value
                    else ""
                ),
                suggestions=self._filtered_autocomplete_suggestions(
                    column,
                    str(value) if value else "",
                ),
                suggestions_max_height=240,
                width=145,
                on_change=(
                    lambda event,
                    row=row_index,
                    field=column:
                    self._handle_autocomplete_change(
                        event,
                        row,
                        field,
                    )
                ),
                on_select=(
                    lambda event,
                    row=row_index,
                    field=column:
                    self._handle_autocomplete_select(
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
                suggestions=self._filtered_autocomplete_suggestions(
                    column,
                    str(value) if value else "",
                ),
                suggestions_max_height=240,
                width=140,
                on_change=(
                    lambda event,
                    row=row_index,
                    field=column:
                    self._handle_autocomplete_change(
                        event,
                        row,
                        field,
                    )
                ),
                on_select=(
                    lambda event,
                    row=row_index,
                    field=column:
                    self._handle_autocomplete_select(
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
                suggestions=self._filtered_autocomplete_suggestions(
                    column,
                    str(value) if value else "",
                ),
                suggestions_max_height=240,
                width=150,
                on_change=(
                    lambda event,
                    row=row_index,
                    field=column:
                    self._handle_autocomplete_change(
                        event,
                        row,
                        field,
                    )
                ),
                on_select=(
                    lambda event,
                    row=row_index,
                    field=column:
                    self._handle_autocomplete_select(
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
                text_size=12,
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
                ignore_up_down_keys=(
                    column in NUMERIC_FOCUS_ORDER
                ),
                on_focus=(
                    (
                        lambda event, row=row_index, field=column:
                        self._handle_numeric_focus(
                            event,
                            row,
                            field,
                        )
                    )
                    if column in NUMERIC_FOCUS_ORDER
                    else None
                ),
                on_blur=(
                    (
                        lambda event, row=row_index, field=column:
                        self._handle_numeric_blur(
                            event,
                            row,
                            field,
                        )
                    )
                    if column in NUMERIC_FOCUS_ORDER
                    else (
                        lambda event, row=row_index, field=column:
                        self._handle_text_commit(
                            event,
                            row,
                            field,
                        )
                    )
                ),
                on_submit=lambda event, row=row_index, field=column: (
                    self._handle_text_submit(
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

        if column in {"Type1", "Type2", "Nature"}:
            return 100

        if column in NUMERIC_COLUMNS:
            return 64

        if column == "Ability":
            return 145

        if column == "Held Item":
            return 145

        return 120

    def _handle_text_submit(
        self,
        event: ft.Event[ft.TextField],
        row_index: int,
        column: str,
    ) -> None:
        """Commit Enter/Next and advance through the common numeric fields."""

        self._handle_text_commit(
            event,
            row_index,
            column,
        )

        if column in NUMERIC_FOCUS_ORDER:
            self.page.run_task(
                self._focus_next_numeric_field,
                row_index,
                column,
            )

    def _handle_numeric_focus(
        self,
        event: ft.Event[ft.TextField],
        row_index: int,
        column: str,
    ) -> None:
        """Track the focused numeric field and listen for Up/Down keys."""

        del event

        if self._active_numeric_field is None:
            self._previous_keyboard_handler = (
                self.page.on_keyboard_event
            )

        self._active_numeric_field = (
            row_index,
            column,
        )
        self.page.on_keyboard_event = (
            self._handle_numeric_keyboard_event
        )

    def _handle_numeric_blur(
        self,
        event: ft.Event[ft.TextField],
        row_index: int,
        column: str,
    ) -> None:
        """Commit a numeric field and restore the prior keyboard handler."""

        self._handle_text_commit(
            event,
            row_index,
            column,
        )

        if self._active_numeric_field != (
            row_index,
            column,
        ):
            return

        self._active_numeric_field = None
        self.page.on_keyboard_event = (
            self._previous_keyboard_handler
        )
        self._previous_keyboard_handler = None

    def _handle_numeric_keyboard_event(
        self,
        event: ft.KeyboardEvent,
    ) -> None:
        """Use Up/Down keyboard events as Previous/Next numeric-field actions."""

        active_field = self._active_numeric_field
        if active_field is None:
            return

        normalized_key = (
            str(event.key or "")
            .strip()
            .casefold()
            .replace(" ", "")
        )

        if normalized_key in {
            "arrowup",
            "up",
        }:
            offset = -1
        elif normalized_key in {
            "arrowdown",
            "down",
        }:
            offset = 1
        else:
            return

        row_index, column = active_field
        self.page.run_task(
            self._focus_numeric_field_offset,
            row_index,
            column,
            offset,
        )

    async def _focus_next_numeric_field(
        self,
        row_index: int,
        column: str,
    ) -> None:
        """Move focus to the next Level/stat field after Enter/Next."""

        await self._focus_numeric_field_offset(
            row_index,
            column,
            1,
        )

    async def _focus_numeric_field_offset(
        self,
        row_index: int,
        column: str,
        offset: int,
    ) -> None:
        """Move focus through Level/stat fields in row-major order."""

        try:
            column_index = NUMERIC_FOCUS_ORDER.index(
                column
            )
        except ValueError:
            return

        current_position = (
            row_index * len(NUMERIC_FOCUS_ORDER)
            + column_index
        )
        target_position = current_position + offset

        total_positions = (
            len(self.working_team)
            * len(NUMERIC_FOCUS_ORDER)
        )

        if (
            target_position < 0
            or target_position >= total_positions
        ):
            return

        target_row, target_column_index = divmod(
            target_position,
            len(NUMERIC_FOCUS_ORDER),
        )
        target_column = NUMERIC_FOCUS_ORDER[
            target_column_index
        ]

        target_control = self.editor_controls.get(
            (
                target_row,
                target_column,
            )
        )

        if isinstance(target_control, ft.TextField):
            await target_control.focus()

    def _handle_text_commit(
        self,
        event: ft.Event[ft.TextField],
        row_index: int,
        column: str,
    ) -> None:
        """Commit a text field after Enter or loss of focus."""

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

        self._commit_editor_value(
            row_index=row_index,
            column=column,
            value=value,
        )

    def _handle_autocomplete_change(
        self,
        event: ft.Event[ft.AutoComplete],
        row_index: int,
        column: str,
    ) -> None:
        """Schedule a commit after the user pauses typing."""

        key = (row_index, column)
        version = self._autocomplete_edit_versions.get(
            key,
            0,
        ) + 1
        self._autocomplete_edit_versions[key] = version

        pending_value = (
            event.control.value or ""
        ).strip()

        self._refresh_autocomplete_suggestions(
            event.control,
            column,
            pending_value,
        )

        self.page.run_task(
            self._commit_autocomplete_after_delay,
            row_index,
            column,
            pending_value,
            version,
            event.control,
        )

    def _handle_autocomplete_select(
        self,
        event: ft.AutoCompleteSelectEvent,
        row_index: int,
        column: str,
    ) -> None:
        """Commit a selected suggestion immediately."""

        key = (row_index, column)
        self._autocomplete_edit_versions[key] = (
            self._autocomplete_edit_versions.get(
                key,
                0,
            ) + 1
        )

        selected_value = (
            event.control.value or ""
        ).strip()

        self._commit_editor_value(
            row_index=row_index,
            column=column,
            value=selected_value,
        )

    async def _commit_autocomplete_after_delay(
        self,
        row_index: int,
        column: str,
        pending_value: str,
        version: int,
        control: ft.AutoComplete,
    ) -> None:
        """Commit only the latest edit after a brief typing pause."""

        await asyncio.sleep(
            AUTOCOMPLETE_DEBOUNCE_SECONDS
        )

        key = (row_index, column)

        if self._autocomplete_edit_versions.get(key) != version:
            return

        if self.editor_controls.get(key) is not control:
            return

        current_value = (
            control.value or ""
        ).strip()

        if current_value != pending_value:
            return

        self._commit_editor_value(
            row_index=row_index,
            column=column,
            value=pending_value,
        )

    def _handle_dropdown_change(
        self,
        event: ft.Event[ft.Dropdown],
        row_index: int,
        column: str,
    ) -> None:
        """Commit a fixed dropdown selection immediately."""

        value = event.control.value

        self._commit_editor_value(
            row_index=row_index,
            column=column,
            value=value,
        )

    def _commit_editor_value(
        self,
        *,
        row_index: int,
        column: str,
        value: object,
    ) -> None:
        """Apply one finalized edit and refresh only when it changed."""

        if (
            row_index < 0
            or row_index >= len(self.working_team)
        ):
            return

        previous_value = self.working_team[
            row_index
        ].get(column)

        if previous_value == value:
            return

        self.working_team[
            row_index
        ][column] = value

        if column == "Pokemon" and isinstance(value, str):
            record = self.working_team[row_index]
            if self._apply_known_pokemon_types(
                record,
                value,
            ):
                for type_column in ("Type1", "Type2"):
                    type_control = self.editor_controls.get(
                        (row_index, type_column)
                    )
                    if type_control is not None:
                        type_control.value = record[type_column]

        self._update_dirty_state()
        self.page.update()

    def _refresh_selector(self) -> None:
        options: list[ft.DropdownOption] = []

        if self.saved_team_snapshot:
            options.append(
                ft.DropdownOption(
                    key="heading:party",
                    content=ft.Text(
                        f"PARTY · {len(self.saved_team_snapshot)}",
                        weight=ft.FontWeight.BOLD,
                        color=TEXT_MUTED,
                    ),
                )
            )
            options.extend(
                ft.DropdownOption(
                    key=f"party:{index}",
                    text=str(
                        pokemon.get("Pokemon")
                        or f"Team Slot {index + 1}"
                    ),
                )
                for index, pokemon in enumerate(
                    self.saved_team_snapshot
                )
            )

        if self.saved_box_snapshot:
            options.append(
                ft.DropdownOption(
                    key="heading:box",
                    content=ft.Text(
                        f"BOX · {len(self.saved_box_snapshot)}",
                        weight=ft.FontWeight.BOLD,
                        color=TEXT_MUTED,
                    ),
                )
            )
            options.extend(
                ft.DropdownOption(
                    key=f"box:{index}",
                    text=str(
                        pokemon.get("Pokemon")
                        or f"Box Slot {index + 1}"
                    ),
                )
                for index, pokemon in enumerate(
                    self.saved_box_snapshot
                )
            )

        self.detail_selector.options = options

        selected_records = (
            self.saved_box_snapshot
            if self.selected_source == "box"
            else self.saved_team_snapshot
        )
        if self.selected_index >= len(selected_records):
            self.selected_source = "party"
            self.selected_index = 0

        if self.saved_team_snapshot or self.saved_box_snapshot:
            if (
                self.selected_source == "party"
                and not self.saved_team_snapshot
            ):
                self.selected_source = "box"
                self.selected_index = 0
            self.detail_selector.value = (
                f"{self.selected_source}:{self.selected_index}"
            )
        else:
            self.detail_selector.value = None

        self._sync_box_buttons()

    def _handle_detail_selection(
        self,
        event: ft.Event[ft.Dropdown],
    ) -> None:
        value = event.control.value
        if value is None:
            return
        if value.startswith("heading:"):
            event.control.value = (
                f"{self.selected_source}:{self.selected_index}"
            )
            self.page.update()
            return

        try:
            source, raw_index = value.split(":", 1)
            selected_index = int(raw_index)
        except (ValueError, TypeError):
            return

        if source not in {"party", "box"}:
            return

        records = (
            self.saved_box_snapshot
            if source == "box"
            else self.saved_team_snapshot
        )
        if selected_index < 0 or selected_index >= len(records):
            return

        self.selected_source = source
        self.selected_index = selected_index
        self._refresh_detail()
        self._sync_box_buttons()
        self.page.update()

    def _refresh_detail(self) -> None:
        records = (
            self.saved_box_snapshot
            if self.selected_source == "box"
            else self.saved_team_snapshot
        )

        if not records:
            fallback = (
                self.saved_team_snapshot
                if self.selected_source == "box"
                else self.saved_box_snapshot
            )
            if not fallback:
                self.detail_host.content = ft.Text(
                    "No Pokémon loaded.",
                    color=TEXT_SECONDARY,
                )
                self._sync_box_buttons()
                return
            self.selected_source = (
                "party" if self.saved_team_snapshot else "box"
            )
            self.selected_index = 0
            records = fallback

        if self.selected_index >= len(records):
            self.selected_index = 0

        pokemon = records[self.selected_index]
        self.detail_host.content = self._build_detail_card(pokemon)
        self._sync_box_buttons()

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
                    font_family=FONT_FAMILY_DISPLAY,
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
                                    self._build_evolution_summary(
                                        pokemon
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
                        ft.ResponsiveRow(
                            controls=cast(
                                list[ft.Control],
                                [
                                    ft.Container(
                                        content=ft.Text(
                                            "Stats",
                                            size=19,
                                            weight=ft.FontWeight.BOLD,
                                            color=TEXT_PRIMARY,
                                        ),
                                        col={
                                            "xs": 12,
                                            "sm": 4,
                                        },
                                        alignment=ft.Alignment.CENTER_LEFT,
                                    ),
                                    ft.Container(
                                        content=self._build_nature_summary(
                                            pokemon
                                        ),
                                        col={
                                            "xs": 12,
                                            "sm": 8,
                                        },
                                        alignment=ft.Alignment.CENTER_RIGHT,
                                    ),
                                ],
                            ),
                            columns=12,
                            spacing=12,
                            run_spacing=8,
                            vertical_alignment=(
                                ft.CrossAxisAlignment.CENTER
                            ),
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

    def _build_evolution_summary(
        self,
        pokemon: dict,
    ) -> ft.Control:
        """Build concise next-evolution guidance for one Pokémon."""

        pokemon_name = str(
            pokemon.get("Pokemon") or ""
        ).strip()

        if not pokemon_name:
            return ft.Container()

        evolution_record = self.evolutions.get(
            pokemon_name
        )

        if not isinstance(evolution_record, dict):
            return ft.Container()

        evolution_options = evolution_record.get(
            "evolutions"
        )

        if not isinstance(evolution_options, list):
            return ft.Container()

        if not evolution_options:
            return ft.Container(
                content=ft.Text(
                    "Final evolutionary stage",
                    size=14,
                    weight=ft.FontWeight.BOLD,
                    color=TEXT_MUTED,
                    text_align=ft.TextAlign.CENTER,
                ),
                margin=ft.Margin.only(top=4),
            )

        heading = (
            "Evolution Options"
            if len(evolution_options) > 1
            else "Next Evolution"
        )

        option_controls = cast(
            list[ft.Control],
            [],
        )

        for evolution in evolution_options:
            if not isinstance(evolution, dict):
                continue

            evolved_name = str(
                evolution.get("into") or ""
            ).strip()

            requirement = str(
                evolution.get("display_text") or ""
            ).strip()

            if not evolved_name or not requirement:
                continue

            option_controls.append(
                ft.Text(
                    f"{evolved_name} — {requirement}",
                    size=14,
                    color=TEXT_SECONDARY,
                    text_align=ft.TextAlign.CENTER,
                )
            )

        if not option_controls:
            return ft.Container()

        return ft.Container(
            content=ft.Column(
                controls=cast(
                    list[ft.Control],
                    [
                        ft.Text(
                            heading,
                            size=13,
                            weight=ft.FontWeight.BOLD,
                            color=PRIMARY_BLUE,
                            text_align=ft.TextAlign.CENTER,
                        ),
                        *option_controls,
                    ],
                ),
                spacing=3,
                horizontal_alignment=(
                    ft.CrossAxisAlignment.CENTER
                ),
                tight=True,
            ),
            margin=ft.Margin.only(top=4),
            padding=ft.Padding.symmetric(
                horizontal=12,
                vertical=8,
            ),
            bgcolor=PRIMARY_BLUE_SOFT,
            border_radius=10,
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

            if asset_exists(badge_path):
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
    @staticmethod
    def _build_nature_summary(
        pokemon: dict,
    ) -> ft.Control:
        """Build the Nature and its affected-stat summary."""

        nature = str(
            pokemon.get("Nature") or ""
        ).strip()

        if nature not in NATURE_EFFECTS:
            return ft.Text(
                "Nature: —",
                size=14,
                color=TEXT_MUTED,
            )

        boosted_stat, lowered_stat = (
            NATURE_EFFECTS[nature]
        )

        controls = cast(
            list[ft.Control],
            [
                ft.Text(
                    f"Nature: {nature},",
                    size=14,
                    weight=ft.FontWeight.BOLD,
                    color=TEXT_SECONDARY,
                ),
            ],
        )

        if boosted_stat is None or lowered_stat is None:
            controls.append(
                ft.Text(
                    "Neutral",
                    size=14,
                    weight=ft.FontWeight.BOLD,
                    color=TEXT_MUTED,
                )
            )
        else:
            controls.extend(
                cast(
                    list[ft.Control],
                    [
                        ft.Icon(
                            ft.Icons.ARROW_UPWARD_ROUNDED,
                            size=17,
                            color="#F87171",
                        ),
                        ft.Text(
                            boosted_stat,
                            size=14,
                            weight=ft.FontWeight.BOLD,
                            color="#F87171",
                        ),
                        ft.Text(
                            "/",
                            size=14,
                            color=TEXT_MUTED,
                        ),
                        ft.Icon(
                            ft.Icons.ARROW_DOWNWARD_ROUNDED,
                            size=17,
                            color="#60A5FA",
                        ),
                        ft.Text(
                            lowered_stat,
                            size=14,
                            weight=ft.FontWeight.BOLD,
                            color="#60A5FA",
                        ),
                    ],
                )
            )

        return ft.Row(
            controls=controls,
            spacing=4,
            tight=True,
            wrap=True,
            vertical_alignment=ft.CrossAxisAlignment.CENTER,
        )

    def _build_stats(
        self,
        pokemon: dict,
    ) -> ft.Control:
        nature = str(
            pokemon.get("Nature") or ""
        ).strip()

        boosted_stat: str | None = None
        lowered_stat: str | None = None

        if nature in NATURE_EFFECTS:
            boosted_stat, lowered_stat = (
                NATURE_EFFECTS[nature]
            )

        return ft.Column(
            controls=cast(
                list[ft.Control],
                [
                    self._build_stat_row(
                        stat_name,
                        self._numeric_value(
                            pokemon.get(stat_name)
                        ),
                        boosted=(
                            stat_name == boosted_stat
                        ),
                        lowered=(
                            stat_name == lowered_stat
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
        *,
        boosted: bool = False,
        lowered: bool = False,
    ) -> ft.Control:
        progress_value = min(
            1.0,
            max(
                0.0,
                stat_value / 300,
            ),
        )

        if boosted:
            value_color = "#F87171"
        elif lowered:
            value_color = "#60A5FA"
        else:
            value_color = TEXT_PRIMARY

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
                        color=value_color,
                    ),
                ],
            ),
            spacing=10,
            vertical_alignment=(
                ft.CrossAxisAlignment.CENTER
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

            if asset_exists(badge_path):
                card_controls.append(
                    ft.GestureDetector(
                        content=ft.Image(
                            src=self._asset_src(
                                badge_path
                            ),
                            height=18,
                            fit=ft.BoxFit.CONTAIN,
                            semantics_label=(
                                f"{move_type} type"
                            ),
                        ),
                        mouse_cursor=ft.MouseCursor.CLICK,
                        tooltip=(
                            f"View {move_type} offensive matchups"
                        ),
                        on_tap=(
                            lambda event,
                            selected_type=move_type:
                            self._show_offensive_type_matchups(
                                event,
                                selected_type,
                            )
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

    def _show_offensive_type_matchups(
        self,
        event: ft.TapEvent[ft.GestureDetector],
        move_type: str,
    ) -> None:
        """Show offensive single-type matchup information."""

        del event

        show_type_matchup_dialog(
            page=self.page,
            pokemon_type=move_type,
            type_chart=self.type_chart,
            mode="offensive",
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

        if asset_exists(badge_path):
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

    @staticmethod
    def _normalize_item_name(item_name: str) -> str:
        """Normalize held-item names for reliable comparisons."""

        return " ".join(item_name.strip().casefold().split())

    def _recommendation_target_record(self) -> dict | None:
        """Return the working party/Box record targeted by the popup."""

        if (
            self._recommendation_target_source is None
            or self._recommendation_target_index is None
        ):
            return None

        records = (
            self.working_box
            if self._recommendation_target_source == "box"
            else self.working_team
        )
        index = self._recommendation_target_index
        if index < 0 or index >= len(records):
            return None
        return records[index]

    def _show_item_recommendations(
        self,
        event: ft.Event[ft.IconButton],
        pokemon: dict,
    ) -> None:
        """Show modeled held items not already equipped by this Pokémon."""

        del event

        self._recommendation_target_source = self.selected_source
        self._recommendation_target_index = self.selected_index

        target_record = self._recommendation_target_record()
        recommendation_record = (
            target_record if target_record is not None else pokemon
        )

        recommendations = recommend_held_items(
            pokemon=recommendation_record,
            moves_data=self.moves_data,
            items_data=self.items_data,
        )

        current_item_name = str(
            recommendation_record.get("Held Item") or ""
        ).strip()
        equipped_item = self._normalize_item_name(
            current_item_name
        )
        if equipped_item in {"", "none", "—", "-"}:
            equipped_item = ""
            current_item_name = ""

        if equipped_item:
            recommendations = [
                recommendation
                for recommendation in recommendations
                if self._normalize_item_name(
                    recommendation.item
                ) != equipped_item
            ]

        pokemon_name = str(
            recommendation_record.get("Pokemon")
            or "this Pokémon"
        )

        self.page.show_dialog(
            ft.AlertDialog(
                modal=True,
                title=ft.Text(
                    "Suggested Held Items",
                    weight=ft.FontWeight.BOLD,
                    font_family=FONT_FAMILY_HEADER,
                    color=TEXT_PRIMARY,
                ),
                content=ft.Container(
                    content=self._build_item_recommendation_content(
                        pokemon_name,
                        recommendations,
                        current_item_name=current_item_name,
                        had_equipped_item=bool(equipped_item),
                    ),
                    width=620,
                    height=520,
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
        *,
        current_item_name: str,
        had_equipped_item: bool,
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
            empty_text = (
                "This Pokémon is already holding the modeled "
                "recommended item."
                if had_equipped_item
                else "No currently modeled held items match this build yet."
            )
            controls.append(
                ft.Container(
                    content=ft.Text(
                        empty_text,
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
                    recommendation,
                    current_item_name=current_item_name,
                )
                for recommendation in recommendations
            )

        return ft.Column(
            controls=controls,
            spacing=14,
            scroll=ft.ScrollMode.AUTO,
        )

    def _modeled_item_record(self, item_name: str) -> dict | None:
        """Return one modeled held-item record by normalized name."""

        normalized_name = self._normalize_item_name(item_name)
        if not normalized_name:
            return None
        for item in self.items_data:
            if not isinstance(item, dict):
                continue
            modeled_name = str(item.get("Item") or "").strip()
            if self._normalize_item_name(modeled_name) == normalized_name:
                return item
        return None

    @staticmethod
    def _format_percent(value: float) -> str:
        rounded = round(value, 2)
        return (
            f"{int(rounded)}%"
            if float(rounded).is_integer()
            else f"{rounded:g}%"
        )

    @staticmethod
    def _item_effect_dimensions(item: dict) -> dict[str, dict[str, object]]:
        """Translate modeled item metadata into comparable effects."""

        effects: dict[str, dict[str, object]] = {}
        item_name = str(item.get("Item") or "").strip()
        effect_type = str(item.get("EffectType") or "").strip()
        stat = str(item.get("StatAffected") or "").strip()
        move_type = str(item.get("MoveTypeAffected") or "").strip()
        move_category = str(item.get("MoveCategoryAffected") or "").strip()
        condition = str(item.get("Condition") or "").strip()
        try:
            multiplier = float(item.get("Multiplier", 1) or 1)
        except (TypeError, ValueError):
            multiplier = 1.0

        if effect_type == "DamageMultiplier":
            amount = (multiplier - 1.0) * 100
            if move_type and move_type != "None":
                key = f"damage:type:{move_type.casefold()}"
                label = f"{move_type} attack damage"
            elif move_category and move_category != "None":
                key = f"damage:category:{move_category.casefold()}"
                label = f"{move_category} attack damage"
            elif condition == "SuperEffective":
                key = "damage:super_effective"
                label = "Super-effective attack damage"
            elif condition == "DamagingMove":
                key = "damage:all_damaging"
                label = "Damaging move damage"
            else:
                key = "damage:general"
                label = "Attack damage"
            effects[key] = {"label": label, "amount": amount, "beneficial": True}

        elif effect_type == "StatMultiplier":
            amount = (multiplier - 1.0) * 100
            stat_labels = {
                "ATK": "Attack", "DEF": "Defense",
                "SPA": "Special Attack", "SPD": "Special Defense",
                "SPE": "Speed", "DEF/SPD": "Defense and Special Defense",
            }
            label = stat_labels.get(stat, stat or "Stat")
            effects[f"stat:{stat.casefold()}"] = {
                "label": label, "amount": amount, "beneficial": True
            }

        elif effect_type == "Healing":
            amount = multiplier * 100
            if condition in {"EndOfTurn", "PoisonType"}:
                effects["healing:end_turn"] = {
                    "label": "End-of-turn HP recovery",
                    "amount": amount, "beneficial": True, "suffix": " max HP",
                }
            elif condition == "DamageDealt":
                effects["healing:damage_dealt"] = {
                    "label": "HP recovered from damage dealt",
                    "amount": amount, "beneficial": True,
                }

        elif effect_type == "Immunity" and move_type and move_type != "None":
            effects[f"immunity:{move_type.casefold()}"] = {
                "label": (
                    f"{move_type} immunity until the holder is hit"
                    if condition == "UntilHit"
                    else f"{move_type} immunity"
                ),
                "amount": None, "beneficial": True,
            }

        elif effect_type == "Tactical":
            if item_name == "Rocky Helmet":
                effects["tactical:contact_damage"] = {
                    "label": "Damages the opponent when contacted (1/6 max HP)",
                    "amount": None, "beneficial": True,
                }
            elif item_name == "Focus Sash":
                effects["tactical:focus_sash"] = {
                    "label": "Can survive an otherwise lethal hit at full HP",
                    "amount": None, "beneficial": True,
                }

        if item_name in {"Choice Band", "Choice Scarf", "Choice Specs"}:
            effects["drawback:move_lock"] = {
                "label": "Locked into the first selected move",
                "reverse_label": "Can freely change moves",
                "amount": None, "beneficial": False,
            }
        if item_name == "Assault Vest":
            effects["drawback:no_status_moves"] = {
                "label": "Cannot select status moves",
                "reverse_label": "Can use status moves",
                "amount": None, "beneficial": False,
            }
        if item_name == "Life Orb":
            effects["drawback:life_orb_recoil"] = {
                "label": "Loses 10% max HP after dealing damage",
                "reverse_label": "No Life Orb recoil",
                "amount": None, "beneficial": False,
            }
        return effects

    def _item_comparison_lines(
        self,
        current_item_name: str,
        recommended_item_name: str,
    ) -> list[tuple[str, str]]:
        """Return concise gains/losses when switching modeled items."""

        if not current_item_name:
            return []
        current_item = self._modeled_item_record(current_item_name)
        recommended_item = self._modeled_item_record(recommended_item_name)
        if current_item is None or recommended_item is None:
            return []
        current_effects = self._item_effect_dimensions(current_item)
        recommended_effects = self._item_effect_dimensions(recommended_item)
        lines: list[tuple[str, str]] = []
        all_keys = list(dict.fromkeys([*current_effects, *recommended_effects]))

        for key in all_keys:
            current = current_effects.get(key)
            recommended = recommended_effects.get(key)
            if current is not None and recommended is not None:
                ca, ra = current.get("amount"), recommended.get("amount")
                if isinstance(ca, (int, float)) and isinstance(ra, (int, float)):
                    delta = float(ra) - float(ca)
                    if abs(delta) < 0.005:
                        continue
                    beneficial = bool(recommended.get("beneficial", True))
                    improves = delta > 0 if beneficial else delta < 0
                    direction = "up" if improves else "down"
                    sign = "+" if delta > 0 else "−"
                    label = str(recommended.get("label") or current.get("label") or "Effect")
                    suffix = str(recommended.get("suffix") or current.get("suffix") or "")
                    lines.append((
                        direction,
                        f"{label} {sign}{self._format_percent(abs(delta))}{suffix}",
                    ))
                continue

            effect = recommended or current
            if effect is None:
                continue
            beneficial = bool(effect.get("beneficial", True))
            is_added = recommended is not None
            if beneficial:
                direction = "up" if is_added else "down"
                label = str(effect.get("label") or "Effect")
                amount = effect.get("amount")
                if isinstance(amount, (int, float)):
                    sign = "+" if is_added else "−"
                    suffix = str(effect.get("suffix") or "")
                    label = f"{label} {sign}{self._format_percent(abs(float(amount)))}{suffix}"
            else:
                direction = "down" if is_added else "up"
                label = str(
                    (effect.get("label") if is_added else effect.get("reverse_label"))
                    or effect.get("label") or "Effect"
                )
            lines.append((direction, label))
        return lines

    def _build_item_comparison(
        self,
        current_item_name: str,
        recommended_item_name: str,
    ) -> ft.Control | None:
        """Build the contextual tradeoff summary for a suggested item."""

        if not current_item_name:
            return None
        lines = self._item_comparison_lines(
            current_item_name, recommended_item_name
        )
        controls: list[ft.Control] = [
            ft.Text(
                f"Compared with {current_item_name}",
                size=14, weight=ft.FontWeight.BOLD, color=TEXT_PRIMARY,
            )
        ]
        if not lines:
            controls.append(ft.Text(
                "No modeled effect change.", size=13, color=TEXT_MUTED, italic=True
            ))
        else:
            for direction, line_text in lines:
                is_gain = direction == "up"
                controls.append(ft.Row(
                    controls=[
                        ft.Icon(
                            ft.Icons.ARROW_UPWARD_ROUNDED if is_gain
                            else ft.Icons.ARROW_DOWNWARD_ROUNDED,
                            size=17, color=SUCCESS if is_gain else "#F59E7A",
                        ),
                        ft.Text(line_text, size=13, color=TEXT_SECONDARY, expand=True),
                    ],
                    spacing=7, vertical_alignment=ft.CrossAxisAlignment.START,
                ))
        return ft.Container(
            content=ft.Column(controls=controls, spacing=6),
            padding=ft.Padding.symmetric(horizontal=12, vertical=10),
            bgcolor=SURFACE_RAISED,
            border=ft.Border.all(1, BORDER_DEFAULT),
            border_radius=10,
        )

    def _build_item_recommendation_card(
        self,
        recommendation: ItemRecommendation,
        *,
        current_item_name: str,
    ) -> ft.Control:
        """Build one unranked recommendation with actionable choices."""

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

        comparison_control = self._build_item_comparison(
            current_item_name,
            recommendation.item,
        )

        catalog_item = self.journey_item_by_name.get(
            self._normalize_item_name(recommendation.item)
        )
        checklist_available = catalog_item is not None
        checklist_item_id = (
            str(catalog_item.get("id", "")).strip()
            if catalog_item is not None
            else ""
        )
        already_on_checklist = (
            bool(checklist_item_id)
            and self._journey_checklist_contains_item(checklist_item_id)
        )

        action_controls: list[ft.Control] = [
            ft.Button(
                content="Add to Pokémon",
                icon=ft.Icons.CATCHING_POKEMON_ROUNDED,
                bgcolor=PRIMARY_BLUE,
                color=TEXT_PRIMARY,
                icon_color=TEXT_PRIMARY,
                on_click=(
                    lambda event, item_name=recommendation.item:
                    self._request_add_recommended_item_to_pokemon(
                        event,
                        item_name,
                    )
                ),
            ),
            ft.Button(
                content=(
                    "Already in Journey Checklist"
                    if already_on_checklist
                    else "Add to Journey Checklist"
                ),
                icon=(
                    ft.Icons.CHECK_CIRCLE_ROUNDED
                    if already_on_checklist
                    else ft.Icons.PLAYLIST_ADD_CHECK_ROUNDED
                ),
                disabled=(
                    not checklist_available or already_on_checklist
                ),
                tooltip=(
                    "This item is already in the Journey Checklist."
                    if already_on_checklist
                    else (
                        None
                        if checklist_available
                        else (
                            "This item is not yet available in the "
                            "Journey item catalog."
                        )
                    )
                ),
                on_click=(
                    (
                        lambda event, item_name=recommendation.item:
                        self._add_recommended_item_to_checklist(
                            event,
                            item_name,
                        )
                    )
                    if checklist_available and not already_on_checklist
                    else None
                ),
            ),
        ]

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
                            size=TEXT_SIZE_BODY,
                            color=TEXT_SECONDARY,
                        ),
                        ft.Text(
                            "Why this item?",
                            size=14,
                            weight=ft.FontWeight.BOLD,
                            color=TEXT_PRIMARY,
                        ),
                        *reason_controls,
                        *(
                            [comparison_control]
                            if comparison_control is not None
                            else []
                        ),
                        ft.Row(
                            controls=action_controls,
                            spacing=10,
                            run_spacing=10,
                            wrap=True,
                        ),
                        ft.Text(
                            (
                                "Adding an item to a Pokémon updates the Team Editor. "
                                "Remember to click Save Team to keep the change."
                            ),
                            size=12,
                            color=TEXT_MUTED,
                            italic=True,
                        ),
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

    def _journey_checklist_contains_item(
        self,
        item_id: str,
    ) -> bool:
        """Return whether saved Journey state currently requires this item."""

        normalized_id = item_id.strip()
        if not normalized_id:
            return False

        for record in self.app_state.my_journey_data.get(
            "item_objectives",
            [],
        ):
            if not isinstance(record, dict):
                continue
            if str(record.get("id", "")).strip() != normalized_id:
                continue

            # AppState only persists item-objective rows whose total required
            # quantity is greater than zero, including Team Planner-derived
            # requirements. The matching row itself is therefore sufficient.
            return True

        return False

    def _request_add_recommended_item_to_pokemon(
        self,
        event: ft.Event[ft.Button],
        item_name: str,
    ) -> None:
        """Add a recommendation, confirming replacement when necessary."""

        del event
        target = self._recommendation_target_record()
        if target is None:
            return

        current_item = str(target.get("Held Item") or "").strip()
        normalized_current = self._normalize_item_name(current_item)
        normalized_new = self._normalize_item_name(item_name)

        if normalized_current == normalized_new:
            return

        self._pending_recommended_item = item_name
        self.page.pop_dialog()

        if normalized_current not in {"", "none", "—", "-"}:
            pokemon_name = str(
                target.get("Pokemon") or "this Pokémon"
            )
            dialog = ft.AlertDialog()
            dialog.modal = True
            dialog.title = ft.Text(
                f"Replace {current_item}?",
                weight=ft.FontWeight.BOLD,
            )
            dialog.content = ft.Column(
                controls=[
                    ft.Text(
                        (
                            f"{pokemon_name} is currently holding {current_item}. "
                            f"Replace it with {item_name} in the Team Editor?"
                        ),
                        color=TEXT_SECONDARY,
                    ),
                    ft.Text(
                        (
                            "This updates the Team Editor only. "
                            "Remember to click Save Team to keep the change."
                        ),
                        size=12,
                        color=TEXT_MUTED,
                        italic=True,
                    ),
                ],
                spacing=10,
                tight=True,
            )
                
            dialog.actions = [
                ft.Button(
                    content="Cancel",
                    on_click=self._cancel_recommended_item_change,
                ),
                ft.Button(
                    content="Replace Item",
                    icon=ft.Icons.SWAP_HORIZ_ROUNDED,
                    bgcolor=PRIMARY_BLUE,
                    color=TEXT_PRIMARY,
                    icon_color=TEXT_PRIMARY,
                    on_click=self._confirm_recommended_item_change,
                ),
            ]
            dialog.actions_alignment = ft.MainAxisAlignment.END
            self.page.show_dialog(dialog)
            return

        self._apply_recommended_item_to_working_record(item_name)

    def _cancel_recommended_item_change(
        self,
        event: ft.Event[ft.Button],
    ) -> None:
        del event
        self._pending_recommended_item = None
        self.page.pop_dialog()
        self.page.update()

    def _confirm_recommended_item_change(
        self,
        event: ft.Event[ft.Button],
    ) -> None:
        del event
        item_name = self._pending_recommended_item
        self._pending_recommended_item = None
        self.page.pop_dialog()
        if item_name:
            self._apply_recommended_item_to_working_record(item_name)

    def _apply_recommended_item_to_working_record(
        self,
        item_name: str,
    ) -> None:
        """Write the item into working Team/Box state for normal saving."""

        target = self._recommendation_target_record()
        if target is None:
            return

        target["Held Item"] = item_name

        self.editor_controls.clear()
        self._autocomplete_edit_versions.clear()
        self.table_host.content = self._build_editor_table()
        self.box_table_host.content = self._build_box_table()
        self._update_dirty_state()

        pokemon_name = str(
            target.get("Pokemon") or "this Pokémon"
        )

        self.save_status.value = (
            f"{item_name} added to {pokemon_name}. Save Team to keep it."
        )
        self.save_status.color = "#FFE5A3"
        self.page.update()

        dialog = ft.AlertDialog()
        dialog.modal = True
        dialog.title = ft.Text(
            "Held Item Added",
            weight=ft.FontWeight.BOLD,
        )
        dialog.content = ft.Text(
            (
                f"{item_name} has been given to {pokemon_name} to hold. "
                'Please be sure to click "Save Team" to send the '
                "updated information to the Battle Compass."
            ),
            color=TEXT_SECONDARY,
        )
        dialog.actions = [
            ft.Button(
            content="Got It",
            on_click=self._dismiss_held_item_added_dialog,
        )
        ]
        dialog.actions_alignment = ft.MainAxisAlignment.END

        self.page.show_dialog(dialog)

        catalog_item = self.journey_item_by_name.get(
            self._normalize_item_name(item_name)
        )
        if catalog_item is not None:
            checklist_item_id = str(
                catalog_item.get("id", "")
            ).strip()
            if (
                checklist_item_id
                and self._journey_checklist_contains_item(
                    checklist_item_id
                )
            ):
                self.page.run_task(
                    self._remove_equipped_item_from_checklist,
                    checklist_item_id,
                )

    async def _remove_equipped_item_from_checklist(
        self,
        item_id: str,
    ) -> None:
        """Remove an equipped recommended item from checklist state."""

        my_journey = self.app_state.my_journey_data
        raw_records = my_journey.get("item_objectives", [])
        if not isinstance(raw_records, list):
            return

        updated_records = [
            dict(record)
            for record in raw_records
            if (
                isinstance(record, dict)
                and str(record.get("id", "")).strip() != item_id
            )
        ]

        try:
            succeeded = await self.app_state.save_item_checklist(
                updated_records
            )
        except (RuntimeError, ValueError):
            return

        if succeeded and self.on_journey_updated is not None:
            self.on_journey_updated()

    async def _dismiss_held_item_added_dialog(
        self,
        event: ft.Event[ft.Button],
    ) -> None:
        """Close the confirmation and return to the Team Editor to save."""

        del event

        self.page.pop_dialog()
        self.page.update()

        await self._scroll_to_team_editor(
            offset=350,
            delay=0.05,
        )

    def _add_recommended_item_to_checklist(
        self,
        event: ft.Event[ft.Button],
        item_name: str,
    ) -> None:
        """Schedule a catalog-backed checklist addition."""

        del event
        catalog_item = self.journey_item_by_name.get(
            self._normalize_item_name(item_name)
        )
        if catalog_item is None:
            return

        self.page.pop_dialog()
        self.page.run_task(
            self._persist_recommended_item_to_checklist,
            str(catalog_item.get("id", "")),
            item_name,
        )

    async def _persist_recommended_item_to_checklist(
        self,
        item_id: str,
        item_name: str,
    ) -> None:
        try:
            succeeded = await self.app_state.add_manual_item_objective(
                item_id=item_id,
                quantity=1,
            )
        except (RuntimeError, ValueError) as error:
            self.page.show_dialog(
                ft.SnackBar(
                    content=ft.Text(
                        f"{item_name} could not be added: {error}"
                    )
                )
            )
            return

        if not succeeded:
            self.page.show_dialog(
                ft.AlertDialog(
                    modal=True,
                    title=ft.Text(
                        "Journey Checklist Not Updated",
                        weight=ft.FontWeight.BOLD,
                    ),
                    content=ft.Text(
                        f"{item_name} could not be added to the Journey Checklist.",
                        color=TEXT_SECONDARY,
                    ),
                    actions=[
                        ft.Button(
                            content="Close",
                            on_click=lambda: self.page.pop_dialog(),
                        )
                    ],
                    actions_alignment=ft.MainAxisAlignment.END,
                )
            )
            return

        dialog = ft.AlertDialog()
        dialog.modal = True
        dialog.title = ft.Text(
            "Journey Checklist Updated",
            weight=ft.FontWeight.BOLD,
        )
        dialog.content = ft.Text(
            f"{item_name} has been added to the Journey Checklist.",
            color=TEXT_SECONDARY,
        )
        dialog.actions = [
            ft.Button(
                content="Got It",
                on_click=self._dismiss_checklist_updated_dialog,
            )
        ]
        dialog.actions_alignment = ft.MainAxisAlignment.END
        self.page.show_dialog(dialog)

    def _dismiss_checklist_updated_dialog(
        self,
        event: ft.Event[ft.Button],
    ) -> None:
        """Close confirmation and rebuild views from current Journey state."""

        del event
        self.page.pop_dialog()

        if self.on_journey_updated is not None:
            self.on_journey_updated()

        self.page.update()

    def _close_item_recommendations(
        self,
        event: ft.Event[ft.Button],
    ) -> None:
        """Close the held-item recommendation dialog."""

        del event
        self._recommendation_target_source = None
        self._recommendation_target_index = None
        self._pending_recommended_item = None
        self.page.pop_dialog()
        self.page.update()

    async def _export_journey(
        self,
        event: ft.Event[ft.Button],
    ) -> None:
        """Export the currently saved Journey to JSON."""

        del event

        if self.has_unsaved_changes:
            self.save_status.value = (
                "Save or discard your changes before exporting."
            )
            self.save_status.color = "#FFE5A3"
            self.page.update()
            return

        try:
            journey = self.app_state.get_journey_export_copy()
            serialized_export = serialize_journey_export(
                journey,
                app_version=_app_version(),
            )

            export_filename = journey_export_filename()

            selected_path = await ft.FilePicker().save_file(
                dialog_title="Export Journey",
                file_name=export_filename,
                file_type=ft.FilePickerFileType.CUSTOM,
                allowed_extensions=["json"],
                src_bytes=serialized_export.encode("utf-8"),
            )

            if not self.page.web:
                if not selected_path:
                    return
        except (OSError, RuntimeError, ValueError) as error:
            self.save_status.value = (
                f"Journey could not be exported: {error}"
            )
            self.save_status.color = "#F87171"
            self.page.update()
            return

        self.save_status.value = "Journey exported successfully."
        self.save_status.color = SUCCESS
        self.page.update()

    async def _select_journey_file(
        self,
        event: ft.Event[ft.Button],
    ) -> None:
        """Select and validate a Journey export."""

        del event

        if self.page.web:
            try:
                await ft.UrlLauncher().launch_url(
                    ft.Url(
                        url="./import.html",
                        target=ft.UrlTarget.SELF,
                    )
                )
            except (RuntimeError, ValueError) as error:
                self._show_load_error(
                    f"The Journey import helper could not be opened: {error}"
                )
            return

        try:
            selected_files = await ft.FilePicker().pick_files(
                dialog_title="Load Journey",
                allow_multiple=False,
                file_type=ft.FilePickerFileType.CUSTOM,
                allowed_extensions=["json"],
                with_data=True,
                cancel_upload_on_window_blur=False,
            )

            if not selected_files:
                return

            selected_file = selected_files[0]

            if selected_file.bytes is not None:
                serialized_export = selected_file.bytes.decode("utf-8")
            elif selected_file.path:
                serialized_export = Path(selected_file.path).read_text(
                    encoding="utf-8"
                )
            else:
                self._show_load_error(
                    "The selected file could not be accessed."
                )
                return

        except (OSError, UnicodeError) as error:
            self._show_load_error(
                f"The selected Journey file could not be read: {error}"
            )
            return

        import_result = parse_journey_export(serialized_export)

        if (
            import_result.status != "valid"
            or import_result.journey is None
        ):
            self._show_load_error(
                import_result.error
                or "The selected Journey file is invalid."
            )
            return

        self.pending_import_journey = import_result.journey
        self._show_load_confirmation(import_result.journey)

    def _show_load_confirmation(self, journey: dict) -> None:
        """Confirm replacement of the active Journey."""

        starter = str(journey.get("starter") or "Unknown")
        team = journey.get("team")
        team_count = len(team) if isinstance(team, list) else 0

        controls = cast(
            list[ft.Control],
            [
                ft.Text(
                    (
                        "Loading this Journey will overwrite the "
                        "Journey currently saved in Pokémon Battle "
                        "Compass."
                    ),
                    size=15,
                    color=TEXT_SECONDARY,
                ),
                ft.Container(
                    content=ft.Column(
                        controls=cast(
                            list[ft.Control],
                            [
                                ft.Text(
                                    f"Starter: {starter}",
                                    weight=ft.FontWeight.BOLD,
                                    color=TEXT_PRIMARY,
                                ),
                                ft.Text(
                                    f"Active team: {team_count} Pokémon",
                                    color=TEXT_SECONDARY,
                                ),
                            ],
                        ),
                        spacing=6,
                        tight=True,
                    ),
                    padding=12,
                    bgcolor=SURFACE_RAISED,
                    border_radius=10,
                ),
            ],
        )

        if self.has_unsaved_changes:
            controls.append(
                ft.Container(
                    content=ft.Text(
                        (
                            "You also have unsaved My Team changes. "
                            "Those edits will be discarded."
                        ),
                        size=14,
                        color="#FFE5A3",
                    ),
                    padding=12,
                    bgcolor="#3B3017",
                    border_radius=10,
                )
            )

        self.page.show_dialog(
            ft.AlertDialog(
                modal=True,
                title=ft.Text(
                    "Load this Journey?",
                    weight=ft.FontWeight.BOLD,
                    color=TEXT_PRIMARY,
                ),
                content=ft.Container(
                    content=ft.Column(
                        controls=controls,
                        spacing=14,
                        tight=True,
                    ),
                    width=520,
                ),
                actions=cast(
                    list[ft.Control],
                    [
                        ft.Button(
                            content="Cancel",
                            on_click=self._cancel_journey_load,
                        ),
                        ft.Button(
                            content="Load Journey",
                            icon=ft.Icons.UPLOAD_FILE_OUTLINED,
                            bgcolor=PRIMARY_BLUE,
                            color=TEXT_PRIMARY,
                            icon_color=TEXT_PRIMARY,
                            on_click=self._confirm_journey_load,
                        ),
                    ],
                ),
                actions_alignment=ft.MainAxisAlignment.END,
            )
        )

    def _cancel_journey_load(
        self,
        event: ft.Event[ft.Button],
    ) -> None:
        """Cancel a pending Journey import."""

        del event
        self.pending_import_journey = None
        self.page.pop_dialog()
        self.page.update()

    async def _confirm_journey_load(
        self,
        event: ft.Event[ft.Button],
    ) -> None:
        """Persist an imported Journey and rebuild the app."""

        del event
        imported_journey = self.pending_import_journey

        if imported_journey is None:
            self.page.pop_dialog()
            self._show_load_error(
                "No valid Journey is waiting to be loaded."
            )
            return

        self.page.pop_dialog()

        try:
            load_succeeded = await self.app_state.import_journey(
                imported_journey
            )
        except (RuntimeError, ValueError) as error:
            self.pending_import_journey = None
            self._show_load_error(
                f"The Journey could not be loaded: {error}"
            )
            return

        if not load_succeeded:
            self.pending_import_journey = None
            self._show_load_error(
                "The Journey could not be saved."
            )
            return

        self.pending_import_journey = None

        if self.on_journey_loaded is not None:
            self.on_journey_loaded()
            return

        self._show_load_error(
            (
                "The Journey was loaded, but the application could "
                "not refresh automatically. Restart Pokémon Battle "
                "Compass to continue."
            )
        )

    def _show_load_error(self, message: str) -> None:
        """Show a non-fatal Journey load error."""

        self.page.show_dialog(
            ft.AlertDialog(
                modal=True,
                title=ft.Text(
                    "Journey could not be loaded",
                    weight=ft.FontWeight.BOLD,
                    color=TEXT_PRIMARY,
                ),
                content=ft.Text(
                    (
                        f"{message}\n\n"
                        "Your current Journey has not been changed."
                    ),
                    size=15,
                    color=TEXT_SECONDARY,
                ),
                actions=[
                    ft.Button(
                        content="OK",
                        on_click=self._close_load_error,
                    ),
                ],
                actions_alignment=ft.MainAxisAlignment.END,
            )
        )

    def _close_load_error(
        self,
        event: ft.Event[ft.Button],
    ) -> None:
        """Close the Journey load error dialog."""

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
            save_succeeded = await self.app_state.save_team_and_box(
                saved_team,
                self.working_box,
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
        self.box_data = self.app_state.box_data
        self.working_team = deepcopy(self.app_state.team_data)
        self.saved_team_snapshot = deepcopy(self.app_state.team_data)
        self.working_box = deepcopy(self.app_state.box_data)
        self.saved_box_snapshot = deepcopy(self.app_state.box_data)
        self.box_table_host.content = self._build_box_table()
        self.save_button.disabled = True
        self.discard_button.disabled = True
        self.export_button.disabled = False
        self.detail_notice.visible = False

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