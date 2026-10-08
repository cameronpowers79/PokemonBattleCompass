"""
Battle Compass primary view.
Manages battle-selection controls, calls the existing engine through the
Battle Compass ViewModel, and renders live recommendation components.
"""
from __future__ import annotations
from collections.abc import Callable
import json
from pathlib import Path
import re
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
from engine.mechanics import get_effective_pokemon_types
from engine.learnsets import supported_strategy_move_methods
from engine.strategy_capabilities import (
    evaluate_strategy_recommendations,
    evaluate_strategy_viability,
    recognize_team_capabilities,
    recommend_strategy_moves_for_added_pokemon,
    strategy_move_guidance,
)
from engine.strategy_definitions import (
    RECOMMENDER_STRATEGY_IDS,
    get_strategy_definition,
)
from ui.components.reference_dialogs import (
    show_type_matchup_dialog,
)
from ui.rendering import (
    asset_exists,
    get_sprite_path,
    opponent_uses_gmax,
)
from ui.theme import (
    BORDER_DEFAULT,
    CONTENT_MAX_WIDTH,
    PRIMARY_BLUE,
    SUCCESS,
    WARNING,
    SURFACE,
    SURFACE_RAISED,
    TEXT_MUTED,
    TEXT_PRIMARY,
    TEXT_SECONDARY,
    TEXT_SIZE_FEATURED_TITLE,
    TEXT_SIZE_CARD_TITLE,
    FONT_FAMILY_HEADER,
)
from ui.viewmodels.app_state import AppState
from ui.strategy_ui import (
    TEAM_STRATEGY_LABELS,
    strategy_color,
    strategy_compact_description,
    strategy_label,
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
DATA_DIR = PROJECT_ROOT / "data"
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
        self.on_strategy_updated: Callable[[str], None] | None = None
        self.on_journey_updated: Callable[[], None] | None = None
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
        self.learnsets_data = reference_data.get("learnsets_swsh", {})
        self.strategy_pokemon_catalog = self._load_strategy_json(
            DATA_DIR / "journey_pokemon.json"
        )
        self.strategy_item_catalog = self._load_strategy_json(
            DATA_DIR / "journey_items.json"
        )
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
        self.strategy_status = ft.Text(
            "",
            size=12,
            color=TEXT_MUTED,
            visible=False,
        )
        self.team_strategy_dropdown = ft.Dropdown(
            label="Team Strategy",
            value=self.app_state.team_strategy,
            options=self._team_strategy_options(),
            width=330,
            on_select=self._handle_team_strategy_change,
            text_style=ft.TextStyle(
                color=strategy_color(self.app_state.team_strategy),
                weight=ft.FontWeight.BOLD,
            ),
        )
        self.strategy_description_text = ft.Text(
            strategy_compact_description(self.app_state.team_strategy),
            size=13,
            color=TEXT_SECONDARY,
        )
        self.strategy_recommender_button = ft.IconButton(
            icon=ft.Icons.HELP_OUTLINE_ROUNDED,
            icon_color=SUCCESS,
            icon_size=28,
            tooltip="Which strategy fits this team?",
            on_click=self._show_strategy_recommender,
        )
        self.results_host = ft.Container(
            width=CONTENT_MAX_WIDTH,
        )
        self._initialize_selections()
        self._refresh_results()
    @staticmethod
    def _load_strategy_json(path: Path) -> list[dict]:
        """Load optional Journey catalog data used by the strategy recommender."""
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, UnicodeError, json.JSONDecodeError):
            return []
        return [record for record in data if isinstance(record, dict)] if isinstance(data, list) else []

    @staticmethod
    def _strategy_name_key(value: object) -> str:
        return " ".join(str(value or "").strip().casefold().split())

    def _strategy_catalog_record_for_name(self, pokemon_name: str) -> dict | None:
        """Resolve a recommendation name back to its Team Planner catalog row."""
        wanted = self._strategy_name_key(re.sub(r"\s+\((?:male|female)\)$", "", pokemon_name, flags=re.IGNORECASE))
        if not wanted:
            return None
        for record in self.strategy_pokemon_catalog:
            names = {
                self._strategy_name_key(record.get("pokemon")),
                self._strategy_name_key(record.get("acquire_as")),
            }
            for step in record.get("evolution_steps", []):
                if isinstance(step, dict):
                    names.add(self._strategy_name_key(step.get("from")))
                    names.add(self._strategy_name_key(step.get("to")))
            if wanted in names:
                return record
        return None

    def _strategy_candidate_record(self, catalog_record: dict) -> dict:
        """Adapt one Journey catalog row to the capability recognizer shape."""
        candidate = dict(catalog_record)
        candidate["Pokemon"] = str(
            catalog_record.get("pokemon")
            or catalog_record.get("Pokemon")
            or catalog_record.get("acquire_as")
            or ""
        ).strip()
        aliases = {
            "Ability": ("Ability", "ability"),
            "Type1": ("Type1", "type1", "primary_type"),
            "Type2": ("Type2", "type2", "secondary_type"),
            "Form": ("Form", "form"),
            "Gender": ("Gender", "gender"),
            "Nature": ("Nature", "nature"),
            "BaseSPE": ("BaseSPE", "BaseSpe", "BaseSpeed", "base_speed"),
        }
        for target, sources in aliases.items():
            for source in sources:
                value = catalog_record.get(source)
                if value not in (None, ""):
                    candidate[target] = value
                    break
        if not candidate.get("Ability"):
            abilities = catalog_record.get("abilities")
            if isinstance(abilities, list) and len(abilities) == 1:
                candidate["Ability"] = str(abilities[0])
        return candidate

    def _strategy_candidate_pokemon_data(self) -> list[dict]:
        """Return all Sword catalog final forms, regardless of earned badges."""
        earned_badges = self.app_state.earned_badges
        active_names = {
            self._strategy_name_key(pokemon.get("Pokemon"))
            for pokemon in self.team_data
            if isinstance(pokemon, dict) and pokemon.get("Pokemon")
        }
        candidates: list[dict] = []
        seen: set[str] = set()
        for record in self.strategy_pokemon_catalog:
            name = str(record.get("pokemon") or record.get("Pokemon") or "").strip()
            if not name:
                continue
            try:
                required_badge = int(record.get("required_badge", 0) or 0)
            except (TypeError, ValueError):
                required_badge = 0
            name_key = self._strategy_name_key(name)
            if name_key in active_names or name_key in seen:
                continue
            candidate = self._strategy_candidate_record(record)
            candidate["required_badge"] = required_badge
            candidate["_available_now"] = required_badge <= earned_badges
            if candidate.get("Pokemon"):
                # Only form-dependent species are expanded. A single Journey
                # objective still represents the species; recommendations
                # evaluate both learnsets and Ability eligibility separately.
                if name_key in {"meowstic", "indeedee"} and not candidate.get("Gender"):
                    for gender in ("Male", "Female"):
                        variant = dict(candidate, Gender=gender, _strategy_gender_variant=True)
                        candidates.append(variant)
                else:
                    candidates.append(candidate)
                seen.add(name_key)
        return candidates

    def _strategy_move_source_id(
        self,
        pokemon: dict,
        move_name: str,
    ) -> str | None:
        """Return a required TM/TR Journey item when no free supported method exists."""
        methods = supported_strategy_move_methods(
            pokemon,
            move_name,
            self.learnsets_data,
        )
        if not methods:
            return None
        if any(
            str(method.get("method") or "").casefold()
            not in {"tm", "tr"}
            and not method.get("item")
            for method in methods
        ):
            return None
        item_codes = [
            str(method.get("item") or "").strip().upper()
            for method in methods
            if str(method.get("item") or "").strip()
        ]
        if not item_codes:
            return None
        for item_code in item_codes:
            match = re.match(r"^(TM|TR)\s*0*(\d+)$", item_code, re.IGNORECASE)
            if match is None:
                continue
            kind, number = match.group(1).upper(), str(int(match.group(2)))
            for item in self.strategy_item_catalog:
                item_name = str(item.get("name") or "").strip()
                item_match = re.match(
                    r"^(TM|TR)\s*0*(\d+)\b",
                    item_name,
                    re.IGNORECASE,
                )
                if (
                    item_match is not None
                    and item_match.group(1).upper() == kind
                    and str(int(item_match.group(2))) == number
                ):
                    return str(item.get("id") or "").strip() or None
        return None

    @staticmethod
    def _strategy_viability_color(viability: str) -> str:
        if viability == "Strong":
            return SUCCESS
        if viability == "Viable":
            return PRIMARY_BLUE
        return WARNING

    def _strategy_analysis(self, strategy_key: str):
        return evaluate_strategy_recommendations(
            strategy_key,
            self.team_data,
            self._strategy_candidate_pokemon_data(),
            self.moves_data,
            self.learnsets_data,
            pokemon_limit=3,
            move_limit=5,
        )

    def _show_strategy_recommender(
        self,
        event: ft.Event[ft.IconButton] | None = None,
    ) -> None:
        """Compare canonical strategies against the current equipped team."""
        del event
        analyses = {
            key: self._strategy_analysis(key)
            for key in RECOMMENDER_STRATEGY_IDS
        }
        self._strategy_recommender_results = analyses

        cards: list[ft.Control] = []
        for strategy_key in RECOMMENDER_STRATEGY_IDS:
            definition = get_strategy_definition(strategy_key)
            analysis = analyses[strategy_key]
            viability = analysis.viability
            viability_color = self._strategy_viability_color(viability.viability)

            detail_controls: list[ft.Control] = [
                ft.Row(
                    controls=[
                        ft.Text(
                            definition.label,
                            size=18,
                            weight=ft.FontWeight.BOLD,
                            color=definition.color,
                            expand=True,
                        ),
                        ft.Container(
                            content=ft.Text(
                                viability.viability,
                                size=12,
                                weight=ft.FontWeight.BOLD,
                                color=viability_color,
                            ),
                            padding=ft.Padding.symmetric(horizontal=10, vertical=5),
                            border=ft.Border.all(1, viability_color),
                            border_radius=14,
                        ),
                    ],
                    vertical_alignment=ft.CrossAxisAlignment.CENTER,
                ),
                ft.Text(
                    definition.compact_description,
                    size=13,
                    color=TEXT_SECONDARY,
                ),
                ft.Text(
                    viability.summary,
                    size=13,
                    color=TEXT_PRIMARY,
                ),
            ]
            if viability.contributing_pokemon:
                detail_controls.append(
                    ft.Text(
                        "Current contributors: "
                        + ", ".join(viability.contributing_pokemon),
                        size=12,
                        color=TEXT_MUTED,
                    )
                )
            if analysis.one_change_away:
                detail_controls.append(
                    ft.Text(
                        "You are one supported change away from a viable version of this strategy.",
                        size=12,
                        color=SUCCESS,
                        weight=ft.FontWeight.W_600,
                    )
                )

            if viability.viability in {"Viable", "Strong"}:
                action = ft.Button(
                    content=(
                        "Selected Strategy"
                        if strategy_key == self.app_state.team_strategy
                        else "Use This Strategy"
                    ),
                    icon=(
                        ft.Icons.CHECK_CIRCLE_ROUNDED
                        if strategy_key == self.app_state.team_strategy
                        else ft.Icons.ARROW_FORWARD_ROUNDED
                    ),
                    disabled=strategy_key == self.app_state.team_strategy,
                    on_click=(
                        lambda e, key=strategy_key:
                        self._select_strategy_from_recommender(e, key)
                    ),
                )
            else:
                action = ft.Button(
                    content="Build toward this strategy",
                    icon=ft.Icons.EDIT_NOTE_ROUNDED,
                    on_click=(
                        lambda e, key=strategy_key:
                        self._show_strategy_build_options(e, key)
                    ),
                )
            detail_controls.append(action)

            cards.append(
                ft.Container(
                    content=ft.Column(
                        controls=detail_controls,
                        spacing=8,
                        tight=True,
                    ),
                    padding=16,
                    bgcolor=SURFACE_RAISED,
                    border=ft.Border.all(1, definition.color),
                    border_radius=12,
                )
            )

        cards.append(
            ft.Text(
                (
                    "Incomplete does not lock a strategy. Close this window and choose "
                    "any strategy directly from Team Strategy if you want to experiment "
                    "with the current team anyway."
                ),
                size=12,
                color=TEXT_MUTED,
                italic=True,
            )
        )

        self.page.show_dialog(
            ft.AlertDialog(
                modal=True,
                title=ft.Text(
                    "Strategy Recommender",
                    weight=ft.FontWeight.BOLD,
                    font_family=FONT_FAMILY_HEADER,
                    color=TEXT_PRIMARY,
                ),
                content=ft.Container(
                    content=ft.Column(
                        controls=[
                            ft.Text(
                                (
                                    "Battle Compass compares your currently equipped team "
                                    "against each strategy. Readiness is guidance, not a lock."
                                ),
                                size=14,
                                color=TEXT_SECONDARY,
                            ),
                            *cards,
                        ],
                        spacing=12,
                        scroll=ft.ScrollMode.AUTO,
                    ),
                    width=720,
                    height=590,
                ),
                actions=[
                    ft.Button(
                        content="Close",
                        on_click=lambda e: self.page.pop_dialog(),
                    )
                ],
                actions_alignment=ft.MainAxisAlignment.END,
            )
        )

    def _select_strategy_from_recommender(
        self,
        event: ft.Event[ft.Button],
        strategy_key: str,
    ) -> None:
        del event
        self.page.pop_dialog()
        self._apply_team_strategy_style(strategy_key)
        self.team_strategy_dropdown.disabled = True
        self.page.update()
        self.page.run_task(self._persist_team_strategy, strategy_key)

    def _show_strategy_build_options(
        self,
        event: ft.Event[ft.Button],
        strategy_key: str,
    ) -> None:
        """Show supported one-change paths for an incomplete strategy."""
        del event
        self.page.pop_dialog()
        analysis = getattr(self, "_strategy_recommender_results", {}).get(strategy_key)
        if analysis is None:
            analysis = self._strategy_analysis(strategy_key)
        definition = get_strategy_definition(strategy_key)

        controls: list[ft.Control] = [
            ft.Text(
                analysis.viability.summary,
                size=14,
                color=TEXT_SECONDARY,
            ),
        ]
        if analysis.viability.missing_required_roles:
            controls.append(
                ft.Text(
                    "Missing required roles: "
                    + ", ".join(analysis.viability.missing_required_roles),
                    size=13,
                    color=WARNING,
                    weight=ft.FontWeight.W_600,
                )
            )

        if analysis.pokemon_additions:
            controls.append(
                ft.Text(
                    "Recommended Pokémon",
                    size=16,
                    weight=ft.FontWeight.BOLD,
                    color=TEXT_PRIMARY,
                )
            )
            for candidate in analysis.pokemon_additions:
                controls.append(
                    self._build_strategy_recommendation_row(
                        candidate.summary,
                        "Plan this Pokémon",
                        lambda e, name=candidate.pokemon_name, key=strategy_key:
                        self._show_strategy_pokemon_plan(e, key, name),
                    )
                )

        if analysis.move_changes:
            controls.append(
                ft.Text(
                    "Recommended move changes",
                    size=16,
                    weight=ft.FontWeight.BOLD,
                    color=TEXT_PRIMARY,
                )
            )
            for candidate in analysis.move_changes:
                controls.append(
                    self._build_strategy_recommendation_row(
                        candidate.summary,
                        "Plan this move",
                        lambda e, rec=candidate, key=strategy_key:
                        self._show_strategy_move_plan(e, key, rec),
                    )
                )

        if not analysis.pokemon_additions and not analysis.move_changes:
            controls.append(
                ft.Text(
                    (
                        "No supported single Pokémon addition or move change currently "
                        "improves this strategy enough to recommend automatically."
                    ),
                    color=TEXT_MUTED,
                    italic=True,
                )
            )

        self.page.show_dialog(
            ft.AlertDialog(
                modal=True,
                title=ft.Text(
                    f"Build toward {definition.label}",
                    weight=ft.FontWeight.BOLD,
                    font_family=FONT_FAMILY_HEADER,
                    color=definition.color,
                ),
                content=ft.Container(
                    content=ft.Column(
                        controls=controls,
                        spacing=12,
                        scroll=ft.ScrollMode.AUTO,
                    ),
                    width=680,
                    height=520,
                ),
                actions=[
                    ft.Button(
                        content="Back",
                        on_click=lambda e: self._return_to_strategy_recommender(e),
                    ),
                    ft.Button(
                        content="Close",
                        on_click=lambda e: self.page.pop_dialog(),
                    ),
                ],
                actions_alignment=ft.MainAxisAlignment.END,
            )
        )

    @staticmethod
    def _build_strategy_recommendation_row(
        summary: str,
        button_text: str,
        on_click,
    ) -> ft.Control:
        return ft.Container(
            content=ft.Column(
                controls=[
                    ft.Text(summary, size=13, color=TEXT_SECONDARY),
                    ft.Button(
                        content=button_text,
                        icon=ft.Icons.ADD_ROUNDED,
                        on_click=on_click,
                    ),
                ],
                spacing=7,
                tight=True,
            ),
            padding=12,
            bgcolor=SURFACE_RAISED,
            border=ft.Border.all(1, BORDER_DEFAULT),
            border_radius=10,
        )

    def _return_to_strategy_recommender(
        self,
        event: ft.Event[ft.Button],
    ) -> None:
        del event
        self.page.pop_dialog()
        self._show_strategy_recommender()

    def _show_strategy_pokemon_plan(
        self,
        event: ft.Event[ft.Button],
        strategy_key: str,
        pokemon_name: str,
    ) -> None:
        """Continue Pokémon-first planning with strategy-relevant move suggestions."""
        del event
        self.page.pop_dialog()
        catalog_record = self._strategy_catalog_record_for_name(pokemon_name)
        if catalog_record is None:
            self._show_strategy_message(
                "That Pokémon could not be matched to the current Team Planner catalog."
            )
            return
        candidate = self._strategy_candidate_record(catalog_record)
        gender_match = re.search(r"\((Male|Female)\)$", pokemon_name, flags=re.IGNORECASE)
        if gender_match and self._strategy_name_key(candidate.get("Pokemon")) in {"meowstic", "indeedee"}:
            candidate["Gender"] = gender_match.group(1).title()
        current_capabilities = recognize_team_capabilities(
            self.team_data,
            self.moves_data,
        )
        suggested_moves = recommend_strategy_moves_for_added_pokemon(
            strategy_key,
            current_capabilities,
            candidate,
            self.moves_data,
            self.learnsets_data,
        )
        guidance = strategy_move_guidance(
            strategy_key, candidate, self.moves_data, self.learnsets_data
        )
        checkboxes = [ft.Checkbox(label=move_name, value=True) for move_name in suggested_moves]
        explanations = [
            ft.Text(f"{name}: {purpose}. How to learn: {method}.", size=12, color=TEXT_SECONDARY)
            for name, purpose, method in guidance
        ]
        definition = get_strategy_definition(strategy_key)
        move_section: list[ft.Control]
        if checkboxes:
            move_section = [
                ft.Text(
                    "Recommended moves to plan",
                    size=14,
                    weight=ft.FontWeight.BOLD,
                    color=TEXT_PRIMARY,
                ),
                *checkboxes,
                *explanations,
                ft.Text(
                    f"The remaining {4 - len(checkboxes)} move slot(s) are yours for coverage, utility, or team preferences.",
                    size=12, color=TEXT_MUTED,
                ),
            ]
        else:
            move_section = [
                ft.Text(
                    (
                        "This Pokémon improves the strategy package without requiring "
                        "a specific additional modeled move recommendation right now."
                    ),
                    size=13,
                    color=TEXT_MUTED,
                )
            ]

        self.page.show_dialog(
            ft.AlertDialog(
                modal=True,
                title=ft.Text(
                    f"Plan {pokemon_name}",
                    weight=ft.FontWeight.BOLD,
                    font_family=FONT_FAMILY_HEADER,
                    color=definition.color,
                ),
                content=ft.Container(
                    content=ft.Column(
                        controls=[
                            ft.Text(
                                (
                                    f"Add {pokemon_name} to Team Planner for "
                                    f"{definition.label}. You can keep or clear any "
                                    "suggested moves before confirming."
                                ),
                                color=TEXT_SECONDARY,
                            ),
                            *move_section,
                        ],
                        spacing=10,
                        scroll=ft.ScrollMode.AUTO,
                    ),
                    width=560,
                    height=330,
                ),
                actions=[
                    ft.Button(
                        content="Cancel",
                        on_click=lambda e: self.page.pop_dialog(),
                    ),
                    ft.Button(
                        content="Add to My Journey",
                        icon=ft.Icons.PLAYLIST_ADD_CHECK_ROUNDED,
                        bgcolor=PRIMARY_BLUE,
                        color=TEXT_PRIMARY,
                        icon_color=TEXT_PRIMARY,
                        on_click=lambda e, record=catalog_record, mon=candidate, boxes=checkboxes, key=strategy_key: self._confirm_strategy_pokemon_plan(
                            e, key, record, mon, boxes
                        ),
                    ),
                ],
                actions_alignment=ft.MainAxisAlignment.END,
            )
        )

    def _confirm_strategy_pokemon_plan(
        self,
        event: ft.Event[ft.Button],
        strategy_key: str,
        catalog_record: dict,
        pokemon: dict,
        checkboxes: list[ft.Checkbox],
    ) -> None:
        del event
        selected_moves = [
            str(box.label)
            for box in checkboxes
            if box.value is True and box.label
        ]
        move_slots = [
            {
                "move_name": move_name,
                "source_item_id": self._strategy_move_source_id(pokemon, move_name),
            }
            for move_name in selected_moves
        ]
        pokemon_id = str(catalog_record.get("id") or "").strip()
        self.page.pop_dialog()
        self.page.run_task(
            self._save_strategy_journey_plan,
            strategy_key,
            pokemon_id,
            move_slots,
        )

    def _show_strategy_move_plan(
        self,
        event: ft.Event[ft.Button],
        strategy_key: str,
        recommendation,
    ) -> None:
        """Confirm one recommended move change before writing it to Move Planner."""
        del event
        self.page.pop_dialog()
        catalog_record = self._strategy_catalog_record_for_name(
            recommendation.pokemon_name
        )
        if catalog_record is None:
            self._show_strategy_message(
                "That Pokémon could not be matched to the current Team Planner catalog."
            )
            return
        pokemon = next(
            (
                row for row in self.team_data
                if isinstance(row, dict)
                and self._strategy_name_key(row.get("Pokemon"))
                == self._strategy_name_key(recommendation.pokemon_name)
            ),
            self._strategy_candidate_record(catalog_record),
        )
        replacement_note = (
            f" It is intended to replace {recommendation.replace_move_name} on the live build."
            if recommendation.replace_move_name
            else ""
        )
        self.page.show_dialog(
            ft.AlertDialog(
                modal=True,
                title=ft.Text(
                    f"Plan {recommendation.move_name}",
                    weight=ft.FontWeight.BOLD,
                    font_family=FONT_FAMILY_HEADER,
                    color=get_strategy_definition(strategy_key).color,
                ),
                content=ft.Text(
                    (
                        f"Add {recommendation.move_name} to "
                        f"{recommendation.pokemon_name}'s Move Planner row."
                        f"{replacement_note} This does not change the currently "
                        "equipped move in My Team."
                    ),
                    color=TEXT_SECONDARY,
                ),
                actions=[
                    ft.Button(
                        content="Cancel",
                        on_click=lambda e: self.page.pop_dialog(),
                    ),
                    ft.Button(
                        content="Add to My Journey",
                        icon=ft.Icons.PLAYLIST_ADD_CHECK_ROUNDED,
                        bgcolor=PRIMARY_BLUE,
                        color=TEXT_PRIMARY,
                        icon_color=TEXT_PRIMARY,
                        on_click=lambda e, record=catalog_record, mon=pokemon, rec=recommendation, key=strategy_key: self._confirm_strategy_move_plan(
                            e, key, record, mon, rec
                        ),
                    ),
                ],
                actions_alignment=ft.MainAxisAlignment.END,
            )
        )

    def _confirm_strategy_move_plan(
        self,
        event: ft.Event[ft.Button],
        strategy_key: str,
        catalog_record: dict,
        pokemon: dict,
        recommendation,
    ) -> None:
        del event
        move_name = str(recommendation.move_name or "").strip()
        pokemon_id = str(catalog_record.get("id") or "").strip()
        moves = [{
            "move_name": move_name,
            "source_item_id": self._strategy_move_source_id(pokemon, move_name),
        }]
        self.page.pop_dialog()
        self.page.run_task(
            self._save_strategy_journey_plan,
            strategy_key,
            pokemon_id,
            moves,
        )

    async def _save_strategy_journey_plan(
        self,
        strategy_key: str,
        pokemon_id: str,
        moves: list[dict[str, str | None]],
    ) -> None:
        """Persist a confirmed strategy recommendation to My Journey."""
        try:
            saved = await self.app_state.add_strategy_plan_to_journey(
                pokemon_id=pokemon_id,
                moves=moves,
            )
        except (RuntimeError, ValueError) as error:
            self._show_strategy_message(
                f"The recommendation could not be added to My Journey: {error}"
            )
            return
        if not saved:
            self._show_strategy_message(
                "The recommendation could not be added to My Journey."
            )
            return
        if self.on_journey_updated is not None:
            self.on_journey_updated()
        definition = get_strategy_definition(strategy_key)
        self._show_strategy_message(
            f"Added to My Journey for {definition.label}."
        )

    def _show_strategy_message(self, message: str) -> None:
        self.page.show_dialog(
            ft.SnackBar(
                content=ft.Text(message),
            )
        )

    def refresh_team_data(
        self,
        team_data: list[dict],
    ) -> None:
        """Refresh recommendation results after the shared team is saved."""
        self.team_data = team_data
        self._refresh_results()
    @staticmethod
    def _team_strategy_options() -> list[ft.DropdownOption]:
        """Build color-coded Team Strategy options."""
        return [
            ft.DropdownOption(
                key=strategy,
                text=label,
                content=ft.Text(
                    label,
                    color=strategy_color(strategy),
                    weight=ft.FontWeight.BOLD,
                ),
            )
            for strategy, label in TEAM_STRATEGY_LABELS.items()
        ]

    def _apply_team_strategy_style(self, strategy: str) -> None:
        """Apply the shared strategy identity to the selector and explainer."""
        self.team_strategy_dropdown.value = strategy
        self.team_strategy_dropdown.text_style = ft.TextStyle(
            color=strategy_color(strategy),
            weight=ft.FontWeight.BOLD,
        )
        self.strategy_description_text.value = strategy_compact_description(strategy)

    def refresh_team_strategy(
        self,
        strategy: str | None = None,
    ) -> None:
        """Refresh the active strategy and recommendation results."""
        active_strategy = strategy or self.app_state.team_strategy
        self._apply_team_strategy_style(active_strategy)
        self.strategy_status.visible = False
        self.strategy_status.value = ""
        if hasattr(self, "results_host"):
            self._refresh_results()
        try:
            self.team_strategy_dropdown.update()
        except RuntimeError:
            pass

    def _handle_team_strategy_change(
        self,
        event: ft.Event[ft.Dropdown],
    ) -> None:
        """Persist a strategy selected from Battle Settings."""
        strategy = str(
            event.control.value or "strongest_matchup"
        )
        self._apply_team_strategy_style(strategy)
        self.team_strategy_dropdown.disabled = True
        self.strategy_status.visible = False
        self.page.update()
        self.page.run_task(
            self._persist_team_strategy,
            strategy,
        )

    async def _persist_team_strategy(
        self,
        strategy: str,
    ) -> None:
        """Save the strategy, then refresh all visible strategy surfaces."""
        previous_strategy = self.app_state.team_strategy
        try:
            save_succeeded = await self.app_state.save_team_strategy(
                strategy
            )
        except (RuntimeError, ValueError) as error:
            self.team_strategy_dropdown.disabled = False
            self._apply_team_strategy_style(previous_strategy)
            self.strategy_status.value = (
                f"Team Strategy could not be saved: {error}"
            )
            self.strategy_status.color = "#F87171"
            self.strategy_status.visible = True
            self.page.update()
            return

        if not save_succeeded:
            self.team_strategy_dropdown.disabled = False
            self._apply_team_strategy_style(previous_strategy)
            self.strategy_status.value = (
                "Team Strategy could not be saved."
            )
            self.strategy_status.color = "#F87171"
            self.strategy_status.visible = True
            self.page.update()
            return

        self.team_strategy_dropdown.disabled = False
        self.refresh_team_strategy(strategy)
        if self.on_strategy_updated:
            self.on_strategy_updated(strategy)
        self.page.update()

    def build(self) -> ft.Control:
        """Return the complete interactive Battle Compass view."""
        settings_card = ft.Container(
            content=ft.Column(
                controls=cast(
                    list[ft.Control],
                    [
                        ft.Text(
                            "Battle Settings",
                            size=TEXT_SIZE_FEATURED_TITLE,
                            weight=ft.FontWeight.BOLD,
                            font_family=FONT_FAMILY_HEADER,
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
                        ft.Container(
                            content=ft.Row(
                                controls=cast(
                                    list[ft.Control],
                                    [
                                        ft.Container(
                                            content=self.opponent_dropdown,
                                            width=240,
                                        ),
                                        ft.Container(
                                            content=ft.ResponsiveRow(
                                                controls=[
                                                    ft.Container(
                                                        content=ft.Column(
                                                            controls=[
                                                                ft.Row(
                                                                    controls=[
                                                                        self.team_strategy_dropdown,
                                                                        self.strategy_recommender_button,
                                                                    ],
                                                                    spacing=6,
                                                                    vertical_alignment=ft.CrossAxisAlignment.CENTER,
                                                                ),
                                                                self.strategy_status,
                                                            ],
                                                            spacing=3,
                                                            tight=True,
                                                        ),
                                                        col={
                                                            "xs": 12,
                                                            "md": 7,
                                                        },
                                                    ),
                                                    ft.Container(
                                                        content=self.strategy_description_text,
                                                        col={
                                                            "xs": 12,
                                                            "md": 5,
                                                        },
                                                        padding=ft.Padding.only(
                                                            top=4,
                                                        ),
                                                    ),
                                                ],
                                                columns=12,
                                                spacing=12,
                                                run_spacing=6,
                                                vertical_alignment=(
                                                    ft.CrossAxisAlignment.CENTER
                                                ),
                                            ),
                                            width=650,
                                        ),
                                    ],
                                ),
                                alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                                spacing=14,
                                run_spacing=14,
                                wrap=True,
                                vertical_alignment=(
                                    ft.CrossAxisAlignment.CENTER
                                ),
                            ),
                            width=float("inf"),
                        ),
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
        if "Hop" in trainers:
            self.selected_trainer = "Hop"
        else:
            self.selected_trainer = trainers[0]
    def _select_first_battle(self) -> None:
        battles = self._battle_names()
        if not battles:
            raise RuntimeError(
                "No battles are available "
                "for the selected trainer."
            )
        if (
            self.selected_trainer == "Hop"
            and "Postwick" in battles
        ):
            self.selected_battle = "Postwick"
        else:
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
        view_model = build_battle_compass_view_model(
            team_data=self.team_data,
            opponent=self._selected_opponent(),
            items=self.items,
            ability_rules=self.ability_rules,
            moves_data=self.moves_data,
            team_strategy=self.app_state.team_strategy,
            battle_roster=self.battle_opponents,
        )
        if view_model.recommendation is None:
            self.results_host.content = self._build_no_recommendation_state(
                view_model.empty_state_message
            )
            return
        self.results_host.content = self._build_results(view_model)
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
                            size=TEXT_SIZE_CARD_TITLE,
                            weight=ft.FontWeight.BOLD,
                            font_family=FONT_FAMILY_HEADER,
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
        recommendation = view_model.recommendation
        if recommendation is None:
            return self._build_no_recommendation_state(
                view_model.empty_state_message
            )

        opponent = view_model.opponent
        display_matchup_label = recommendation.matchup_label
        display_matchup_level = recommendation.matchup_level

        card_move = recommendation.best_move
        card_move_score = recommendation.best_move_score
        card_item_boosted = recommendation.item_boosted
        card_effectiveness_label = get_effectiveness_label(
            recommendation.best_move_type_multiplier,
            mode="offense",
        )
        card_effectiveness_color = self._effectiveness_color(
            recommendation.best_move_type_multiplier,
            mode="offense",
        )
        move_panel_label = "Best Move"
        score_label = "Move Score"
        score_text: str | None = None

        selected_plan = view_model.selected_strategy_plan
        if selected_plan is not None:
            display_matchup_label = f"{selected_plan.fit} Strategic Fit"
            display_matchup_level = {
                "Strong": 3,
                "Viable": 2,
            }.get(selected_plan.fit, 1)

            strategic_move = dict(
                self.move_lookup.get(
                    selected_plan.lead_move,
                    {},
                )
            )
            strategic_move["Move"] = selected_plan.lead_move

            card_move = strategic_move
            card_move_score = 0.0
            card_item_boosted = False
            card_effectiveness_label = "Strategic opener"
            card_effectiveness_color = strategy_color(view_model.team_strategy)
            move_panel_label = "Recommended Move"
            score_label = "Plan Role"
            score_text = "Engine Setup"

        recommendation_card = RecommendationCard(
            pokemon_name=recommendation.pokemon["Pokemon"],
            gender_symbol=self._gender_symbol(
                recommendation.pokemon.get("Gender")
            ),
            artwork_src=self._pokemon_asset(
                recommendation.pokemon["Pokemon"],
                gender=recommendation.pokemon.get("Gender"),
                use_texture=True,
                held_item=recommendation.pokemon.get("Held Item"),
                nature=recommendation.pokemon.get("Nature"),
            ),
            type_badges=self._pokemon_type_badges(
                recommendation.pokemon
            ),
            best_move=card_move["Move"],
            best_move_type=str(
                card_move.get("Type") or "Unknown"
            ),
            best_move_type_badge_src=self._type_badge_asset(
                card_move.get("Type")
            ),
            effectiveness_label=card_effectiveness_label,
            effectiveness_color=card_effectiveness_color,
            move_score=card_move_score,
            item_boosted=card_item_boosted,
            held_item=recommendation.held_item,
            item_multiplier=recommendation.item_multiplier,
            base_move_score=recommendation.base_move_score,
            item_bonus_amount=recommendation.item_bonus_amount,
            matchup_label=display_matchup_label,
            matchup_ratio=recommendation.ratio,
            matchup_level=display_matchup_level,
            why_text=view_model.why_text,
            battle_notes=[
                (
                    note.icon,
                    note.text,
                    self._note_style(note.category),
                )
                for note in recommendation.battle_notes
            ],
            on_full_analysis_click=self._scroll_to_full_analysis,
            on_type_badge_click=self._show_type_matchups,
            on_move_type_badge_click=self._show_offensive_type_matchups,
            move_panel_label=move_panel_label,
            score_label=score_label,
            score_text=score_text,
        )

        threat_score = recommendation.incoming_worst_score
        threat_move_name = str(recommendation.worst_move["Move"])
        threat_category = str(
            recommendation.worst_move.get("Category", "Unknown")
        )
        threat_move_type = str(
            recommendation.worst_move.get("Type") or "Unknown"
        )
        threat_multiplier = recommendation.incoming_type_multiplier
        threat_score_label = "Incoming Worst Score"
        threat_move_label = "Worst Incoming Move"
        strategy_plan = view_model.selected_strategy_plan
        if strategy_plan is not None and strategy_plan.opener_threat_move:
            threat_score = strategy_plan.opener_threat_score
            threat_move_name = strategy_plan.opener_threat_move
            threat_category = strategy_plan.opener_threat_category or "Unknown"
            threat_move_type = strategy_plan.opener_threat_type or "Unknown"
            threat_multiplier = strategy_plan.opener_threat_multiplier
            threat_score_label = "Opener Threat Score"
            threat_move_label = f"Worst Response to {strategy_plan.lead_move}"
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
                held_item=opponent.get(
                    "Held Item"
                ),
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
            incoming_worst_score=threat_score,
            worst_incoming_move=threat_move_name,
            incoming_category=threat_category,
            incoming_move_type=threat_move_type,
            incoming_type_badge_src=(
                self._type_badge_asset(
                    threat_move_type
                )
            ),
            defensive_effectiveness_label=(
                get_effectiveness_label(
                    threat_multiplier,
                    mode="defense",
                )
            ),
            defensive_effectiveness_color=(
                self._effectiveness_color(
                    threat_multiplier,
                    mode="defense",
                )
            ),
            defensive_effectiveness_background=(
                self._effectiveness_background(
                    threat_multiplier,
                    mode="defense",
                )
            ),
            on_type_badge_click=(
                self._show_type_matchups
            ),
            on_move_type_badge_click=(
                self._show_offensive_type_matchups
            ),
            threat_score_label=threat_score_label,
            threat_move_label=threat_move_label,
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
        strategy_action_panel = self._build_strategy_action_panel(view_model)
        result_controls: list[ft.Control] = []
        if strategy_action_panel is not None:
            result_controls.append(strategy_action_panel)
        result_controls.extend(
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
            ]
        )
        return ft.Column(
            controls=result_controls,
            spacing=28,
            horizontal_alignment=ft.CrossAxisAlignment.CENTER,
        )
    def _build_strategy_action_panel(
        self,
        view_model: BattleCompassViewModel,
    ) -> ft.Control | None:
        """Show the selected strategy plan, readiness, or tactical fallback."""

        if view_model.team_strategy == "strongest_matchup":
            return None

        if view_model.team_strategy not in {"poison_attrition", "poison_offensive_pressure"}:
            readiness = evaluate_strategy_viability(
                view_model.team_strategy,
                recognize_team_capabilities(self.team_data, self.moves_data),
            )
            readiness_color = self._strategy_viability_color(readiness.viability)
            details: list[ft.Control] = [
                ft.Text(
                    strategy_label(view_model.team_strategy) + " Readiness",
                    size=TEXT_SIZE_CARD_TITLE,
                    weight=ft.FontWeight.BOLD,
                    font_family=FONT_FAMILY_HEADER,
                    color=TEXT_PRIMARY,
                ),
                ft.Text(
                    readiness.viability,
                    size=19,
                    weight=ft.FontWeight.BOLD,
                    color=readiness_color,
                ),
                ft.Text(
                    readiness.summary,
                    size=14,
                    color=TEXT_SECONDARY,
                ),
            ]
            if readiness.contributing_pokemon:
                details.append(
                    ft.Text(
                        "Current contributors: " + ", ".join(readiness.contributing_pokemon),
                        size=12,
                        color=TEXT_MUTED,
                    )
                )
            details.append(
                ft.Text(
                    (
                        view_model.strategy_fallback_reason
                        or "This strategy's live tactical branch is not yet specialized."
                    ),
                    size=12,
                    color=TEXT_MUTED,
                )
            )
            return ft.Container(
                content=ft.Column(controls=details, spacing=8),
                width=940,
                padding=16,
                bgcolor=SURFACE_RAISED,
                border=ft.Border.all(1, strategy_color(view_model.team_strategy)),
                border_radius=14,
            )

        plan = view_model.selected_strategy_plan
        if plan is not None:
            action = plan.action
            detail = plan.action_detail
            footer = (
                "The Recommendation Card shows step one of this plan. Full Analysis "
                "remains strategy-neutral so you can still compare direct options."
            )
        else:
            action = "Direct fallback recommended"
            detail = (
                view_model.strategy_fallback_reason
                or "No safe opening is available for the selected Poison strategy in this matchup."
            )
            footer = (
                "The selected strategy is still active; Battle Compass is deviating "
                "because the modeled matchup does not support a safe strategic opener."
            )

        return ft.Container(
            content=ft.Column(
                controls=[
                    ft.Text(
                        TEAM_STRATEGY_LABELS.get(view_model.team_strategy, "Poison Strategy") + " Plan",
                        size=TEXT_SIZE_CARD_TITLE,
                        weight=ft.FontWeight.BOLD,
                        font_family=FONT_FAMILY_HEADER,
                        color=TEXT_PRIMARY,
                    ),
                    ft.Text(
                        action,
                        size=19,
                        weight=ft.FontWeight.BOLD,
                        color=strategy_color(view_model.team_strategy),
                    ),
                    ft.Text(
                        detail,
                        size=14,
                        color=TEXT_SECONDARY,
                    ),
                    ft.Text(
                        footer,
                        size=12,
                        color=TEXT_MUTED,
                    ),
                ],
                spacing=8,
            ),
            width=940,
            padding=16,
            bgcolor=SURFACE_RAISED,
            border=ft.Border.all(1, strategy_color(view_model.team_strategy)),
            border_radius=14,
        )
    def _show_type_matchups(
        self,
        pokemon_types: list[str],
    ) -> None:
        """Show the Pokémon's combined defensive type matchups."""
        show_type_matchup_dialog(
            page=self.page,
            pokemon_types=pokemon_types,
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
                held_item=pokemon.get(
                    "Held Item"
                ),
                            nature=pokemon.get(
                    "Nature"
                ),
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
            effectiveness_label=(
                get_effectiveness_label(
                    matchup.best_move_type_multiplier,
                    mode="offense",
                )
            ),
            effectiveness_color=(
                self._effectiveness_color(
                    matchup.best_move_type_multiplier,
                    mode="offense",
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
        types = get_effective_pokemon_types(
            pokemon
        )
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
        held_item: object = None,
    nature: object = None,
    ) -> str:
        asset_path = get_sprite_path(
            pokemon_name,
            gender=gender,
            use_gmax=use_gmax,
            use_texture=use_texture,
            held_item=held_item,
                    nature=nature,
        )
        if asset_path is None:
            # A missing form-specific asset must never prevent a Journey from
            # reopening. Nor should we show another form's artwork instead.
            # UI component contracts require a string source, so an empty
            # source intentionally renders no artwork rather than the wrong form.
            return ""
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
        if not asset_exists(trainer_path):
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
