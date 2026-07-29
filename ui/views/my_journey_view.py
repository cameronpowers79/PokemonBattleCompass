"""My Journey view with persistent badge and objective progression.

Badge, item, and planned-Pokémon changes save immediately. Real badge artwork,
celebrations, encounter-table expansion, and map markers remain deferred.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import flet as ft

from ui.theme import (
    BORDER_DEFAULT,
    CARD_PADDING,
    CARD_RADIUS,
    CONTENT_MAX_WIDTH,
    DANGER,
    PRIMARY_BLUE,
    SUCCESS,
    SURFACE,
    SURFACE_RAISED,
    TEXT_MUTED,
    TEXT_PRIMARY,
    TEXT_SECONDARY,
)

from ui.viewmodels.app_state import AppState


DATA_DIR = Path(__file__).resolve().parents[2] / "data"


class MyJourneyView:
    """Render My Journey fixture data with saved badge progression."""

    def __init__(
        self,
        page: ft.Page,
        *,
        app_state: AppState,
    ) -> None:
        self.page = page
        self.app_state = app_state
        self.items = self._load_json(DATA_DIR / "journey_items.json")
        self.pokemon = self._load_json(DATA_DIR / "journey_pokemon.json")
        self.earned_badges = app_state.earned_badges
        self.item_quantities = {
            str(item.get("id")): app_state.get_item_quantity_obtained(
                str(item.get("id"))
            )
            for item in self.items
        }
        self.pokemon_obtained = {
            str(pokemon.get("id")): app_state.is_pokemon_obtained(
                str(pokemon.get("id"))
            )
            for pokemon in self.pokemon
        }
        self._root: ft.Column | None = None

    @staticmethod
    def _load_json(path: Path) -> list[dict[str, Any]]:
        with path.open("r", encoding="utf-8") as file:
            data = json.load(file)
        if not isinstance(data, list):
            raise ValueError(f"Expected a list in {path.name}.")
        return data

    def build(self) -> ft.Control:
        self._root = ft.Column(
            controls=self._build_page_controls(),
            spacing=24,
            width=CONTENT_MAX_WIDTH,
            horizontal_alignment=ft.CrossAxisAlignment.CENTER,
        )
        return self._root

    def _build_page_controls(self) -> list[ft.Control]:
        return [
            self._build_page_intro(),
            ft.ResponsiveRow(
                controls=[
                    self._build_current_objectives_card(),
                    self._build_badge_tracker_card(),
                ],
                columns=12,
                spacing=20,
                run_spacing=20,
            ),
            ft.ResponsiveRow(
                controls=[
                    self._build_journey_checklist_card(),
                    self._build_map_card(),
                ],
                columns=12,
                spacing=20,
                run_spacing=20,
            ),
            ft.ResponsiveRow(
                controls=[self._build_team_planner_card()],
                columns=12,
                spacing=20,
                run_spacing=20,
            ),
        ]

    def _refresh(self) -> None:
        if self._root is None:
            return
        self._root.controls = self._build_page_controls()
        self.page.update()

    async def _earn_next_badge(self) -> None:
        if self.earned_badges >= 8:
            return

        next_badge_count = self.earned_badges + 1
        save_succeeded = await self.app_state.save_earned_badges(
            next_badge_count
        )

        if not save_succeeded:
            self.page.show_dialog(
                ft.SnackBar(
                    content=ft.Text(
                        "Badge progress could not be saved."
                    )
                )
            )
            return

        self.earned_badges = next_badge_count
        self._refresh()

    async def _set_item_quantity(
        self,
        item_id: str,
        quantity: int,
    ) -> None:
        item = next(
            (entry for entry in self.items if str(entry.get("id")) == item_id),
            None,
        )
        if item is None:
            return

        required = max(1, int(item.get("quantity_required", 1)))
        bounded_quantity = max(0, min(quantity, required))
        previous = self.item_quantities.get(item_id, 0)
        if bounded_quantity == previous:
            return

        save_succeeded = await self.app_state.save_item_objective_quantity(
            item_id=item_id,
            quantity_obtained=bounded_quantity,
        )
        if not save_succeeded:
            self._show_save_error("Item progress could not be saved.")
            return

        self.item_quantities[item_id] = bounded_quantity
        self._refresh()

    async def _set_pokemon_obtained(
        self,
        pokemon_id: str,
        obtained: bool,
    ) -> None:
        previous = self.pokemon_obtained.get(pokemon_id, False)
        if obtained == previous:
            return

        save_succeeded = await self.app_state.save_pokemon_objective(
            pokemon_id=pokemon_id,
            obtained=obtained,
        )
        if not save_succeeded:
            self._show_save_error("Pokémon progress could not be saved.")
            return

        self.pokemon_obtained[pokemon_id] = obtained
        self._refresh()

    def _show_save_error(self, message: str) -> None:
        self.page.show_dialog(ft.SnackBar(content=ft.Text(message)))

    def _item_checkbox_handler(
        self,
        checkbox: ft.Checkbox,
        item_id: str,
        required: int,
    ) -> None:
        quantity = required if checkbox.value is True else 0
        self.page.run_task(self._set_item_quantity, item_id, quantity)

    def _pokemon_checkbox_handler(
        self,
        checkbox: ft.Checkbox,
        pokemon_id: str,
    ) -> None:
        self.page.run_task(
            self._set_pokemon_obtained,
            pokemon_id,
            checkbox.value is True,
        )

    @staticmethod
    def _build_page_intro() -> ft.Control:
        return ft.Column(
            controls=[
                ft.Text(
                    "My Journey",
                    size=30,
                    weight=ft.FontWeight.BOLD,
                    color=TEXT_PRIMARY,
                ),
                ft.Text(
                    "Plan what matters before the next battle: track progress, "
                    "review active objectives, and prepare future team additions.",
                    size=15,
                    color=TEXT_SECONDARY,
                    text_align=ft.TextAlign.CENTER,
                ),
            ],
            spacing=6,
            horizontal_alignment=ft.CrossAxisAlignment.CENTER,
        )

    def _item_status(self, item: dict[str, Any]) -> str:
        required = int(item.get("quantity_required", 1))
        item_id = str(item.get("id", ""))
        obtained = self.item_quantities.get(item_id, 0)
        if obtained >= required:
            return "obtained"

        sources = item.get("sources", [])
        if any(
            int(source.get("required_badge", 0)) <= self.earned_badges
            for source in sources
        ):
            return "available"
        return "unavailable"

    def _pokemon_status(self, pokemon: dict[str, Any]) -> str:
        pokemon_id = str(pokemon.get("id", ""))
        if self.pokemon_obtained.get(pokemon_id, False):
            return "obtained"
        required_badge = int(pokemon.get("required_badge", 0))
        return (
            "available"
            if required_badge <= self.earned_badges
            else "unavailable"
        )

    @staticmethod
    def _status_icon(status: str, tooltip: str | None = None) -> ft.Icon:
        if status == "obtained":
            return ft.Icon(
                ft.Icons.CHECK_CIRCLE_ROUNDED,
                color=PRIMARY_BLUE,
                size=22,
                tooltip=tooltip or "Obtained",
            )
        if status == "available":
            return ft.Icon(
                ft.Icons.ERROR_ROUNDED,
                color=SUCCESS,
                size=22,
                tooltip=tooltip or "Available",
            )
        return ft.Icon(
            ft.Icons.BLOCK_ROUNDED,
            color=DANGER,
            size=22,
            tooltip=tooltip or "Unavailable",
        )

    def _build_current_objectives_card(self) -> ft.Control:
        objectives: list[ft.Control] = []

        for item in self.items:
            if self._item_status(item) != "available":
                continue
            objectives.append(
                self._build_objective_row(
                    status="available",
                    title=self._item_display_name(item),
                    detail=self._current_item_source_text(item),
                    action=self._build_item_progress_control(item, compact=True),
                )
            )

        for pokemon in self.pokemon:
            if self._pokemon_status(pokemon) != "available":
                continue
            objectives.append(
                self._build_objective_row(
                    status="available",
                    title=str(pokemon.get("pokemon", "Unknown Pokémon")),
                    detail=self._pokemon_acquisition_text(pokemon),
                    action=self._build_pokemon_progress_control(
                        pokemon,
                        compact=True,
                    ),
                )
            )

        if not objectives:
            objectives.append(
                ft.Text(
                    "No objectives are currently available.",
                    size=14,
                    color=TEXT_MUTED,
                    italic=True,
                )
            )

        return self._build_card(
            title="Current Objectives",
            icon=ft.Icons.FACT_CHECK_OUTLINED,
            subtitle="Top available goals you can act on right now.",
            body=ft.Column(controls=objectives[:3], spacing=10),
            col={"xs": 12, "lg": 6},
        )

    def _build_badge_tracker_card(self) -> ft.Control:
        badges: list[ft.Control] = []

        for index in range(8):
            badge_number = index + 1
            earned = index < self.earned_badges
            next_badge = index == self.earned_badges and self.earned_badges < 8

            if earned:
                icon = ft.Icons.CHECK_ROUNDED
                icon_color = PRIMARY_BLUE
                border_color = PRIMARY_BLUE
                opacity = 1.0
                tooltip = f"Badge {badge_number} earned"
            elif next_badge:
                icon = ft.Icons.SHIELD_OUTLINED
                icon_color = SUCCESS
                border_color = SUCCESS
                opacity = 1.0
                tooltip = f"Earn Badge {badge_number}"
            else:
                icon = ft.Icons.SHIELD_OUTLINED
                icon_color = TEXT_MUTED
                border_color = BORDER_DEFAULT
                opacity = 0.4
                tooltip = f"Badge {badge_number} is locked"

            badge_circle = ft.Container(
                content=ft.Icon(icon, size=28, color=icon_color),
                width=58,
                height=58,
                bgcolor=SURFACE_RAISED,
                border=ft.Border.all(1, border_color),
                border_radius=29,
                alignment=ft.Alignment.CENTER,
                tooltip=tooltip,
                opacity=opacity,
            )

            if next_badge:
                badges.append(
                    ft.GestureDetector(
                        content=badge_circle,
                        on_tap=self._earn_next_badge,
                        mouse_cursor=ft.MouseCursor.CLICK,
                    )
                )
            else:
                badges.append(badge_circle)

        badge_row = ft.Row(
            controls=badges,
            spacing=10,
            run_spacing=10,
            wrap=True,
            alignment=ft.MainAxisAlignment.CENTER,
        )

        progress_row_controls: list[ft.Control] = [
            ft.Text(
                f"{self.earned_badges} of 8 badges earned",
                size=13,
                color=TEXT_SECONDARY,
            ),
        ]
        progress_row = ft.Row(
            controls=progress_row_controls,
            alignment=ft.MainAxisAlignment.START,
            vertical_alignment=ft.CrossAxisAlignment.CENTER,
            wrap=True,
        )

        controls: list[ft.Control] = []
        controls.append(badge_row)
        controls.append(progress_row)

        return self._build_card(
            title="Badge Tracker",
            icon=ft.Icons.MILITARY_TECH_OUTLINED,
            subtitle=(
                "Select the next badge to record your progress and "
                "unlock eligible objectives."
            ),
            body=ft.Column(controls=controls, spacing=14),
            col={"xs": 12, "lg": 6},
        )

    def _build_journey_checklist_card(self) -> ft.Control:
        rows: list[ft.DataRow] = []
        for item in self.items:
            status = self._item_status(item)
            rows.append(
                ft.DataRow(
                    cells=[
                        ft.DataCell(
                            self._status_icon(
                                status,
                                self._item_status_tooltip(item, status),
                            )
                        ),
                        ft.DataCell(
                            ft.Text(
                                self._item_display_name(item),
                                color=TEXT_PRIMARY,
                                weight=ft.FontWeight.W_600,
                            )
                        ),
                        ft.DataCell(
                            ft.Text(
                                self._item_location_text(item),
                                color=TEXT_SECONDARY,
                                size=13,
                            )
                        ),
                        ft.DataCell(
                            self._build_item_obtained_action(item, status)
                        ),
                    ],
                )
            )

        table = ft.DataTable(
            columns=[
                self._column("Status"),
                self._column("Item"),
                self._column("Location"),
                self._column("Mark as obtained"),
            ],
            rows=rows,
            border=ft.Border.all(1, BORDER_DEFAULT),
            border_radius=12,
            heading_row_color=SURFACE_RAISED,
            column_spacing=18,
            data_row_min_height=52,
            data_row_max_height=72,
        )

        return self._build_card(
            title="Journey Checklist",
            icon=ft.Icons.CHECKLIST_ROUNDED,
            subtitle="Availability and completion status remain separate from progress controls.",
            body=ft.Row(controls=[table], scroll=ft.ScrollMode.AUTO),
            col={"xs": 12, "lg": 6},
        )

    def _build_map_card(self) -> ft.Control:
        return self._build_card(
            title="Galar Map",
            icon=ft.Icons.MAP_OUTLINED,
            subtitle="Journey objective markers will be added in a later pass.",
            body=ft.Container(
                content=ft.Image(
                    src="Galar_Map.png",
                    fit=ft.BoxFit.CONTAIN,
                    semantics_label="Map of the Galar region",
                ),
                width=520,
                height=700,
                bgcolor=SURFACE_RAISED,
                border=ft.Border.all(1, BORDER_DEFAULT),
                border_radius=12,
                padding=10,
                alignment=ft.Alignment.TOP_CENTER,
                clip_behavior=ft.ClipBehavior.ANTI_ALIAS,
            ),
            col={"xs": 12, "lg": 6},
        )

    def _build_team_planner_card(self) -> ft.Control:
        rows: list[ft.DataRow] = []

        for pokemon in self.pokemon:
            status = self._pokemon_status(pokemon)
            encounter = self._primary_encounter(pokemon)

            pokemon_cell_controls: list[ft.Control] = [
                self._status_icon(status),
                ft.Column(
                    controls=[
                        ft.Text(
                            str(pokemon.get("pokemon", "Unknown")),
                            color=TEXT_PRIMARY,
                            weight=ft.FontWeight.BOLD,
                            size=15,
                        ),
                        ft.Text(
                            self._pokemon_acquisition_text(pokemon),
                            color=TEXT_SECONDARY,
                            size=13,
                        ),
                        ft.Text(
                            str(pokemon.get("evolution_summary", "")),
                            color=TEXT_MUTED,
                            size=12,
                            italic=True,
                        ),
                    ],
                    spacing=2,
                ),
            ]

            rows.append(
                ft.DataRow(
                    cells=[
                        ft.DataCell(
                            ft.Row(
                                controls=pokemon_cell_controls,
                                spacing=10,
                                vertical_alignment=ft.CrossAxisAlignment.CENTER,
                            )
                        ),
                        ft.DataCell(
                            ft.Text(
                                self._pokemon_location_text(pokemon),
                                color=TEXT_SECONDARY,
                                size=13,
                            )
                        ),
                        ft.DataCell(
                            ft.Text(
                                self._pokemon_method_text(pokemon, encounter),
                                color=TEXT_SECONDARY,
                                size=13,
                            )
                        ),
                        ft.DataCell(
                            ft.Text(
                                self._pokemon_weather_text(encounter),
                                color=TEXT_SECONDARY,
                                size=13,
                            )
                        ),
                        ft.DataCell(
                            ft.Text(
                                self._pokemon_rarity_text(pokemon, encounter),
                                color=TEXT_SECONDARY,
                                size=13,
                            )
                        ),
                        ft.DataCell(
                            ft.Text(
                                self._pokemon_level_text(encounter),
                                color=TEXT_SECONDARY,
                                size=13,
                            )
                        ),
                        ft.DataCell(self._pokemon_more_locations_control(pokemon)),
                        ft.DataCell(
                            self._build_pokemon_obtained_action(
                                pokemon,
                                status,
                            )
                        ),
                    ]
                )
            )

        table = ft.DataTable(
            columns=[
                self._column("Pokémon"),
                self._column("Location"),
                self._column("Method"),
                self._column("Weather"),
                self._column("Rarity"),
                self._column("Level"),
                self._column("More Locations"),
                self._column("Mark as acquired"),
            ],
            rows=rows,
            border=ft.Border.all(1, BORDER_DEFAULT),
            border_radius=12,
            heading_row_color=SURFACE_RAISED,
            column_spacing=20,
            data_row_min_height=76,
            data_row_max_height=104,
        )

        return self._build_card(
            title="Team Planner",
            icon=ft.Icons.GROUP_ADD_OUTLINED,
            subtitle=(
                "Planned final team members with acquisition, encounter, "
                "and evolution guidance."
            ),
            body=ft.Row(controls=[table], scroll=ft.ScrollMode.AUTO),
            col={"xs": 12},
        )

    @staticmethod
    def _column(label: str) -> ft.DataColumn:
        return ft.DataColumn(
            label=ft.Text(
                label,
                weight=ft.FontWeight.BOLD,
                color=TEXT_PRIMARY,
            )
        )

    def _build_objective_row(
        self,
        *,
        status: str,
        title: str,
        detail: str,
        action: ft.Control | None = None,
    ) -> ft.Control:
        return ft.Container(
            content=ft.Row(
                controls=[
                    self._status_icon(status),
                    ft.Column(
                        controls=[
                            ft.Text(
                                title,
                                color=TEXT_PRIMARY,
                                weight=ft.FontWeight.W_600,
                                size=14,
                            ),
                            ft.Text(detail, color=TEXT_SECONDARY, size=12),
                        ],
                        spacing=2,
                        expand=True,
                    ),
                    *([action] if action is not None else []),
                ],
                spacing=10,
                vertical_alignment=ft.CrossAxisAlignment.CENTER,
            ),
            padding=12,
            bgcolor=SURFACE_RAISED,
            border_radius=12,
        )

    @staticmethod
    def _item_display_name(item: dict[str, Any]) -> str:
        quantity = int(item.get("quantity_required", 1))
        name = str(item.get("name", "Unknown item"))
        return f"{name} ×{quantity}" if quantity > 1 else name

    def _item_status_tooltip(
        self,
        item: dict[str, Any],
        status: str,
    ) -> str:
        required = int(item.get("quantity_required", 1))
        obtained = self.item_quantities.get(str(item.get("id", "")), 0)
        if status == "obtained":
            return f"Obtained ({obtained}/{required})"
        if obtained > 0:
            return f"In progress ({obtained}/{required})"
        return status.title()

    def _build_item_obtained_action(
        self,
        item: dict[str, Any],
        status: str,
    ) -> ft.Control:
        if status == "unavailable":
            return ft.Text("—", color=TEXT_MUTED, text_align=ft.TextAlign.CENTER)
        return self._build_item_progress_control(item)

    def _build_pokemon_obtained_action(
        self,
        pokemon: dict[str, Any],
        status: str,
    ) -> ft.Control:
        if status == "unavailable":
            return ft.Text("—", color=TEXT_MUTED, text_align=ft.TextAlign.CENTER)
        return self._build_pokemon_progress_control(pokemon)

    def _build_item_progress_control(
        self,
        item: dict[str, Any],
        *,
        compact: bool = False,
    ) -> ft.Control:
        item_id = str(item.get("id", ""))
        required = max(1, int(item.get("quantity_required", 1)))
        obtained = min(self.item_quantities.get(item_id, 0), required)
        status = self._item_status(item)
        enabled = status != "unavailable"

        if required == 1:
            checkbox = ft.Checkbox(
                value=obtained >= 1,
                disabled=not enabled,
                tooltip=self._item_status_tooltip(item, status),
                active_color=PRIMARY_BLUE,
            )
            checkbox.on_change = lambda: self._item_checkbox_handler(
                checkbox, item_id, required
            )
            return checkbox

        decrement = ft.IconButton(
            icon=ft.Icons.REMOVE_ROUNDED,
            icon_size=16,
            tooltip="Remove one obtained",
            disabled=not enabled or obtained <= 0,
            on_click=lambda: self.page.run_task(
                self._set_item_quantity, item_id, obtained - 1
            ),
        )
        increment = ft.IconButton(
            icon=ft.Icons.ADD_ROUNDED,
            icon_size=16,
            tooltip="Mark one obtained",
            disabled=not enabled or obtained >= required,
            on_click=lambda: self.page.run_task(
                self._set_item_quantity, item_id, obtained + 1
            ),
        )
        progress = ft.Text(
            f"{obtained}/{required}",
            size=12 if compact else 13,
            color=(PRIMARY_BLUE if obtained >= required else TEXT_SECONDARY),
            weight=ft.FontWeight.W_600,
        )
        quantity_controls: list[ft.Control] = [
            decrement,
            progress,
            increment,
        ]
        return ft.Row(
            controls=quantity_controls,
            spacing=0,
            tight=True,
            vertical_alignment=ft.CrossAxisAlignment.CENTER,
        )

    def _build_pokemon_progress_control(
        self,
        pokemon: dict[str, Any],
        *,
        compact: bool = False,
    ) -> ft.Control:
        pokemon_id = str(pokemon.get("id", ""))
        obtained = self.pokemon_obtained.get(pokemon_id, False)
        status = self._pokemon_status(pokemon)
        checkbox = ft.Checkbox(
            value=obtained,
            disabled=status == "unavailable",
            tooltip="Caught" if obtained else status.title(),
            active_color=PRIMARY_BLUE,
            scale=0.9 if compact else 1.0,
        )
        checkbox.on_change = lambda: self._pokemon_checkbox_handler(
            checkbox, pokemon_id
        )
        return checkbox

    def _available_sources(self, item: dict[str, Any]) -> list[dict[str, Any]]:
        return [
            source
            for source in item.get("sources", [])
            if int(source.get("required_badge", 0)) <= self.earned_badges
        ]

    def _current_item_source_text(self, item: dict[str, Any]) -> str:
        available = self._available_sources(item)
        if not available:
            return "Locked"
        return str(available[0].get("location", "Location unavailable"))

    def _item_location_text(self, item: dict[str, Any]) -> str:
        sources = item.get("sources", [])
        available = self._available_sources(item)
        selected = available[0] if available else (sources[0] if sources else {})
        location = str(selected.get("location", "Location unavailable"))

        if len(sources) > 1:
            return f"{location} + {len(sources) - 1} more"
        return location

    @staticmethod
    def _primary_encounter(pokemon: dict[str, Any]) -> dict[str, Any]:
        acquisition = pokemon.get("primary_acquisition", {})
        encounters = acquisition.get("encounters", [])
        if encounters:
            return encounters[0]
        return {}

    @staticmethod
    def _pokemon_method_text(
        pokemon: dict[str, Any],
        encounter: dict[str, Any],
    ) -> str:
        acquisition = pokemon.get("primary_acquisition", {})
        raw_method = encounter.get("method") or acquisition.get("method", "")
        if not raw_method:
            return "Details forthcoming"
        method = str(raw_method).replace("_", " ").title()
        method = method.replace("Max Raid Battle", "Max Raid")
        return method

    @staticmethod
    def _pokemon_weather_text(encounter: dict[str, Any]) -> str:
        weather = encounter.get("weather")
        return str(weather) if weather else "—"

    @staticmethod
    def _pokemon_rarity_text(
        pokemon: dict[str, Any],
        encounter: dict[str, Any],
    ) -> str:
        rarity = encounter.get("rarity_percent")
        if rarity is not None:
            return f"{rarity}%"

        acquisition = pokemon.get("primary_acquisition", {})
        if acquisition.get("method") == "max_raid_battle":
            return "Raid"
        return "—"

    @staticmethod
    def _pokemon_level_text(encounter: dict[str, Any]) -> str:
        min_level = encounter.get("level_min")
        max_level = encounter.get("level_max")

        if min_level is None and max_level is None:
            return "Varies"

        if min_level == max_level:
            return str(min_level)

        if min_level is None:
            return str(max_level)

        if max_level is None:
            return str(min_level)

        return f"{min_level}–{max_level}"

    @staticmethod
    def _pokemon_more_locations_control(
        pokemon: dict[str, Any],
    ) -> ft.Control:
        source_url = str(pokemon.get("source_url", "")).strip()
        if not source_url:
            return ft.Text("—", color=TEXT_MUTED, size=13)

        return ft.TextButton(
            "View locations",
            url=source_url,
            icon=ft.Icons.OPEN_IN_NEW_ROUNDED,
        )

    @staticmethod
    def _pokemon_acquisition_text(pokemon: dict[str, Any]) -> str:
        final_name = str(pokemon.get("pokemon", "Unknown"))
        acquire_as = str(pokemon.get("acquire_as", final_name))
        return (
            f"Catch {acquire_as}"
            if acquire_as != final_name
            else f"Catch {final_name}"
        )

    @staticmethod
    def _pokemon_location_text(pokemon: dict[str, Any]) -> str:
        acquisition = pokemon.get("primary_acquisition", {})
        return str(acquisition.get("location", "Location unavailable"))

    @staticmethod
    def _pokemon_encounter_text(pokemon: dict[str, Any]) -> str:
        acquisition = pokemon.get("primary_acquisition", {})
        method = str(acquisition.get("method", "")).replace("_", " ").title()
        encounters = acquisition.get("encounters", [])

        if encounters:
            encounter = encounters[0]
            weather = str(encounter.get("weather", ""))
            min_level = encounter.get("level_min")
            max_level = encounter.get("level_max")
            level_text = ""
            if min_level is not None and max_level is not None:
                level_text = (
                    f"Lv. {min_level}"
                    if min_level == max_level
                    else f"Lv. {min_level}–{max_level}"
                )
            return " · ".join(
                value for value in [method, weather, level_text] if value
            )

        note = str(acquisition.get("availability_note", ""))
        return note or method or "Details forthcoming"

    @staticmethod
    def _build_card(
        *,
        title: str,
        icon: ft.IconData,
        subtitle: str,
        body: ft.Control,
        col: Any,
    ) -> ft.Container:
        controls: list[ft.Control] = [
            ft.Row(
                controls=[
                    ft.Icon(icon, size=25, color=PRIMARY_BLUE),
                    ft.Text(
                        title,
                        size=23,
                        weight=ft.FontWeight.BOLD,
                        color=TEXT_PRIMARY,
                        expand=True,
                    ),
                ],
                spacing=10,
                vertical_alignment=ft.CrossAxisAlignment.CENTER,
            ),
            ft.Text(subtitle, size=14, color=TEXT_SECONDARY),
            ft.Divider(color=BORDER_DEFAULT, height=1),
            body,
        ]

        return ft.Container(
            content=ft.Column(controls=controls, spacing=16),
            padding=CARD_PADDING,
            bgcolor=SURFACE,
            border=ft.Border.all(1, BORDER_DEFAULT),
            border_radius=CARD_RADIUS,
            col=col,
        )