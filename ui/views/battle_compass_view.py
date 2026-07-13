"""
Battle Compass primary view.

Manages battle-selection controls, calls the existing engine through the
Battle Compass ViewModel, and renders live recommendation components.
"""

from __future__ import annotations

from pathlib import Path
from typing import cast

import flet as ft

from ui.components.opponent_card import OpponentCard
from ui.components.other_strong_options import (
    OtherStrongOptions,
    StrongOptionData,
    StrongOptionNote,
)
from ui.components.recommendation_card import RecommendationCard
from ui.rendering import (
    get_sprite_path,
    opponent_uses_gmax,
)
from ui.theme import (
    BORDER_DEFAULT,
    CONTENT_MAX_WIDTH,
    PRIMARY_BLUE,
    SURFACE,
    TEXT_PRIMARY,
)
from ui.viewmodels.battle_compass_vm import (
    BattleCompassViewModel,
    MatchupViewModel,
    build_battle_compass_view_model,
    get_effectiveness_label,
    load_reference_data,
)


PROJECT_ROOT = Path(__file__).resolve().parents[2]
ASSETS_DIR = PROJECT_ROOT / "assets"

STARTER_OPTIONS = [
    "Grookey",
    "Scorbunny",
    "Sobble",
]


class BattleCompassView:
    """Interactive Battle Compass view backed by the existing engine."""

    def __init__(self, page: ft.Page) -> None:
        self.page = page

        reference_data = load_reference_data()

        self.team_data = reference_data["team_data"]
        self.opponents = reference_data["opponents"]
        self.items = reference_data["items"]
        self.ability_rules = reference_data["ability_rules"]
        self.moves_data = reference_data["moves_data"]

        self.selected_starter = STARTER_OPTIONS[0]
        self.selected_trainer = ""
        self.selected_battle = ""
        self.selected_opponent_name = ""

        self.filtered_opponents: list[dict] = []
        self.battle_opponents: list[dict] = []

        self.starter_dropdown = ft.Dropdown(
            label="Your Starter",
            value=self.selected_starter,
            options=self._dropdown_options(STARTER_OPTIONS),
            on_select=self._handle_starter_change,
            col={
                "xs": 12,
                "md": 4,
            },
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
                                    self.starter_dropdown,
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
        self._refresh_starter_filter()
        self._select_first_trainer()
        self._select_first_battle()
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
            if row.get("Trainer") == self.selected_trainer
        ]

        battle_order_lookup: dict[str, int] = {}

        for row in trainer_rows:
            battle_name = row.get("Battle")

            if not battle_name:
                continue

            battle_order = row.get("BattleOrder", 9999)

            if not isinstance(battle_order, int):
                battle_order = 9999

            if battle_name not in battle_order_lookup:
                battle_order_lookup[battle_name] = battle_order
            else:
                battle_order_lookup[battle_name] = min(
                    battle_order_lookup[battle_name],
                    battle_order,
                )

        return sorted(
            battle_order_lookup,
            key=lambda battle_name: (
                battle_order_lookup[battle_name],
                battle_name,
            ),
        )

    def _refresh_battle_opponents(self) -> None:
        matching_opponents = [
            row
            for row in self.filtered_opponents
            if (
                row.get("Trainer") == self.selected_trainer
                and row.get("Battle") == self.selected_battle
            )
        ]

        def slot_sort_key(row: dict) -> int:
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
                "No trainers are available for the selected starter."
            )

        self.selected_trainer = trainers[0]

    def _select_first_battle(self) -> None:
        battles = self._battle_names()

        if not battles:
            raise RuntimeError(
                "No battles are available for the selected trainer."
            )

        self.selected_battle = battles[0]

    def _select_first_opponent(self) -> None:
        self._refresh_battle_opponents()

        if not self.battle_opponents:
            raise RuntimeError(
                "No opponents are available for the selected battle."
            )

        self.selected_opponent_name = self.battle_opponents[0]["Pokemon"]

    def _sync_dropdowns(self) -> None:
        trainer_names = self._trainer_names()
        battle_names = self._battle_names()
        opponent_names = [
            row["Pokemon"]
            for row in self.battle_opponents
            if row.get("Pokemon")
        ]

        self.starter_dropdown.value = self.selected_starter

        self.trainer_dropdown.options = self._dropdown_options(
            trainer_names
        )
        self.trainer_dropdown.value = self.selected_trainer

        self.battle_dropdown.options = self._dropdown_options(
            battle_names
        )
        self.battle_dropdown.value = self.selected_battle

        self.opponent_dropdown.options = self._dropdown_options(
            opponent_names
        )
        self.opponent_dropdown.value = self.selected_opponent_name

    def _selected_opponent(self) -> dict:
        return next(
            row
            for row in self.battle_opponents
            if row.get("Pokemon") == self.selected_opponent_name
        )

    def _handle_starter_change(
        self,
        event: ft.Event[ft.Dropdown],
    ) -> None:
        self.selected_starter = (
            event.control.value or STARTER_OPTIONS[0]
        )

        self._refresh_starter_filter()
        self._select_first_trainer()
        self._select_first_battle()
        self._select_first_opponent()
        self._sync_dropdowns()
        self._refresh_results()
        self.page.update()

    def _handle_trainer_change(
        self,
        event: ft.Event[ft.Dropdown],
    ) -> None:
        if event.control.value:
            self.selected_trainer = event.control.value

        self._select_first_battle()
        self._select_first_opponent()
        self._sync_dropdowns()
        self._refresh_results()
        self.page.update()

    def _handle_battle_change(
        self,
        event: ft.Event[ft.Dropdown],
    ) -> None:
        if event.control.value:
            self.selected_battle = event.control.value

        self._select_first_opponent()
        self._sync_dropdowns()
        self._refresh_results()
        self.page.update()

    def _handle_opponent_change(
        self,
        event: ft.Event[ft.Dropdown],
    ) -> None:
        if event.control.value:
            self.selected_opponent_name = event.control.value

        self._refresh_results()
        self.page.update()

    def _refresh_results(self) -> None:
        view_model = build_battle_compass_view_model(
            team_data=self.team_data,
            opponent=self._selected_opponent(),
            items=self.items,
            ability_rules=self.ability_rules,
            moves_data=self.moves_data,
        )

        self.results_host.content = self._build_results(
            view_model
        )

    def _build_results(
        self,
        view_model: BattleCompassViewModel,
    ) -> ft.Control:
        recommendation = view_model.recommendation
        opponent = view_model.opponent

        recommendation_card = RecommendationCard(
            pokemon_name=recommendation.pokemon["Pokemon"],
            gender_symbol=self._gender_symbol(
                recommendation.pokemon.get("Gender")
            ),
            artwork_src=self._pokemon_asset(
                recommendation.pokemon["Pokemon"],
                gender=recommendation.pokemon.get("Gender"),
                use_texture=True,
            ),
            type_badges=self._pokemon_type_badges(
                recommendation.pokemon
            ),
            best_move=recommendation.best_move["Move"],
            best_move_type_badge_src=self._type_badge_asset(
                recommendation.best_move.get("Type")
            ),
            effectiveness_label=get_effectiveness_label(
                recommendation.best_move_multiplier,
                mode="offense",
            ),
            effectiveness_color=self._effectiveness_color(
                recommendation.best_move_multiplier,
                mode="offense",
            ),
            move_score=recommendation.best_move_score,
            item_boosted=recommendation.item_boosted,
            held_item=recommendation.held_item,
            item_multiplier=recommendation.item_multiplier,
            base_move_score=recommendation.base_move_score,
            item_bonus_amount=recommendation.item_bonus_amount,
            matchup_label=recommendation.matchup_label,
            matchup_ratio=recommendation.ratio,
            matchup_level=recommendation.matchup_level,
            why_text=view_model.why_text,
            battle_notes=[
                (
                    note.icon,
                    note.text,
                    self._note_style(note.category),
                )
                for note in recommendation.battle_notes
            ],
        )

        worst_move_type = recommendation.worst_move.get("Type")

        opponent_card = OpponentCard(
            pokemon_name=opponent["Pokemon"],
            artwork_src=self._pokemon_asset(
                opponent["Pokemon"],
                use_gmax=opponent_uses_gmax(opponent),
                use_texture=True,
            ),
            level=opponent.get("Level"),
            type_badges=self._pokemon_type_badges(opponent),
            incoming_worst_score=(
                recommendation.incoming_worst_score
            ),
            worst_incoming_move=(
                recommendation.worst_move["Move"]
            ),
            incoming_category=(
                recommendation.worst_move.get(
                    "Category",
                    "Unknown",
                )
            ),
            incoming_type_badge_src=self._type_badge_asset(
                worst_move_type
            ),
            defensive_effectiveness_label=(
                get_effectiveness_label(
                    recommendation.incoming_multiplier,
                    mode="defense",
                )
            ),
            defensive_effectiveness_color=(
                self._effectiveness_color(
                    recommendation.incoming_multiplier,
                    mode="defense",
                )
            ),
            defensive_effectiveness_background=(
                self._effectiveness_background(
                    recommendation.incoming_multiplier,
                    mode="defense",
                )
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
        )

        return ft.Column(
            controls=cast(
                list[ft.Control],
                [
                    recommendation_card,
                    opponent_card,
                    other_options,
                ],
            ),
            spacing=28,
            horizontal_alignment=ft.CrossAxisAlignment.CENTER,
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
            type_badges=self._pokemon_type_badges(pokemon),
            matchup_label=matchup.matchup_label,
            matchup_ratio=matchup.ratio,
            best_move=matchup.best_move["Move"],
            best_move_type_badge_src=self._type_badge_asset(
                matchup.best_move.get("Type")
            ),
            notes=[
                StrongOptionNote(
                    icon=note.icon,
                    text=note.text,
                    category=self._note_style(note.category),
                )
                for note in matchup.battle_notes
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
                self._type_badge_asset(pokemon_type),
            )
            for pokemon_type in types
            if isinstance(pokemon_type, str) and pokemon_type
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
                f"No sprite asset found for {pokemon_name}."
            )

        return self._asset_src(asset_path)

    def _type_badge_asset(
        self,
        pokemon_type: object,
    ) -> str:
        if not isinstance(pokemon_type, str) or not pokemon_type:
            raise ValueError("Move or Pokémon type is missing.")

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

        normalized_gender = gender.strip().lower()

        if normalized_gender == "male":
            return "♂"

        if normalized_gender == "female":
            return "♀"

        return None

    @staticmethod
    def _note_style(category: str) -> str:
        styles = {
            "info": "info",
            "opportunity": "info",
            "caution": "warning",
            "warning": "warning",
        }

        return styles.get(category, "info")

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