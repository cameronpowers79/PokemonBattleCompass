"""
Journey onboarding view.

Coordinates the welcome screen, Journey import, starter selection, starter
entry, and Journey completion. The existing Journey is not replaced until
the player confirms a valid import or finishes and validates new starter data.
"""

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path
import json
import re
from typing import cast

import flet as ft

from ui.components.journey_ready import JourneyReady
from ui.components.strategy_move_card import strategy_move_card
from ui.components.starter_details import StarterDetails
from ui.components.starter_selection import StarterSelection
from ui.storage.journey_storage import parse_journey_export
from ui.theme import (
    APP_BACKGROUND,
    CONTENT_MAX_WIDTH,
    PRIMARY_BLUE,
    SURFACE,
    SURFACE_RAISED,
    TEXT_PRIMARY,
    TEXT_SECONDARY,
    TEXT_SIZE_PAGE_TITLE,
    TEXT_SIZE_LABEL,
    TEXT_SIZE_BODY_LARGE,
    FONT_FAMILY_HEADER,
)
from ui.viewmodels.app_state import AppState
from engine.strategy_definitions import STRATEGY_DEFINITIONS, get_strategy_definition
from engine.strategy_capabilities import (
    recommend_strategy_pokemon_additions,
    recognize_learnable_pokemon_capabilities,
    recognize_pokemon_capabilities,
    evaluate_strategy_viability,
    strategy_move_guidance,
)
from engine.learnsets import supported_strategy_move_methods
from ui.rendering import get_sprite_path
from ui.strategy_ui import strategy_color


STARTER_DEFAULTS = {
    "Grookey": {
        "Type1": "Grass",
        "Ability": "Overgrow",
        "Move1": "Scratch",
        "Move2": "Growl",
    },
    "Scorbunny": {
        "Type1": "Fire",
        "Ability": "Blaze",
        "Move1": "Tackle",
        "Move2": "Growl",
    },
    "Sobble": {
        "Type1": "Water",
        "Ability": "Torrent",
        "Move1": "Pound",
        "Move2": "Growl",
    },
}


class OnboardingView:
    """Coordinate first-use welcome and Journey onboarding."""

    def __init__(
        self,
        page: ft.Page,
        *,
        app_state: AppState,
        on_complete: Callable[[], None],
        on_new_journey_complete: Callable[[], None] | None = None,
        show_welcome: bool = False,
    ) -> None:
        self.page = page
        self.app_state = app_state
        self.on_complete = on_complete
        self.on_new_journey_complete = (
            on_new_journey_complete
        )
        self.show_welcome = show_welcome

        self.pending_starter: str | None = None
        self.starter_details: StarterDetails | None = None
        self.pending_import_journey: dict | None = None
        self.pending_starter_record: dict | None = None
        self.starter_retention = "keep"
        self.pending_strategy = "strongest_matchup"
        self.planned_team: list[dict] = []
        self.weather_focus: str | None = None
        self.weather_intent = "auto"
        self._planning_catalog = self._load_planning_catalog()
        self._planning_item_catalog = self._load_planning_json("journey_items.json")
        self._planning_learnsets = self.app_state.reference_data.get("learnsets_swsh", {})

        self.file_picker = ft.FilePicker()
        self.page.services.append(self.file_picker)

        initial_content: ft.Control

        if show_welcome:
            initial_content = self._build_welcome_screen()
        elif (
            not app_state.has_team_member
            and app_state.starter in STARTER_DEFAULTS
        ):
            self.pending_starter = app_state.starter
            initial_content = self._build_starter_details(
                app_state.starter
            )
        else:
            initial_content = self._build_starter_selection()

        self.content_host = ft.Container(
            content=initial_content,
            width=CONTENT_MAX_WIDTH,
            alignment=ft.Alignment.TOP_CENTER,
        )

    def build(self) -> ft.Control:
        """Return the complete onboarding view."""

        return ft.Container(
            content=ft.SafeArea(
                content=ft.Column(
                    controls=cast(
                        list[ft.Control],
                        [
                            self._build_branding_header(),
                            self.content_host,
                        ],
                    ),
                    spacing=28,
                    horizontal_alignment=(
                        ft.CrossAxisAlignment.CENTER
                    ),
                ),
            ),
            expand=True,
            bgcolor=APP_BACKGROUND,
            padding=28,
            alignment=ft.Alignment.TOP_CENTER,
        )

    @staticmethod
    def _build_branding_header() -> ft.Control:
        """Build the onboarding branding header."""

        return ft.Column(
            controls=cast(
                list[ft.Control],
                [
                    ft.Image(
                        src="raw/BattleCompassLogo.png",
                        width=112,
                        fit=ft.BoxFit.CONTAIN,
                        semantics_label="Battle Compass logo",
                    ),
                    ft.Image(
                        src="raw/WordMarkLogoBlock.png",
                        width=620,
                        fit=ft.BoxFit.CONTAIN,
                        semantics_label="Pokémon Battle Compass",
                    ),
                ],
            ),
            spacing=8,
            horizontal_alignment=ft.CrossAxisAlignment.CENTER,
        )

    def _build_welcome_screen(self) -> ft.Control:
        """Offer new-Journey onboarding or portable Journey import."""

        return ft.Container(
            content=ft.Column(
                controls=cast(
                    list[ft.Control],
                    [
                        ft.Text(
                            "Welcome to Pokémon Battle Compass",
                            size=TEXT_SIZE_PAGE_TITLE,
                            weight=ft.FontWeight.BOLD,
                            font_family=FONT_FAMILY_HEADER,
                            color=TEXT_PRIMARY,
                            text_align=ft.TextAlign.CENTER,
                        ),
                        ft.Text(
                            (
                                "Start a new adventure, or restore a "
                                "Journey you previously exported."
                            ),
                            size=TEXT_SIZE_LABEL,
                            color=TEXT_SECONDARY,
                            text_align=ft.TextAlign.CENTER,
                        ),
                        ft.Row(
                            controls=cast(
                                list[ft.Control],
                                [
                                    ft.Button(
                                        content="Start a New Journey",
                                        icon=ft.Icons.EXPLORE_OUTLINED,
                                        bgcolor=PRIMARY_BLUE,
                                        color=TEXT_PRIMARY,
                                        icon_color=TEXT_PRIMARY,
                                        on_click=self._start_new_journey,
                                    ),
                                    ft.Button(
                                        content="Load a Journey",
                                        icon=ft.Icons.UPLOAD_FILE_OUTLINED,
                                        on_click=self._select_journey_file,
                                    ),
                                ],
                            ),
                            alignment=ft.MainAxisAlignment.CENTER,
                            spacing=14,
                            wrap=True,
                        ),
                    ],
                ),
                spacing=18,
                horizontal_alignment=ft.CrossAxisAlignment.CENTER,
            ),
            width=720,
            padding=28,
            bgcolor=SURFACE,
            border_radius=16,
            alignment=ft.Alignment.CENTER,
        )

    def _start_new_journey(
        self,
        event: ft.Event[ft.Button],
    ) -> None:
        """Continue from Welcome into starter selection."""

        del event
        self.show_welcome = False
        self.content_host.content = self._build_starter_selection()
        self.page.update()

    async def _select_journey_file(
        self,
        event: ft.Event[ft.Button],
    ) -> None:
        """Select and validate a portable Journey export."""

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
                    "The Journey import helper could not be opened: "
                    f"{error}"
                )
            return

        try:
            selected_files = await self.file_picker.pick_files(
                dialog_title="Load Journey",
                allow_multiple=False,
                file_type=ft.FilePickerFileType.CUSTOM,
                allowed_extensions=["json"],
                with_data=True,
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
        """Confirm activation of the selected Journey."""

        starter = str(journey.get("starter") or "Unknown")
        team = journey.get("team")
        team_count = len(team) if isinstance(team, list) else 0

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
                        controls=cast(
                            list[ft.Control],
                            [
                                ft.Text(
                                    (
                                        "This Journey will become the active "
                                        "Journey on this device."
                                    ),
                                    size=TEXT_SIZE_BODY_LARGE,
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
                                                    (
                                                        "Active team: "
                                                        f"{team_count} Pokémon"
                                                    ),
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
                        ),
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
        """Persist the imported Journey and show success confirmation."""

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

        self.pending_import_journey = None

        if not load_succeeded:
            self._show_load_error(
                "The Journey could not be saved."
            )
            return

        self.page.show_dialog(
            ft.AlertDialog(
                modal=True,
                title=ft.Text(
                    "Journey Loaded!",
                    weight=ft.FontWeight.BOLD,
                    color=TEXT_PRIMARY,
                ),
                content=ft.Text(
                    (
                        "Your saved Journey has been restored. Select OK "
                        "to continue from its last saved page."
                    ),
                    size=TEXT_SIZE_BODY_LARGE,
                    color=TEXT_SECONDARY,
                ),
                actions=[
                    ft.Button(
                        content="OK",
                        icon=ft.Icons.CHECK_ROUNDED,
                        bgcolor=PRIMARY_BLUE,
                        color=TEXT_PRIMARY,
                        icon_color=TEXT_PRIMARY,
                        on_click=self._finish_journey_load,
                    ),
                ],
                actions_alignment=ft.MainAxisAlignment.END,
            )
        )

    def _finish_journey_load(
        self,
        event: ft.Event[ft.Button],
    ) -> None:
        """Close load confirmation and enter the restored Journey."""

        del event
        self.page.pop_dialog()
        self.on_complete()

    def _show_load_error(self, message: str) -> None:
        """Show a non-fatal Journey import error."""

        self.page.show_dialog(
            ft.AlertDialog(
                modal=True,
                title=ft.Text(
                    "Journey could not be loaded",
                    weight=ft.FontWeight.BOLD,
                    color=TEXT_PRIMARY,
                ),
                content=ft.Text(
                    message,
                    size=TEXT_SIZE_BODY_LARGE,
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
        """Close a Journey-import error dialog."""

        del event
        self.page.pop_dialog()
        self.page.update()

    def _build_starter_selection(self) -> ft.Control:
        """Build the starter-selection component."""

        return StarterSelection(
            starter_defaults=STARTER_DEFAULTS,
            on_selected=self._handle_starter_selected,
        )

    def _build_starter_details(
        self,
        starter_name: str | None,
    ) -> ft.Control:
        """Build the starter-details component."""

        if (
            starter_name is None
            or starter_name not in STARTER_DEFAULTS
        ):
            return self._build_starter_selection()

        self.starter_details = StarterDetails(
            starter_name=starter_name,
            starter_defaults=STARTER_DEFAULTS[
                starter_name
            ],
            moves_data=self.app_state.moves_data,
            on_completed=self._starter_ready,
        )

        return self.starter_details

    def _handle_starter_selected(
        self,
        starter_name: str,
    ) -> None:
        """Open starter details without changing persistent Journey data."""

        if starter_name not in STARTER_DEFAULTS:
            return

        self.pending_starter = starter_name
        self.content_host.content = self._build_starter_details(
            starter_name
        )
        self.page.update()

    @staticmethod
    def _load_planning_json(filename: str) -> list[dict]:
        path = Path(__file__).resolve().parents[2] / "data" / filename
        try:
            result = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            return []
        return [record for record in result if isinstance(record, dict)] if isinstance(result, list) else []

    @classmethod
    def _load_planning_catalog(cls) -> list[dict]:
        return cls._load_planning_json("journey_pokemon.json")

    @staticmethod
    def _candidate(record: dict) -> dict:
        result = dict(record)
        result["Pokemon"] = str(record.get("pokemon") or record.get("Pokemon") or "")
        for key, options in {"Gender": ("Gender", "gender"), "Ability": ("Ability", "ability"), "Form": ("Form", "form")}.items():
            for option in options:
                if record.get(option):
                    result[key] = record[option]
                    break
        return result

    @staticmethod
    def _species_key(name: str) -> str:
        return re.sub(r"\s+\((?:Male|Female)\)$", "", name, flags=re.I).casefold().strip()

    def _planning_record(self, name: str) -> dict | None:
        key = self._species_key(name)
        return next((r for r in self._planning_catalog if self._species_key(str(r.get("pokemon") or "")) == key), None)

    def _planned_candidate(self, selection: dict) -> dict:
        record = self._planning_record(selection["name"])
        candidate = self._candidate(record or {"pokemon": selection["name"]})
        match = re.search(r"\((Male|Female)\)$", selection["name"], re.I)
        if match:
            candidate["Gender"] = match.group(1).title()
        if selection.get("ability"):
            candidate["Ability"] = selection["ability"]
        return candidate

    def _starter_ready(self, starter_record: dict) -> None:
        """Keep the completed starter provisional until final confirmation."""
        if self.pending_starter is None:
            return
        self.pending_starter_record = dict(starter_record)
        self.planned_team = []
        self.weather_focus = None
        self.weather_intent = "auto"
        self.content_host.content = self._build_strategy_intro()
        self.page.update()

    @staticmethod
    def _primary_button(label: str, on_click) -> ft.Button:
        return ft.Button(
            content=label, on_click=on_click, bgcolor=PRIMARY_BLUE,
            color="#FFFFFF", icon_color="#FFFFFF",
            style=ft.ButtonStyle(padding=ft.Padding.symmetric(horizontal=22, vertical=15)),
        )

    @staticmethod
    def _onboarding_panel(title: str, controls: list[ft.Control]) -> ft.Control:
        return ft.Container(
            content=ft.Column(controls=[
                ft.Text(title, size=TEXT_SIZE_PAGE_TITLE, weight=ft.FontWeight.BOLD,
                        font_family=FONT_FAMILY_HEADER, color=TEXT_PRIMARY),
                *controls,
            ], spacing=20),
            width=940, padding=32, bgcolor=SURFACE,
            border=ft.Border.all(1, "#354052"), border_radius=18,
        )

    def _build_strategy_intro(self) -> ft.Control:
        return self._onboarding_panel("Build a team your way", [
            ft.Text(
                "Battle Compass can help you choose a team strategy, find Pokémon that support it, "
                "and plan useful moves and where to obtain them. Your starter is always part of your Journey.",
                color=TEXT_SECONDARY, size=17,
            ),
            ft.Container(
                content=ft.Column(controls=[
                    ft.Text("Would you like Battle Compass to help plan your strategy?",
                            color=TEXT_PRIMARY, weight=ft.FontWeight.BOLD, size=19),
                    ft.Text("This is optional. You can use the Strategy Recommender any time during your Journey.",
                            color=TEXT_SECONDARY),
                    ft.Row(controls=[
                        self._primary_button("Yes — Help Me Plan", lambda e: self._show_retention()),
                        ft.OutlinedButton(content="Skip for Now", on_click=lambda e: self._skip_strategy()),
                    ], wrap=True, spacing=14),
                ], spacing=14), padding=22, bgcolor=SURFACE_RAISED,
                border=ft.Border.all(1, "#354052"), border_radius=14,
            ),
        ])

    def _show_retention(self):
        self.content_host.content = self._build_starter_retention()
        self.page.update()

    def _skip_strategy(self):
        self.pending_strategy = "strongest_matchup"
        self.planned_team = []
        self._show_plan_review()

    def _build_starter_retention(self) -> ft.Control:
        group = ft.RadioGroup(
            value=self.starter_retention,
            content=ft.Column(controls=[
                ft.Row(controls=[ft.Radio(value="keep"), ft.Text(
                    "Keep my starter — reserve one of six slots", expand=True, size=15,
                    color=TEXT_PRIMARY, max_lines=None)], spacing=8),
                ft.Row(controls=[ft.Radio(value="box"), ft.Text(
                    "Open to boxing my starter — plan six other Pokémon", expand=True,
                    size=15, color=TEXT_PRIMARY, max_lines=None)], spacing=8),
                ft.Row(controls=[ft.Radio(value="undecided"), ft.Text(
                    "Undecided — keep a slot for now; explore alternatives later",
                    expand=True, size=15, color=TEXT_PRIMARY, max_lines=None)], spacing=8),
            ], spacing=18),
        )
        def advance(event):
            self.starter_retention = str(group.value or "keep")
            self.content_host.content = self._build_strategy_choice()
            self.page.update()
        return self._onboarding_panel("Planning around your starter", [
            ft.Text(
                "In the next steps, Battle Compass can help you choose a strategy and guide you "
                "toward a team that takes advantage of it. When suggesting teammates, should "
                "Battle Compass assume you will:",
                color=TEXT_SECONDARY, size=17,
            ),
            ft.Container(content=group, padding=20, bgcolor=SURFACE_RAISED,
                         border=ft.Border.all(1, "#354052"), border_radius=12),
            ft.Text("This is only a planning preference. Your starter stays in your Journey either way.",
                    color=TEXT_SECONDARY),
            ft.Row(controls=[
                ft.OutlinedButton(content="Back", on_click=lambda e: self._back_to_intro()),
                self._primary_button("Choose Team Strategy", advance),
            ], wrap=True, spacing=12),
        ])

    def _back_to_intro(self):
        self.content_host.content = self._build_strategy_intro()
        self.page.update()

    def _build_strategy_choice(self) -> ft.Control:
        options = [ft.DropdownOption(
            key=k, text=v.label,
            content=ft.Text(v.label, color=strategy_color(k), weight=ft.FontWeight.BOLD),
        ) for k, v in STRATEGY_DEFINITIONS.items()]
        selector = ft.Dropdown(
            label="Team Strategy", value=self.pending_strategy, options=options,
            width=490, text_style=ft.TextStyle(
                color=strategy_color(self.pending_strategy), weight=ft.FontWeight.BOLD),
        )
        definition = get_strategy_definition(self.pending_strategy)
        description = ft.Text(definition.full_description, color=TEXT_SECONDARY, size=16)
        def chosen(event):
            self.pending_strategy = str(selector.value or "strongest_matchup")
            description.value = get_strategy_definition(self.pending_strategy).full_description
            selector.text_style = ft.TextStyle(color=strategy_color(self.pending_strategy), weight=ft.FontWeight.BOLD)
            self.page.update()
        selector.on_select = chosen
        def next_step(event):
            self.pending_strategy = str(selector.value or "strongest_matchup")
            self.content_host.content = self._build_team_planning()
            self.page.update()
        return self._onboarding_panel("Choose your Team Strategy", [
            ft.Text("Pick the kind of battles you'd like to fight. You can change strategies later.",
                    color=TEXT_SECONDARY, size=17),
            ft.Container(content=ft.Column(controls=[selector, description], spacing=18),
                         padding=22, bgcolor=SURFACE_RAISED,
                         border=ft.Border.all(1, "#354052"), border_radius=12),
            ft.Row(controls=[
                ft.OutlinedButton(content="Back", on_click=lambda e: self._navigate_retention()),
                self._primary_button("Plan My Team", next_step),
            ], wrap=True, spacing=12),
        ])

    def _navigate_retention(self):
        self._show_retention()

    def _starter_final_candidate(self) -> dict:
        starter = self.pending_starter or ""
        final = {"Grookey": "Rillaboom", "Scorbunny": "Cinderace", "Sobble": "Inteleon"}.get(starter, starter)
        candidate = self._candidate(self._planning_record(final) or {"pokemon": final})
        # A currently entered starter's Ability is carried into the planned evolution.
        if self.pending_starter_record and self.pending_starter_record.get("Ability"):
            candidate["Ability"] = self.pending_starter_record["Ability"]
        return candidate

    def _planning_capabilities(self):
        from dataclasses import replace
        members: list[tuple[dict, bool]] = []
        if self.starter_retention != "box":
            members.append((self._starter_final_candidate(), False))
        members.extend((self._planned_candidate(item), item.get("weather_role") == "setter")
                       for item in self.planned_team)
        results = []
        automatic_weather = {"drizzle", "drought", "sand stream", "snow warning"}
        for mon, designated_setter in members:
            result = recognize_learnable_pokemon_capabilities(
                mon, self.app_state.moves_data, self._planning_learnsets)
            if self.pending_strategy == "weather_control":
                # Access to a weather TM isn't a commitment to actually setting it.
                # Only an auto-weather Ability or a chosen manual setter counts.
                ability = str(mon.get("Ability") or "").casefold()
                if ability not in automatic_weather and not designated_setter:
                    keys = tuple(k for k in result.capability_keys if not k.startswith("WEATHER_SET_"))
                    result = replace(result, capability_keys=keys)
            results.append(result)
        return results

    def _planning_options(self):
        used = {self._species_key(x["name"]) for x in self.planned_team}
        used.add(self._species_key({"Grookey":"Rillaboom", "Scorbunny":"Cinderace", "Sobble":"Inteleon"}.get(self.pending_starter or "", "")))
        options = []
        for record in self._planning_catalog:
            name = str(record.get("pokemon") or "")
            if not name or self._species_key(name) in used:
                continue
            candidate = self._candidate(record)
            candidate["_available_now"] = int(record.get("required_badge") or 0) == 0
            candidate["required_badge"] = int(record.get("required_badge") or 0)
            candidate["_journey_starter"] = self.pending_starter
            if name.casefold() in {"meowstic", "indeedee"} and not candidate.get("Gender"):
                for gender in ("Male", "Female"):
                    options.append(dict(candidate, Gender=gender, _strategy_gender_variant=True))
            else:
                options.append(candidate)
        return options

    @staticmethod
    def _recommendation_artwork(pokemon_name: str) -> ft.Control:
        """Use the same form-safe textures as Battle Compass itself."""
        match = re.match(r"^(.*?) \((Male|Female)\)$", pokemon_name)
        species = match.group(1) if match else pokemon_name
        gender = match.group(2) if match else None
        path = get_sprite_path(species, gender=gender, use_texture=True)
        if path is None:
            content: ft.Control = ft.Icon(ft.Icons.CATCHING_POKEMON, size=42, color=TEXT_SECONDARY)
        else:
            assets_root = Path(__file__).resolve().parents[2] / "assets"
            try:
                src = Path(path).resolve().relative_to(assets_root.resolve()).as_posix()
                content = ft.Image(src=src, width=112, height=132, fit=ft.BoxFit.CONTAIN,
                                   semantics_label=f"{pokemon_name} artwork")
            except ValueError:
                content = ft.Icon(ft.Icons.CATCHING_POKEMON, size=42, color=TEXT_SECONDARY)
        return ft.Container(content=content, width=132, height=152,
                            alignment=ft.Alignment.CENTER,
                            bgcolor=SURFACE, border_radius=12)

    def _set_weather_focus(self, focus: str, intent: str = "auto") -> None:
        self.weather_focus = focus
        self.weather_intent = intent
        self.content_host.content = self._build_team_planning()
        self.page.update()

    def _weather_package_progress(self, capabilities):
        weather_names = {"SUN": "Sun", "RAIN": "Rain", "SAND": "Sandstorm", "HAIL": "Hail"}
        statuses = []
        for weather, label in weather_names.items():
            setters = [p.pokemon_name for p in capabilities if f"WEATHER_SET_{weather}" in p.capability_keys]
            beneficiaries = [p.pokemon_name for p in capabilities if f"WEATHER_BENEFIT_{weather}" in p.capability_keys]
            matched = [(a, b) for a in setters for b in beneficiaries if a != b]
            if setters or beneficiaries:
                statuses.append((weather, label, setters, beneficiaries, matched))
        return statuses

    def _weather_planning_controls(self, capabilities) -> list[ft.Control]:
        statuses = self._weather_package_progress(capabilities)
        out: list[ft.Control] = [ft.Text("Weather packages", size=19, weight=ft.FontWeight.BOLD)]
        for weather, label, setters, beneficiaries, matched in statuses:
            message = (f"{label}: ready — {matched[0][0]} sets weather for {matched[0][1]}" if matched
                       else f"{label}: setter {', '.join(setters) if setters else 'needed'}; matching beneficiary {'available' if beneficiaries else 'needed'}")
            out.append(ft.Text(message, color=TEXT_SECONDARY))
        if self.weather_focus is None:
            out.append(ft.Text("Choose a weather to build around. You can add another weather package later.", color=TEXT_SECONDARY))
        else:
            out.append(ft.Text(f"Building: { {'SUN':'Sun','RAIN':'Rain','SAND':'Sandstorm','HAIL':'Hail'}[self.weather_focus] }", weight=ft.FontWeight.BOLD))
        out.append(ft.Row(controls=[ft.OutlinedButton(content=label, on_click=lambda e, w=weather: self._set_weather_focus(w, 'auto'))
                                    for weather, label in (("SUN", "Sun"), ("RAIN", "Rain"), ("SAND", "Sandstorm"), ("HAIL", "Hail"))], wrap=True))
        if self.weather_focus:
            focus = self.weather_focus
            have_setter = any(f"WEATHER_SET_{focus}" in p.capability_keys for p in capabilities)
            have_match = any(w == focus and bool(matched) for w, _, _, _, matched in statuses)
            if have_match:
                out.append(ft.Text(f"Your {focus.title()} weather strategy is ready! Strengthen it, choose another weather, or finish planning.", color=TEXT_SECONDARY))
            out.append(ft.Row(controls=[
                ft.OutlinedButton(content="Find matching beneficiaries", on_click=lambda e: self._set_weather_focus(focus, 'beneficiary')),
                ft.OutlinedButton(content="Find setters / alternative setters", on_click=lambda e: self._set_weather_focus(focus, 'setter')),
            ], wrap=True))
            if self.weather_intent == 'auto':
                self.weather_intent = 'setter'
        return out

    def _build_team_planning(self) -> ft.Control:
        max_picks = 6 if self.starter_retention == "box" else 5
        controls: list[ft.Control] = [
            ft.Text(f"Starter: {self.pending_starter}  •  Strategy: {get_strategy_definition(self.pending_strategy).label}", color=strategy_color(self.pending_strategy), weight=ft.FontWeight.BOLD, size=17),
            ft.Text(f"Future teammates selected: {len(self.planned_team)} / {max_picks}. These will be Journey goals, not immediately added to My Team.", color=TEXT_SECONDARY),
        ]
        for selection in self.planned_team:
            controls.append(ft.Row(controls=[
                ft.Text(selection["name"], expand=True),
                ft.Button(content="Remove", on_click=lambda e, n=selection["name"]: self._remove_planned(n)),
            ]))
        if self.pending_strategy == "strongest_matchup":
            controls.append(ft.Text("Strongest Matchup doesn't impose team roles. Choose your teammates freely during your Journey.", color=TEXT_SECONDARY))
        elif len(self.planned_team) < max_picks:
            capabilities = self._planning_capabilities()
            viability = evaluate_strategy_viability(self.pending_strategy, capabilities)
            controls.append(ft.Text(f"Projected strategy potential: {viability.viability} — {viability.summary}", color=TEXT_SECONDARY))
            if self.pending_strategy == "weather_control":
                controls.extend(self._weather_planning_controls(capabilities))
            options = recommend_strategy_pokemon_additions(self.pending_strategy, capabilities, self._planning_options(),
                                                            self.app_state.moves_data, self._planning_learnsets, limit=5,
                                                            weather_focus=self.weather_focus if self.pending_strategy == "weather_control" else None,
                                                            weather_intent=self.weather_intent if self.pending_strategy == "weather_control" else None,
                                                            planning_role=("beneficiary" if self.pending_strategy == "screen_control" and any(
                                                                "DUAL_SCREEN" in x.capability_keys for x in capabilities) else None))
            if self.pending_strategy == "weather_control" and not self.weather_focus:
                options = []
            if not options:
                controls.append(ft.Text("Choose a weather above to see matched recommendations, or finish planning when you are ready." if self.pending_strategy == "weather_control" else "No further supported strategy contributors were found; remaining slots are yours for coverage and personal preferences.", color=TEXT_SECONDARY))
            else:
                controls.append(ft.Text("Suggested next teammates (recalculated after each choice):", weight=ft.FontWeight.BOLD))
                for item in options:
                    details = ft.Column(controls=[
                        ft.Text(item.pokemon_name, size=19, color=TEXT_PRIMARY, weight=ft.FontWeight.BOLD),
                        ft.Text(item.summary, size=14, color=TEXT_SECONDARY),
                        ft.Row(controls=[self._primary_button(
                            f"+ Plan {item.pokemon_name}",
                            lambda e, rec=item: self._add_planned(rec))]),
                    ], spacing=12, expand=True)
                    controls.append(ft.Container(
                        content=ft.Row(controls=[
                            self._recommendation_artwork(item.pokemon_name), details,
                        ], spacing=18, vertical_alignment=ft.CrossAxisAlignment.CENTER),
                        padding=16, bgcolor=SURFACE_RAISED,
                        border=ft.Border.all(1, "#354052"), border_radius=14))
        controls.append(ft.Row(controls=[
            ft.Button(content="Back", on_click=lambda e: self._back_to_strategy()),
            self._primary_button("Review and Confirm", lambda e: self._show_plan_review()),
        ], wrap=True))
        return self._onboarding_panel("Build your future team", controls)

    def _back_to_strategy(self):
        self.content_host.content = self._build_strategy_choice()
        self.page.update()

    def _remove_planned(self, name: str):
        self.planned_team = [s for s in self.planned_team if s["name"] != name]
        self.content_host.content = self._build_team_planning()
        self.page.update()

    def _add_planned(self, recommendation):
        name = recommendation.pokemon_name
        ability = re.search(r"Recommended Ability: ([^.]+)", recommendation.summary)
        self.planned_team.append({"name": name, "ability": ability.group(1).split(" (")[0] if ability else "", "moves": None,
                                  "weather_role": self.weather_intent if self.pending_strategy == "weather_control" else None,
                                  "weather_focus": self.weather_focus if self.pending_strategy == "weather_control" else None,
                                  "screen_role": ("beneficiary" if self.pending_strategy == "screen_control" and any(
                                      "DUAL_SCREEN" in x.capability_keys for x in self._planning_capabilities()) else "setter")})
        if self.pending_strategy == "weather_control" and self.weather_focus and self.weather_intent == "setter":
            self.weather_intent = "beneficiary"
        self.content_host.content = self._build_team_planning()
        self.page.update()

    def _planned_move_guidance(self, selection: dict, candidate: dict):
        # Carry the player's weather package intent into shared move guidance.
        # A weather setter needs a weather move only without an automatic Ability;
        # beneficiaries may receive genuinely boosted attacks or utility moves.
        planned = dict(candidate)
        if self.pending_strategy == "weather_control":
            planned["_strategy_weather_role"] = selection.get("weather_role")
            planned["_strategy_weather_focus"] = selection.get("weather_focus")
        if self.pending_strategy == "screen_control":
            planned["_strategy_screen_role"] = selection.get("screen_role")
        return strategy_move_guidance(
            self.pending_strategy, planned, self.app_state.moves_data,
            self._planning_learnsets)

    def _onboarding_move_badge(self, move_name: str) -> ft.Control:
        move = next((row for row in self.app_state.moves_data
                     if isinstance(row, dict) and row.get("Move") == move_name), {})
        move_type = str(move.get("Type") or "")
        badge_src = None
        if move_type:
            badge_file = Path(__file__).resolve().parents[2] / "assets" / "type_badges" / f"{move_type}.png"
            if badge_file.exists():
                badge_src = f"type_badges/{move_type}.png"
        return strategy_move_card(move_name, move_type, badge_src, width=174)

    def _show_plan_review(self):
        items: list[ft.Control] = [
            ft.Text(f"Starter: {self.pending_starter} (always retained in your Journey)"),
            ft.Text(f"Starter team preference: {self.starter_retention}"),
            ft.Text(f"Strategy: {get_strategy_definition(self.pending_strategy).label}"),
            ft.Text(f"Future teammates: {len(self.planned_team)}"),
        ]
        for selection in self.planned_team:
            candidate = self._planned_candidate(selection)
            guidance = self._planned_move_guidance(selection, candidate)
            if selection.get("moves") is None:
                selection["moves"] = [name for name, _, _ in guidance]
            items.append(ft.Text(f"{selection['name']} — recommended Ability: {selection.get('ability') or 'Flexible'}", weight=ft.FontWeight.BOLD))
            if not guidance:
                items.append(ft.Text("No additional strategy move is necessary for this role; choose the remaining moves to suit your team.", color=TEXT_SECONDARY))
            selection.setdefault("move_sources", {})
            for name, purpose, method in guidance:
                methods = supported_strategy_move_methods(candidate, name, self._planning_learnsets)
                options = self._move_acquisition_options(methods)
                toggle = ft.Checkbox(label=f"{name} — {purpose}", value=name in selection["moves"])
                def changed(event, mon=selection, move=name, box=toggle):
                    current = list(mon.get("moves") or [])
                    if box.value and move not in current:
                        current.append(move)
                    elif not box.value and move in current:
                        current.remove(move)
                    mon["moves"] = current
                toggle.on_change = changed
                # Keep the explanation inside the available width beside the card.
                # A checkbox with a long inline label otherwise forces a Row wider
                # than the review panel and clips the text off-screen.
                toggle.label = None
                items.append(ft.Row(
                    controls=[
                        self._onboarding_move_badge(name),
                        ft.Column(
                            controls=[
                                ft.Row(controls=[
                                    toggle,
                                    ft.Text(f"{name} — {purpose}",
                                            color=TEXT_PRIMARY, size=14,
                                            expand=True, max_lines=None),
                                ], spacing=6, vertical_alignment=ft.CrossAxisAlignment.CENTER),
                            ], expand=True, spacing=0,
                        ),
                    ],
                    spacing=12, vertical_alignment=ft.CrossAxisAlignment.CENTER,
                ))
                if options:
                    allowed = {key for key, _ in options}
                    selected_source = selection["move_sources"].get(name)
                    if selected_source not in allowed:
                        selected_source = options[0][0]
                        selection["move_sources"][name] = selected_source
                    source_picker = ft.Dropdown(
                        label=f"How to learn {name}", width=420,
                        value=selected_source,
                        options=[ft.DropdownOption(key=key, text=label) for key, label in options],
                    )
                    def source_changed(event, mon=selection, move=name, dropdown=source_picker):
                        mon["move_sources"][move] = str(dropdown.value or "natural")
                    source_picker.on_select = source_changed
                    items.append(ft.Container(content=source_picker, padding=ft.Padding.only(left=30)))
        items.append(ft.Text("Only checked moves will be planned. You can freely choose remaining slots later.", color=TEXT_SECONDARY))
        items.append(ft.Row(controls=[
            ft.Button(content="Back", on_click=lambda e: self._return_to_planning()),
            self._primary_button("Prepare My Journey", lambda e: self.page.run_task(self._replace_journey)),
        ], wrap=True))
        self.content_host.content = self._onboarding_panel("Review your new Journey", items)
        self.page.update()

    @staticmethod
    def _move_acquisition_options(methods: list[dict]) -> list[tuple[str, str]]:
        """Offer natural and item routes separately; do not add items implicitly."""
        options: list[tuple[str, str]] = []
        for method in methods:
            kind = str(method.get("method") or "").casefold()
            item = str(method.get("item") or "").strip()
            if item:
                option = (item, f"Use {item} ({kind.upper()}) — add to Journey Checklist")
            elif kind == "level" and method.get("level") is not None:
                option = ("natural", f"Learn naturally at level {method['level']} — no item needed")
            elif kind in {"relearner", "reminder", "evolution"}:
                option = ("natural", "Move Reminder / evolution — no item needed")
            else:
                option = ("natural", f"{kind.title()} — no item needed")
            if option[0] not in {entry[0] for entry in options}:
                options.append(option)
        # Favor free learning, but let players explicitly select TM/TR.
        options.sort(key=lambda entry: (entry[0] != "natural", entry[1]))
        return options

    def _return_to_planning(self):
        self.content_host.content = self._build_team_planning()
        self.page.update()

    async def _replace_journey(self) -> None:
        """Only commit after the user approves the complete onboarding plan."""
        if self.pending_starter is None or self.pending_starter_record is None:
            return
        saved = await self.app_state.replace_journey(starter=self.pending_starter, team_data=[self.pending_starter_record])
        if not saved:
            self._show_onboarding_error("Could not save your new Journey. The previous Journey remains safe.")
            return
        strategy_saved = await self.app_state.save_team_strategy(self.pending_strategy)
        if not strategy_saved:
            self._show_onboarding_error("The Journey was created, but its strategy couldn't be saved. Select it again in Battle Compass.")
            return
        for selection in self.planned_team:
            record = self._planning_record(selection["name"])
            if record is None or not record.get("id"):
                continue
            mon = self._planned_candidate(selection)
            guidance = self._planned_move_guidance(selection, mon)
            slots = []
            selected = set(selection.get("moves") or [])
            for move_name, _, _ in guidance:
                if move_name not in selected:
                    continue
                source = selection.get("move_sources", {}).get(move_name, "natural")
                objective_id = self._item_objective_id(source) if source != "natural" else None
                slots.append({"move_name": move_name, "source_item_id": objective_id})
            try:
                result = await self.app_state.add_strategy_plan_to_journey(pokemon_id=str(record["id"]), moves=slots)
            except (RuntimeError, ValueError) as error:
                self._show_onboarding_error(f"Journey saved, but a team objective failed: {error}. Check My Journey before continuing.")
                return
            if not result:
                self._show_onboarding_error("Journey saved, but some team objectives could not be saved. Check My Journey.")
                return
        self._show_journey_ready()

    def _item_objective_id(self, code: str) -> str | None:
        matched = re.match(r"^(TM|TR)\s*0*(\d+)$", str(code).strip(), re.I)
        if not matched:
            return None
        kind, number = matched.group(1).upper(), int(matched.group(2))
        for item in self._planning_item_catalog:
            name_match = re.match(r"^(TM|TR)\s*0*(\d+)\b", str(item.get("name") or ""), re.I)
            if name_match and name_match.group(1).upper() == kind and int(name_match.group(2)) == number:
                return str(item.get("id") or "") or None
        return None

    def _show_onboarding_error(self, message: str):
        self.page.show_dialog(ft.AlertDialog(title=ft.Text("Journey setup needs attention"),
                          content=ft.Text(message), actions=[ft.Button(content="OK", on_click=lambda e: self.page.pop_dialog())]))

    def _show_journey_ready(self) -> None:
        self.content_host.content = JourneyReady(on_continue=self.on_new_journey_complete or self.on_complete)
        self.page.update()
