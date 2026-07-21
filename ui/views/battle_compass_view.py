"""
Battle Compass primary view.

Manages battle-selection controls, calls the existing engine through the
Battle Compass ViewModel, and renders live recommendation components.
"""

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path
from typing import cast

import flet as ft

from ui.components.full_analysis import (
    FULL_ANALYSIS_SCROLL_KEY,
    FullAnalysis,
)
from ui.components.opponent_card import OpponentCard
from ui.components.other_strong_options import (
    OtherStrongOptions,
    StrongOptionData,
    StrongOptionNote,
)
from ui.components.recommendation_card import RecommendationCard
from ui.components.reference_dialogs import (
    show_type_matchup_dialog,
)
from ui.rendering import (
    get_sprite_path,
    opponent_uses_gmax,
)
from ui.theme import (
    BORDER_DEFAULT,
    CONTENT_MAX_WIDTH,
    PRIMARY_BLUE,
    SURFACE,
    TEXT_MUTED,
    TEXT_PRIMARY,
    TEXT_SECONDARY,
)
from ui.viewmodels.app_state import AppState
from ui.viewmodels.battle_compass_vm import (
    BattleCompassViewModel,
    MatchupViewModel,
    build_battle_compass_view_model,
    get_effectiveness_label,
    load_reference_data,
)


PROJECT_ROOT = Path(__file__).resolve().parents[2]
ASSETS_DIR = PROJECT_ROOT / "assets"
TRAINER_TEXTURE_DIR = (
    ASSETS_DIR
    / "raw"
    / "pokesprite"
    / "pokemon-gen8"
    / "regular"
)

STARTER_OPTIONS = [
    "Grookey",
    "Scorbunny",
    "Sobble",
]


class BattleCompassView:
    """Interactive Battle Compass view backed by the existing engine."""

    def __init__(
        self,
        page: ft.Page,
        *,
        app_state: AppState,
        team_data: list[dict] | None = None,
        selected_starter: str | None = None,
        on_start_new_journey: Callable[[], None] | None = None,
    ) -> None:
        self.page = page
        self.app_state = app_state
        self.on_start_new_journey = on_start_new_journey

        reference_data = load_reference_data()

        self.team_data = (
            team_data
            if team_data is not None
            else reference_data["team_data"]
        )
        self.opponents = reference_data["opponents"]
        self.items = reference_data["items"]
        self.ability_rules = reference_data["ability_rules"]
        self.ability_descriptions = {
            row["Ability"]: row["Description"]
            for row in reference_data.get(
                "ability_descriptions",
                [],
            )
            if isinstance(row, dict)
            and isinstance(row.get("Ability"), str)
            and isinstance(row.get("Description"), str)
        }
        self.moves_data = reference_data["moves_data"]
        self.move_lookup = {
            move["Move"]: move
            for move in self.moves_data
            if isinstance(
                move.get("Move"),
                str,
            )
            and move.get("Move")
        }
        self.type_chart = reference_data["type_chart"]

        self.journey_starter = (
            selected_starter
            if selected_starter in STARTER_OPTIONS
            else STARTER_OPTIONS[0]
        )
        self.selected_starter = self.journey_starter
        self.pending_starter: str | None = None

        saved_selection = (
            self.app_state.battle_compass_selection
        )

        self.selected_trainer = (
            saved_selection.get("trainer")
            or ""
        )
        self.selected_battle = (
            saved_selection.get("battle")
            or ""
        )
        self.selected_opponent_name = (
            saved_selection.get("opponent")
            or ""
        )

        self.filtered_opponents: list[dict] = []
        self.battle_opponents: list[dict] = []

        self.starter_dropdown = ft.Dropdown(
            label="Your Starter",
            value=self.selected_starter,
            options=self._dropdown_options(
                STARTER_OPTIONS
            ),
            on_select=self._handle_starter_change,
        )

        self.trainer_dropdown = ft.Dropdown(
            label="Trainer",
            on_select=self._handle_trainer_change,
            col={
                "xs": 12,
                "md": 4,
            },
        )

        self.battle_dropdown = ft.Dropdown(
            label="Battle",
            on_select=self._handle_battle_change,
            col={
                "xs": 12,
                "md": 4,
            },
        )

        self.opponent_dropdown = ft.Dropdown(
            label="Opponent Pokémon",
            on_select=self._handle_opponent_change,
        )

        self.results_host = ft.Container(
            width=CONTENT_MAX_WIDTH,
        )

        self._initialize_selections()
        self._refresh_results()

    def refresh_team_data(
        self,
        team_data: list[dict],
    ) -> None:
        """Refresh recommendation results after the shared team is saved."""

        self.team_data = team_data
        self._refresh_results()

    def build(self) -> ft.Control:
        """Return the complete interactive Battle Compass view."""

        settings_card = ft.Container(
            content=ft.Column(
                controls=cast(
                    list[ft.Control],
                    [
                        ft.Text(
                            "Battle Settings",
                            size=24,
                            weight=ft.FontWeight.BOLD,
                            color=TEXT_PRIMARY,
                        ),
                        ft.ResponsiveRow(
                            controls=cast(
                                list[ft.Control],
                                [
                                    self._build_starter_control(),
                                    self.trainer_dropdown,
                                    self.battle_dropdown,
                                ],
                            ),
                            columns=12,
                            spacing=14,
                            run_spacing=14,
                        ),
                        self.opponent_dropdown,
                    ],
                ),
                spacing=16,
            ),
            width=940,
            padding=20,
            bgcolor=SURFACE,
            border=ft.Border.all(
                1,
                BORDER_DEFAULT,
            ),
            border_radius=16,
        )

        return ft.Column(
            controls=cast(
                list[ft.Control],
                [
                    settings_card,
                    self.results_host,
                ],
            ),
            spacing=24,
            horizontal_alignment=ft.CrossAxisAlignment.CENTER,
        )

    def _build_starter_control(self) -> ft.Control:
        """Build the starter dropdown with its Journey help popup."""

        help_popup = ft.PopupMenuButton(
            icon=ft.Icons.INFO_OUTLINE_ROUNDED,
            icon_color=PRIMARY_BLUE,
            tooltip="About changing your starter",
            bgcolor=SURFACE,
            menu_padding=6,
            size_constraints=ft.BoxConstraints(
                min_width=280,
                max_width=320,
            ),
            items=[
                ft.PopupMenuItem(
                    padding=0,
                    content=ft.Container(
                        content=ft.Column(
                            controls=cast(
                                list[ft.Control],
                                [
                                    ft.Text(
                                        "New Journey or Explore?",
                                        size=15,
                                        weight=ft.FontWeight.BOLD,
                                        color=TEXT_PRIMARY,
                                    ),
                                    ft.Text(
                                        (
                                            "Choose a different starter here "
                                            "when you want to begin a new "
                                            "Journey or temporarily Explore "
                                            "another starter path."
                                        ),
                                        size=13,
                                        color=TEXT_SECONDARY,
                                    ),
                                    ft.Text(
                                        (
                                            "Explore changes only the Battle "
                                            "Compass matchup filter. Starting "
                                            "a new Journey returns you to the "
                                            "Welcome screen and lets you reset "
                                            "the app for a new playthrough."
                                        ),
                                        size=13,
                                        color=TEXT_MUTED,
                                    ),
                                ],
                            ),
                            spacing=8,
                        ),
                        width=292,
                        padding=12,
                        bgcolor=SURFACE,
                        border_radius=10,
                    ),
                ),
            ],
        )

        return ft.Container(
            content=ft.Row(
                controls=cast(
                    list[ft.Control],
                    [
                        ft.Container(
                            content=self.starter_dropdown,
                            expand=True,
                        ),
                        help_popup,
                    ],
                ),
                spacing=4,
                vertical_alignment=ft.CrossAxisAlignment.CENTER,
            ),
            col={
                "xs": 12,
                "md": 4,
            },
        )

    @staticmethod
    def _dropdown_options(
        values: list[str],
    ) -> list[ft.DropdownOption]:
        return [
            ft.DropdownOption(
                key=value,
                text=value,
            )
            for value in values
        ]

    def _initialize_selections(self) -> None:
        """Restore saved selections, falling back when necessary."""

        self._refresh_starter_filter()

        trainer_names = self._trainer_names()

        if self.selected_trainer not in trainer_names:
            self._select_first_trainer()

        battle_names = self._battle_names()

        if self.selected_battle not in battle_names:
            self._select_first_battle()

        self._refresh_battle_opponents()

        opponent_names = [
            row["Pokemon"]
            for row in self.battle_opponents
            if row.get("Pokemon")
        ]

        if (
            self.selected_opponent_name
            not in opponent_names
        ):
            self._select_first_opponent()

        self._sync_dropdowns()

    def _refresh_starter_filter(self) -> None:
        self.filtered_opponents = [
            row
            for row in self.opponents
            if self._row_matches_starter(
                row,
                self.selected_starter,
            )
        ]

    @staticmethod
    def _row_matches_starter(
        row: dict,
        selected_starter: str,
    ) -> bool:
        player_starter = row.get("PlayerStarter")

        return (
            not player_starter
            or player_starter == selected_starter
        )

    def _trainer_names(self) -> list[str]:
        return sorted(
            {
                row["Trainer"]
                for row in self.filtered_opponents
                if row.get("Trainer")
            }
        )

    def _battle_names(self) -> list[str]:
        trainer_rows = [
            row
            for row in self.filtered_opponents
            if row.get("Trainer")
            == self.selected_trainer
        ]

        battle_order_lookup: dict[str, int] = {}

        for row in trainer_rows:
            battle_name = row.get("Battle")

            if not battle_name:
                continue

            battle_order = row.get(
                "BattleOrder",
                9999,
            )

            if not isinstance(
                battle_order,
                int,
            ):
                battle_order = 9999

            if battle_name not in battle_order_lookup:
                battle_order_lookup[
                    battle_name
                ] = battle_order
            else:
                battle_order_lookup[
                    battle_name
                ] = min(
                    battle_order_lookup[
                        battle_name
                    ],
                    battle_order,
                )

        return sorted(
            battle_order_lookup,
            key=lambda battle_name: (
                battle_order_lookup[
                    battle_name
                ],
                battle_name,
            ),
        )

    def _refresh_battle_opponents(self) -> None:
        matching_opponents = [
            row
            for row in self.filtered_opponents
            if (
                row.get("Trainer")
                == self.selected_trainer
                and row.get("Battle")
                == self.selected_battle
            )
        ]

        def slot_sort_key(
            row: dict,
        ) -> int:
            slot = row.get("Slot")

            if isinstance(slot, int):
                return slot

            return 9999

        self.battle_opponents = sorted(
            matching_opponents,
            key=slot_sort_key,
        )

    def _select_first_trainer(self) -> None:
        trainers = self._trainer_names()

        if not trainers:
            raise RuntimeError(
                "No trainers are available "
                "for the selected starter."
            )

        self.selected_trainer = trainers[0]

    def _select_first_battle(self) -> None:
        battles = self._battle_names()

        if not battles:
            raise RuntimeError(
                "No battles are available "
                "for the selected trainer."
            )

        self.selected_battle = battles[0]

    def _select_first_opponent(self) -> None:
        self._refresh_battle_opponents()

        if not self.battle_opponents:
            raise RuntimeError(
                "No opponents are available "
                "for the selected battle."
            )

        self.selected_opponent_name = (
            self.battle_opponents[0][
                "Pokemon"
            ]
        )

    def _sync_dropdowns(self) -> None:
        trainer_names = self._trainer_names()
        battle_names = self._battle_names()

        opponent_names = [
            row["Pokemon"]
            for row in self.battle_opponents
            if row.get("Pokemon")
        ]

        self.starter_dropdown.value = (
            self.selected_starter
        )

        self.trainer_dropdown.options = (
            self._dropdown_options(
                trainer_names
            )
        )
        self.trainer_dropdown.value = (
            self.selected_trainer
        )

        self.battle_dropdown.options = (
            self._dropdown_options(
                battle_names
            )
        )
        self.battle_dropdown.value = (
            self.selected_battle
        )

        self.opponent_dropdown.options = (
            self._dropdown_options(
                opponent_names
            )
        )
        self.opponent_dropdown.value = (
            self.selected_opponent_name
        )

    def _selected_opponent(self) -> dict:
        return next(
            row
            for row in self.battle_opponents
            if (
                row.get("Pokemon")
                == self.selected_opponent_name
            )
        )

    def _handle_starter_change(
        self,
        event: ft.Event[ft.Dropdown],
    ) -> None:
        """Handle a Battle Settings starter selection."""

        requested_starter = event.control.value

        if (
            requested_starter
            not in STARTER_OPTIONS
        ):
            self._sync_dropdowns()
            self.page.update()
            return

        if (
            requested_starter
            == self.selected_starter
        ):
            return

        if (
            requested_starter
            == self.journey_starter
        ):
            self._apply_starter_selection(
                requested_starter
            )
            return

        self.pending_starter = (
            requested_starter
        )

        # Keep the visible dropdown on the currently active
        # selection until the player chooses an action.
        self.starter_dropdown.value = (
            self.selected_starter
        )
        self.page.update()

        self.page.show_dialog(
            self._build_starter_change_dialog(
                requested_starter
            )
        )

    def _build_starter_change_dialog(
        self,
        requested_starter: str,
    ) -> ft.AlertDialog:
        """Build the Explore / New Journey decision dialog."""

        return ft.AlertDialog(
            modal=True,
            title=ft.Text(
                "A second starter?",
                color=TEXT_PRIMARY,
                weight=ft.FontWeight.BOLD,
            ),
            content=ft.Column(
                controls=cast(
                    list[ft.Control],
                    [
                        ft.Text(
                            (
                                f"Wow, {requested_starter} too? "
                                "Are you exploring another path, "
                                "or thinking of beginning a new "
                                "Journey?"
                            ),
                            color=TEXT_SECONDARY,
                            size=15,
                        ),
                        ft.Text(
                            (
                                "Exploring changes only the Battle "
                                "Compass matchup filter. Your saved "
                                "Journey and team will stay exactly "
                                "as they are."
                            ),
                            color=TEXT_MUTED,
                            size=13,
                        ),
                        ft.Text(
                            (
                                "Starting a new Journey opens the "
                                "Welcome screen. Your current Journey "
                                "will remain safe unless you finish "
                                "onboarding and click Prepare My "
                                "Journey."
                            ),
                            color=TEXT_MUTED,
                            size=13,
                        ),
                    ],
                ),
                spacing=12,
                tight=True,
            ),
            actions=cast(
                list[ft.Control],
                [
                    ft.Button(
                        content="Cancel",
                        on_click=(
                            self._cancel_starter_change
                        ),
                    ),
                    ft.Button(
                        content="Just Exploring",
                        icon=ft.Icons.EXPLORE_OUTLINED,
                        on_click=(
                            self._explore_pending_starter
                        ),
                    ),
                    ft.Button(
                        content="Start a New Journey",
                        icon=ft.Icons.RESTART_ALT_ROUNDED,
                        bgcolor=PRIMARY_BLUE,
                        color=TEXT_PRIMARY,
                        icon_color=TEXT_PRIMARY,
                        on_click=(
                            self._start_new_journey
                        ),
                    ),
                ],
            ),
            actions_alignment=(
                ft.MainAxisAlignment.END
            ),
        )

    def _cancel_starter_change(
        self,
        event: ft.Event[ft.Button],
    ) -> None:
        """Cancel the pending starter change."""

        del event

        self.pending_starter = None
        self.page.pop_dialog()

        self._sync_dropdowns()
        self.page.update()

    def _explore_pending_starter(
        self,
        event: ft.Event[ft.Button],
    ) -> None:
        """Apply the alternate starter only to Battle Settings."""

        del event

        requested_starter = (
            self.pending_starter
        )
        self.pending_starter = None

        self.page.pop_dialog()

        if (
            requested_starter
            in STARTER_OPTIONS
        ):
            self._apply_starter_selection(
                requested_starter
            )
            return

        self._sync_dropdowns()
        self.page.update()

    def _start_new_journey(
        self,
        event: ft.Event[ft.Button],
    ) -> None:
        """Open onboarding without changing persistent Journey data."""

        del event

        self.pending_starter = None
        self.page.pop_dialog()

        if self.on_start_new_journey is None:
            self._sync_dropdowns()
            self.page.update()
            return

        self.on_start_new_journey()

    def _apply_starter_selection(
        self,
        starter_name: str,
    ) -> None:
        """Apply a starter to the current Battle Compass session."""

        self.selected_starter = starter_name

        self._refresh_starter_filter()
        self._select_first_trainer()
        self._select_first_battle()
        self._select_first_opponent()
        self._sync_dropdowns()
        self._refresh_results()

        self.page.update()

    async def _save_selection(self) -> None:
        """Persist the active Battle Compass dropdown chain."""

        await (
            self.app_state
            .save_battle_compass_selection(
                trainer=self.selected_trainer,
                battle=self.selected_battle,
                opponent=(
                    self.selected_opponent_name
                ),
            )
        )

    async def _handle_trainer_change(
        self,
        event: ft.Event[ft.Dropdown],
    ) -> None:
        if event.control.value:
            self.selected_trainer = (
                event.control.value
            )

        self._select_first_battle()
        self._select_first_opponent()
        self._sync_dropdowns()
        self._refresh_results()

        await self._save_selection()

        self.page.update()

    async def _handle_battle_change(
        self,
        event: ft.Event[ft.Dropdown],
    ) -> None:
        if event.control.value:
            self.selected_battle = (
                event.control.value
            )

        self._select_first_opponent()
        self._sync_dropdowns()
        self._refresh_results()

        await self._save_selection()

        self.page.update()

    async def _handle_opponent_change(
        self,
        event: ft.Event[ft.Dropdown],
    ) -> None:
        if event.control.value:
            self.selected_opponent_name = (
                event.control.value
            )

        self._refresh_results()

        await self._save_selection()

        self.page.update()

    def _refresh_results(self) -> None:
        view_model = (
            build_battle_compass_view_model(
                team_data=self.team_data,
                opponent=(
                    self._selected_opponent()
                ),
                items=self.items,
                ability_rules=(
                    self.ability_rules
                ),
                moves_data=self.moves_data,
            )
        )

        if view_model.recommendation is None:
            self.results_host.content = (
                self._build_no_recommendation_state(
                    view_model.empty_state_message
                )
            )
            return

        self.results_host.content = (
            self._build_results(
                view_model
            )
        )

    @staticmethod
    def _build_no_recommendation_state(
        message: str | None,
    ) -> ft.Control:
        """Build a friendly empty state when no damaging move is available."""

        return ft.Container(
            content=ft.Column(
                controls=cast(
                    list[ft.Control],
                    [
                        ft.Icon(
                            ft.Icons.INFO_OUTLINE_ROUNDED,
                            size=34,
                            color=PRIMARY_BLUE,
                        ),
                        ft.Text(
                            "No Battle Recommendation Yet",
                            size=22,
                            weight=ft.FontWeight.BOLD,
                            color=TEXT_PRIMARY,
                            text_align=ft.TextAlign.CENTER,
                        ),
                        ft.Text(
                            (
                                message
                                or (
                                    "Add at least one damaging move to "
                                    "your team, save it, and return here."
                                )
                            ),
                            size=15,
                            color=TEXT_SECONDARY,
                            text_align=ft.TextAlign.CENTER,
                        ),
                    ],
                ),
                spacing=12,
                horizontal_alignment=(
                    ft.CrossAxisAlignment.CENTER
                ),
            ),
            width=940,
            padding=28,
            bgcolor=SURFACE,
            border=ft.Border.all(
                1,
                BORDER_DEFAULT,
            ),
            border_radius=16,
            alignment=ft.Alignment.CENTER,
        )

    def _build_results(
        self,
        view_model: BattleCompassViewModel,
    ) -> ft.Control:
        recommendation = (
            view_model.recommendation
        )

        if recommendation is None:
            return self._build_no_recommendation_state(
                view_model.empty_state_message
            )

        opponent = view_model.opponent

        recommendation_card = (
            RecommendationCard(
                pokemon_name=(
                    recommendation.pokemon[
                        "Pokemon"
                    ]
                ),
                gender_symbol=(
                    self._gender_symbol(
                        recommendation.pokemon.get(
                            "Gender"
                        )
                    )
                ),
                artwork_src=(
                    self._pokemon_asset(
                        recommendation.pokemon[
                            "Pokemon"
                        ],
                        gender=(
                            recommendation.pokemon.get(
                                "Gender"
                            )
                        ),
                        use_texture=True,
                    )
                ),
                type_badges=(
                    self._pokemon_type_badges(
                        recommendation.pokemon
                    )
                ),
                best_move=(
                    recommendation.best_move[
                        "Move"
                    ]
                ),
                best_move_type=str(
                    recommendation.best_move.get(
                        "Type"
                    )
                    or "Unknown"
                ),
                best_move_type_badge_src=(
                    self._type_badge_asset(
                        recommendation.best_move.get(
                            "Type"
                        )
                    )
                ),
                effectiveness_label=(
                    get_effectiveness_label(
                        (
                            recommendation
                            .best_move_type_multiplier
                        ),
                        mode="offense",
                    )
                ),
                effectiveness_color=(
                    self._effectiveness_color(
                        (
                            recommendation
                            .best_move_type_multiplier
                        ),
                        mode="offense",
                    )
                ),
                move_score=(
                    recommendation.best_move_score
                ),
                item_boosted=(
                    recommendation.item_boosted
                ),
                held_item=(
                    recommendation.held_item
                ),
                item_multiplier=(
                    recommendation.item_multiplier
                ),
                base_move_score=(
                    recommendation.base_move_score
                ),
                item_bonus_amount=(
                    recommendation.item_bonus_amount
                ),
                matchup_label=(
                    recommendation.matchup_label
                ),
                matchup_ratio=(
                    recommendation.ratio
                ),
                matchup_level=(
                    recommendation.matchup_level
                ),
                why_text=view_model.why_text,
                battle_notes=[
                    (
                        note.icon,
                        note.text,
                        self._note_style(
                            note.category
                        ),
                    )
                    for note
                    in recommendation.battle_notes
                ],
                on_full_analysis_click=(
                    self._scroll_to_full_analysis
                ),
                on_type_badge_click=(
                    self._show_type_matchups
                ),
                on_move_type_badge_click=(
                    self._show_offensive_type_matchups
                ),
            )
        )

        worst_move_type = (
            recommendation.worst_move.get(
                "Type"
            )
        )

        has_trainer = (
            self.selected_trainer.strip()
            != str(
                opponent.get("Pokemon")
                or ""
            ).strip()
        )

        opponent_moves: list[dict] = []

        for slot in range(1, 5):
            move_name = opponent.get(
                f"Move{slot}"
            )

            if (
                not isinstance(move_name, str)
                or not move_name
            ):
                continue

            move = dict(
                self.move_lookup.get(
                    move_name,
                    {},
                )
            )

            move["Move"] = move_name
            move["Type"] = opponent.get(
                f"Move{slot}Type"
            )
            move["Category"] = opponent.get(
                f"Move{slot}Category"
            )
            move["Power"] = opponent.get(
                f"Move{slot}Power"
            )
            move["Accuracy"] = opponent.get(
                f"Move{slot}Accuracy"
            )
            move["BadgeSrc"] = (
                self._type_badge_asset(
                    move.get("Type")
                )
            )

            opponent_moves.append(
                move
            )

        opponent_card = OpponentCard(
            page=self.page,
            trainer_name=(
                self._display_trainer_name(
                    self.selected_trainer
                )
                if has_trainer
                else None
            ),
            trainer_artwork_src=(
                self._trainer_asset(
                    self.selected_trainer
                )
                if has_trainer
                else None
            ),
            pokemon_name=opponent["Pokemon"],
            artwork_src=self._pokemon_asset(
                opponent["Pokemon"],
                use_gmax=(
                    opponent_uses_gmax(
                        opponent
                    )
                ),
                use_texture=True,
            ),
            level=opponent.get("Level"),
            type_badges=(
                self._pokemon_type_badges(
                    opponent
                )
            ),
            opponent_moves=opponent_moves,
            ability_name=opponent.get("Ability"),
            ability_descriptions=self.ability_descriptions,
            ability_rules=self.ability_rules,
            incoming_worst_score=(
                recommendation
                .incoming_worst_score
            ),
            worst_incoming_move=(
                recommendation.worst_move[
                    "Move"
                ]
            ),
            incoming_category=(
                recommendation.worst_move.get(
                    "Category",
                    "Unknown",
                )
            ),
            incoming_move_type=str(
                worst_move_type or "Unknown"
            ),
            incoming_type_badge_src=(
                self._type_badge_asset(
                    worst_move_type
                )
            ),
            defensive_effectiveness_label=(
                get_effectiveness_label(
                    (
                        recommendation
                        .incoming_type_multiplier
                    ),
                    mode="defense",
                )
            ),
            defensive_effectiveness_color=(
                self._effectiveness_color(
                    (
                        recommendation
                        .incoming_type_multiplier
                    ),
                    mode="defense",
                )
            ),
            defensive_effectiveness_background=(
                self._effectiveness_background(
                    (
                        recommendation
                        .incoming_type_multiplier
                    ),
                    mode="defense",
                )
            ),
            on_type_badge_click=(
                self._show_type_matchups
            ),
            on_move_type_badge_click=(
                self._show_offensive_type_matchups
            ),
        )

        other_options = OtherStrongOptions(
            options=[
                self._build_strong_option(
                    matchup,
                    rank=index,
                )
                for index, matchup in enumerate(
                    view_model.other_options,
                    start=1,
                )
            ],
            on_type_badge_click=(
                self._show_type_matchups
            ),
            on_move_type_badge_click=(
                self._show_offensive_type_matchups
            ),
        )

        full_analysis = FullAnalysis(
            matchups=view_model.all_matchups,
        )

        return ft.Column(
            controls=cast(
                list[ft.Control],
                [
                    ft.ResponsiveRow(
                        controls=[
                            ft.Container(
                                content=recommendation_card,
                                col={
                                    "xs": 12,
                                    "xl": 6,
                                },
                            ),
                            ft.Container(
                                content=opponent_card,
                                col={
                                    "xs": 12,
                                    "xl": 6,
                                },
                            ),
                        ],
                        columns=12,
                        spacing=20,
                        run_spacing=20,
                        vertical_alignment=ft.CrossAxisAlignment.START,
                    ),
                    other_options,
                    full_analysis,
                ],
            ),
    spacing=28,
    horizontal_alignment=ft.CrossAxisAlignment.CENTER,
)

    def _show_type_matchups(
        self,
        pokemon_type: str,
    ) -> None:
        """Show defensive single-type matchup information."""

        show_type_matchup_dialog(
            page=self.page,
            pokemon_type=pokemon_type,
            type_chart=self.type_chart,
        )

    def _show_offensive_type_matchups(
        self,
        move_type: str,
    ) -> None:
        """Show offensive single-type matchup information."""

        show_type_matchup_dialog(
            page=self.page,
            pokemon_type=move_type,
            type_chart=self.type_chart,
            mode="offensive",
        )

    async def _scroll_to_full_analysis(
        self,
        event: ft.Event[ft.Button],
    ) -> None:
        """Scroll smoothly to the Full Analysis section."""

        del event

        await self.page.scroll_to(
            scroll_key=FULL_ANALYSIS_SCROLL_KEY,
            duration=600,
            curve=ft.AnimationCurve.EASE_IN_OUT,
        )

    def _build_strong_option(
        self,
        matchup: MatchupViewModel,
        *,
        rank: int,
    ) -> StrongOptionData:
        pokemon = matchup.pokemon

        return StrongOptionData(
            rank=rank,
            pokemon_name=pokemon["Pokemon"],
            sprite_src=self._pokemon_asset(
                pokemon["Pokemon"],
                gender=pokemon.get("Gender"),
                use_texture=False,
            ),
            type_badges=(
                self._pokemon_type_badges(
                    pokemon
                )
            ),
            matchup_label=(
                matchup.matchup_label
            ),
            matchup_ratio=matchup.ratio,
            best_move=(
                matchup.best_move["Move"]
            ),
            best_move_type=str(
                matchup.best_move.get("Type")
                or "Unknown"
            ),
            best_move_type_badge_src=(
                self._type_badge_asset(
                    matchup.best_move.get(
                        "Type"
                    )
                )
            ),
            notes=[
                StrongOptionNote(
                    icon=note.icon,
                    text=note.text,
                    category=self._note_style(
                        note.category
                    ),
                )
                for note
                in matchup.battle_notes
            ],
        )

    def _pokemon_type_badges(
        self,
        pokemon: dict,
    ) -> list[tuple[str, str]]:
        types = [
            pokemon.get("Type1"),
            pokemon.get("Type2"),
        ]

        return [
            (
                pokemon_type,
                self._type_badge_asset(
                    pokemon_type
                ),
            )
            for pokemon_type in types
            if (
                isinstance(
                    pokemon_type,
                    str,
                )
                and pokemon_type
            )
        ]

    def _pokemon_asset(
        self,
        pokemon_name: str,
        *,
        gender: str | None = None,
        use_gmax: bool = False,
        use_texture: bool,
    ) -> str:
        asset_path = get_sprite_path(
            pokemon_name,
            gender=gender,
            use_gmax=use_gmax,
            use_texture=use_texture,
        )

        if asset_path is None:
            raise FileNotFoundError(
                "No sprite asset found for "
                f"{pokemon_name}."
            )

        return self._asset_src(
            asset_path
        )

    def _trainer_asset(
        self,
        trainer_name: str,
    ) -> str:
        """Return the trainer texture for the selected opponent."""

        normalized_name = trainer_name.strip()

        if normalized_name.startswith("BT "):
            filename = "bt-texture.png"
        elif normalized_name == "HT Sebastian":
            filename = "ht-sebastian-texture.png"
        elif normalized_name in {
            "HT Aria",
            "HT Camilla",
        }:
            filename = (
                "ht-aria-camilla-texture.png"
            )
        else:
            trainer_slug = (
                normalized_name
                .lower()
                .replace(" ", "-")
            )
            filename = (
                f"{trainer_slug}-texture.png"
            )

        trainer_path = (
            TRAINER_TEXTURE_DIR
            / filename
        )

        if not trainer_path.exists():
            raise FileNotFoundError(
                "No trainer texture found for "
                f"{trainer_name}: {trainer_path}"
            )

        return self._asset_src(
            trainer_path
        )

    @staticmethod
    def _display_trainer_name(
        trainer_name: str,
    ) -> str:
        """Remove stadium-trainer prefixes from the displayed name."""

        normalized_name = trainer_name.strip()

        if normalized_name.startswith(
            ("BT ", "HT ")
        ):
            return normalized_name[3:]

        return normalized_name

    def _type_badge_asset(
        self,
        pokemon_type: object,
    ) -> str:
        if (
            not isinstance(
                pokemon_type,
                str,
            )
            or not pokemon_type
        ):
            raise ValueError(
                "Move or Pokémon type is missing."
            )

        return self._asset_src(
            ASSETS_DIR
            / "type_badges"
            / f"{pokemon_type}.png"
        )

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

    @staticmethod
    def _gender_symbol(
        gender: object,
    ) -> str | None:
        if not isinstance(gender, str):
            return None

        normalized_gender = (
            gender.strip().lower()
        )

        if normalized_gender == "male":
            return "♂︎"

        if normalized_gender == "female":
            return "♀︎"

        return None

    @staticmethod
    def _note_style(
        category: str,
    ) -> str:
        styles = {
            "info": "info",
            "opportunity": "info",
            "caution": "warning",
            "warning": "warning",
        }

        return styles.get(
            category,
            "info",
        )

    @staticmethod
    def _effectiveness_color(
        multiplier: float,
        *,
        mode: str,
    ) -> str:
        if mode == "offense":
            if multiplier > 1:
                return "#7EE2A1"

            if multiplier == 1:
                return "#D1D5DB"

            if multiplier == 0:
                return "#F87171"

            return "#FACC15"

        if multiplier < 1:
            return "#4ADE80"

        if multiplier == 1:
            return "#D1D5DB"

        if multiplier < 4:
            return "#FACC15"

        return "#F87171"

    @staticmethod
    def _effectiveness_background(
        multiplier: float,
        *,
        mode: str,
    ) -> str:
        if mode == "defense":
            if multiplier < 1:
                return "#174B35"

            if multiplier == 1:
                return "#303640"

            if multiplier < 4:
                return "#4A3A17"

            return "#4B2025"

        return "#182A24"