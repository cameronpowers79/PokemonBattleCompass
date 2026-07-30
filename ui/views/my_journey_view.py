"""My Journey view with persistent badge and objective progression.

Badge, item, and planned-Pokémon changes save immediately. The graphical badge
tracker includes earned-badge celebrations; map markers remain deferred.
"""

from __future__ import annotations

import asyncio
import json
from copy import deepcopy
from pathlib import Path
from typing import Any, Callable

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

BADGE_LAYERS = [
    ("Grass Badge", "badges/grass_badge.png"),
    ("Water Badge", "badges/water_badge.png"),
    ("Fire Badge", "badges/fire_badge.png"),
    ("Fighting Badge", "badges/fighting_badge.png"),
    ("Fairy Badge", "badges/fairy_badge.png"),
    ("Rock Badge", "badges/rock_badge.png"),
    ("Dark Badge", "badges/dark_badge.png"),
    ("Dragon Badge", "badges/dragon_badge.png"),
]

BADGE_IMAGE_SIZE = (781, 779)

BADGE_CROP_BOUNDS = {
    "Grass Badge": (300, 445, 661, 757),
    "Water Badge": (502, 65, 744, 327),
    "Fire Badge": (257, 191, 523, 618),
    "Fighting Badge": (57, 399, 346, 748),
    "Fairy Badge": (514, 271, 761, 629),
    "Rock Badge": (286, 15, 581, 225),
    "Dark Badge": (184, 111, 397, 446),
    "Dragon Badge": (18, 37, 301, 559),
}

BADGE_FRAME_ASSET = "badges/badge_coin_frame.png"


class MyJourneyView:
    """Render My Journey fixture data with saved badge progression."""

    def __init__(
        self,
        page: ft.Page,
        *,
        app_state: AppState,
        on_go_to_my_team: Callable[[str], None] | None = None,
    ) -> None:
        self.page = page
        self.app_state = app_state
        self.on_go_to_my_team = on_go_to_my_team
        self.items = self._load_json(DATA_DIR / "journey_items.json")
        self.pokemon = self._load_json(DATA_DIR / "journey_pokemon.json")
        self.earned_badges = app_state.earned_badges
        self.derived_item_requirements = (
            self._build_derived_item_requirements()
        )
        self.item_objectives = self._load_item_objectives()
        self.item_quantities = {
            item_id: int(record.get("quantity_obtained", 0))
            for item_id, record in self.item_objectives.items()
        }
        self.pokemon_obtained = {
            str(pokemon.get("id")): app_state.is_pokemon_obtained(
                str(pokemon.get("id"))
            )
            for pokemon in self.pokemon
        }
        self._root: ft.Column | None = None
        self._caught_stage_selector: ft.Dropdown | None = None
        self._add_item_selector: ft.Dropdown | None = None
        self._add_item_quantity: ft.TextField | None = None

        self._badge_celebration_badge: ft.Container | None = None
        self._badge_celebration_shine: ft.Container | None = None
        self._badge_celebration_sparkles: list[ft.Container] = []

    @staticmethod
    def _load_json(path: Path) -> list[dict[str, Any]]:
        with path.open("r", encoding="utf-8") as file:
            data = json.load(file)
        if not isinstance(data, list):
            raise ValueError(f"Expected a list in {path.name}.")
        return data

    def _build_derived_item_requirements(self) -> dict[str, int]:
        """Aggregate evolution-item quantities required by the team plan."""

        requirements: dict[str, int] = {}
        for pokemon in self.pokemon:
            for requirement in pokemon.get("required_items", []):
                if not isinstance(requirement, dict):
                    continue
                item_id = str(requirement.get("item_id", "")).strip()
                quantity = requirement.get("quantity", 0)
                if (
                    not item_id
                    or not isinstance(quantity, int)
                    or isinstance(quantity, bool)
                    or quantity <= 0
                ):
                    continue
                requirements[item_id] = (
                    requirements.get(item_id, 0) + quantity
                )
        return requirements

    def _load_item_objectives(self) -> dict[str, dict[str, int]]:
        """Load persisted checklist rows or initialize the fixture checklist."""

        journey_state = self.app_state.my_journey_data
        stored_records = journey_state.get("item_objectives", [])
        initialized = (
            journey_state.get("checklist_initialized") is True
        )

        stored_by_id: dict[str, dict[str, Any]] = {
            str(record.get("id")): record
            for record in stored_records
            if isinstance(record, dict) and record.get("id")
        }

        objectives: dict[str, dict[str, int]] = {}

        if initialized:
            for item_id, record in stored_by_id.items():
                obtained = record.get("quantity_obtained", 0)
                manual = record.get("manual_quantity_required", 0)
                objectives[item_id] = {
                    "quantity_obtained": (
                        obtained
                        if isinstance(obtained, int)
                        and not isinstance(obtained, bool)
                        and obtained >= 0
                        else 0
                    ),
                    "manual_quantity_required": (
                        manual
                        if isinstance(manual, int)
                        and not isinstance(manual, bool)
                        and manual >= 0
                        else 0
                    ),
                }
        else:
            # Backward-compatible fixture initialization: preserve the
            # checklist that existed before editing was introduced.
            for item in self.items:
                item_id = str(item.get("id", "")).strip()
                if not item_id:
                    continue
                catalog_required = max(
                    1,
                    int(item.get("quantity_required", 1)),
                )
                derived = self.derived_item_requirements.get(
                    item_id,
                    0,
                )
                legacy = stored_by_id.get(item_id, {})
                obtained = legacy.get("quantity_obtained", 0)
                objectives[item_id] = {
                    "quantity_obtained": (
                        obtained
                        if isinstance(obtained, int)
                        and not isinstance(obtained, bool)
                        and obtained >= 0
                        else 0
                    ),
                    "manual_quantity_required": max(
                        0,
                        catalog_required - derived,
                    ),
                }

        # Team-planner requirements always keep their linked item present.
        for item_id in self.derived_item_requirements:
            objectives.setdefault(
                item_id,
                {
                    "quantity_obtained": 0,
                    "manual_quantity_required": 0,
                },
            )

        return objectives

    def _required_item_quantity(self, item_id: str) -> int:
        record = self.item_objectives.get(item_id, {})
        manual = int(record.get("manual_quantity_required", 0))
        derived = self.derived_item_requirements.get(item_id, 0)
        return manual + derived

    def _checklist_items(self) -> list[dict[str, Any]]:
        return [
            item
            for item in self.items
            if self._required_item_quantity(
                str(item.get("id", ""))
            ) > 0
        ]

    def _serialized_item_objectives(self) -> list[dict]:
        records: list[dict] = []
        for item_id, record in self.item_objectives.items():
            required = self._required_item_quantity(item_id)
            if required <= 0:
                continue
            obtained = min(
                int(record.get("quantity_obtained", 0)),
                required,
            )
            records.append({
                "id": item_id,
                "quantity_obtained": obtained,
                "manual_quantity_required": int(
                    record.get("manual_quantity_required", 0)
                ),
            })
        return records

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

    def refresh_from_app_state(self) -> None:
        """Reload saved Journey progress after party or Box changes."""

        self.earned_badges = self.app_state.earned_badges
        self.item_objectives = self._load_item_objectives()
        self.item_quantities = {
            item_id: int(record.get("quantity_obtained", 0))
            for item_id, record in self.item_objectives.items()
        }
        self.pokemon_obtained = {
            str(pokemon.get("id")): self.app_state.is_pokemon_obtained(
                str(pokemon.get("id"))
            )
            for pokemon in self.pokemon
        }
        self._refresh()

    async def _earn_next_badge(self) -> None:
        """Persist the next badge and show its celebration dialog."""

        if self.earned_badges >= len(BADGE_LAYERS):
            return

        earned_badge_index = self.earned_badges
        next_badge_count = earned_badge_index + 1

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
        self._show_badge_celebration(earned_badge_index)

    def _build_centered_badge_image(
    self,
    badge_name: str,
    badge_asset: str,
    viewport_size: int,
    tint: str | None = None,
) -> ft.Control:
        """Crop a badge layer to its visible badge and center it."""

        source_width, source_height = BADGE_IMAGE_SIZE
        left, top, right, bottom = BADGE_CROP_BOUNDS[badge_name]

        crop_width = right - left
        crop_height = bottom - top

        padding = 24
        available_size = viewport_size - padding * 2

        scale = min(
            available_size / crop_width,
            available_size / crop_height,
        )

        rendered_width = source_width * scale
        rendered_height = source_height * scale

        visible_width = crop_width * scale
        visible_height = crop_height * scale

        image_left = (
            viewport_size / 2
            - visible_width / 2
            - left * scale
        )
        image_top = (
            viewport_size / 2
            - visible_height / 2
            - top * scale
        )

        badge_image = ft.Image(
            src=badge_asset,
            width=rendered_width,
            height=rendered_height,
            fit=ft.BoxFit.FILL,
            left=image_left,
            top=image_top,
            semantics_label=badge_name,
        )

        if tint is not None:
            badge_image.color = tint
            badge_image.color_blend_mode = ft.BlendMode.SRC_IN

        return ft.Stack(
            controls=[badge_image],
            width=viewport_size,
            height=viewport_size,
            clip_behavior=ft.ClipBehavior.HARD_EDGE,
        )

    def _show_badge_celebration(
        self,
        badge_index: int,
    ) -> None:
        """Celebrate a newly earned isolated badge."""

        if badge_index < 0 or badge_index >= len(BADGE_LAYERS):
            return

        badge_name, badge_asset = BADGE_LAYERS[badge_index]
        celebration_size = 260

        centered_badge = self._build_centered_badge_image(
            badge_name,
            badge_asset,
            celebration_size,
        )

        centered_badge_glow = self._build_centered_badge_image(
            badge_name,
            badge_asset,
            celebration_size,
            tint=ft.Colors.WHITE,
        )

        self._badge_celebration_badge = ft.Container(
            content=centered_badge,
            width=celebration_size,
            height=celebration_size,
            alignment=ft.Alignment.CENTER,
            opacity=0.0,
            scale=0.72,
            animate_opacity=ft.Animation(
                260,
                ft.AnimationCurve.EASE_OUT,
            ),
            animate_scale=ft.Animation(
                360,
                ft.AnimationCurve.EASE_OUT_BACK,
            ),
        )

        self._badge_celebration_shine = ft.Container(
            content=centered_badge_glow,
            width=celebration_size,
            height=celebration_size,
            alignment=ft.Alignment.CENTER,
            opacity=0.0,
            scale=1.0,
            animate_opacity=ft.Animation(
                180,
                ft.AnimationCurve.EASE_IN_OUT,
            ),
            animate_scale=ft.Animation(
                240,
                ft.AnimationCurve.EASE_OUT,
            ),
        )

        sparkle_positions = [
            (22, 42, 17),
            (194, 34, 14),
            (212, 174, 16),
            (34, 190, 14),
            (121, 14, 12),
            (122, 222, 13),
        ]

        self._badge_celebration_sparkles = []

        stack_controls: list[ft.Control] = [
            self._badge_celebration_badge,
            self._badge_celebration_shine,
        ]

        for left, top, size in sparkle_positions:
            sparkle = ft.Container(
                content=ft.Icon(
                    ft.Icons.AUTO_AWESOME_ROUNDED,
                    size=size,
                    color=ft.Colors.AMBER_200,
                ),
                left=left,
                top=top,
                opacity=0.0,
                scale=0.55,
                animate_opacity=ft.Animation(
                    180,
                    ft.AnimationCurve.EASE_IN_OUT,
                ),
                animate_scale=ft.Animation(
                    220,
                    ft.AnimationCurve.EASE_OUT_BACK,
                ),
            )
            self._badge_celebration_sparkles.append(sparkle)
            stack_controls.append(sparkle)

        dialog = ft.AlertDialog()
        dialog.modal = False
        dialog.title = ft.Text(
            "Congratulations!",
            weight=ft.FontWeight.BOLD,
            color=TEXT_PRIMARY,
            text_align=ft.TextAlign.CENTER,
        )
        dialog.content = ft.Column(
            controls=[
                ft.Container(
                    content=ft.Stack(
                        controls=stack_controls,
                        width=celebration_size,
                        height=celebration_size,
                        clip_behavior=ft.ClipBehavior.NONE,
                    ),
                    width=celebration_size,
                    height=celebration_size,
                    alignment=ft.Alignment.CENTER,
                ),
                ft.Text(
                    f"You earned the {badge_name}!",
                    size=20,
                    weight=ft.FontWeight.BOLD,
                    color=TEXT_PRIMARY,
                    text_align=ft.TextAlign.CENTER,
                ),
                ft.Text(
                    (
                        "Any Journey objectives unlocked by this badge "
                        "are now available."
                    ),
                    size=14,
                    color=TEXT_SECONDARY,
                    text_align=ft.TextAlign.CENTER,
                ),
            ],
            spacing=12,
            tight=True,
            horizontal_alignment=ft.CrossAxisAlignment.CENTER,
        )
        dialog.actions = [
            ft.Button(
                content="Continue",
                on_click=self._dismiss_badge_celebration,
            )
        ]
        dialog.actions_alignment = ft.MainAxisAlignment.CENTER
        dialog.on_dismiss = self._clear_badge_celebration_state

        self.page.show_dialog(dialog)
        self.page.run_task(self._animate_badge_celebration)

    async def _animate_badge_celebration(self) -> None:
        """Run the isolated badge pop, sparkle burst, and gleam."""

        await asyncio.sleep(0.08)

        if self._badge_celebration_badge is None:
            return

        self._badge_celebration_badge.opacity = 1.0
        self._badge_celebration_badge.scale = 1.0

        for sparkle in self._badge_celebration_sparkles:
            sparkle.opacity = 1.0
            sparkle.scale = 1.0

        self.page.update()

        await asyncio.sleep(0.34)

        if self._badge_celebration_shine is not None:
            self._badge_celebration_shine.opacity = 0.38
            self._badge_celebration_shine.scale = 1.045
            self.page.update()

        await asyncio.sleep(0.22)

        if self._badge_celebration_shine is not None:
            self._badge_celebration_shine.opacity = 0.0
            self._badge_celebration_shine.scale = 1.0

        for sparkle in self._badge_celebration_sparkles:
            sparkle.opacity = 0.0
            sparkle.scale = 0.72

        self.page.update()

        await asyncio.sleep(0.28)

        if self._badge_celebration_shine is not None:
            self._badge_celebration_shine.opacity = 0.28
            self._badge_celebration_shine.scale = 1.025
            self.page.update()

            await asyncio.sleep(0.18)

            self._badge_celebration_shine.opacity = 0.0
            self._badge_celebration_shine.scale = 1.0
            self.page.update()

    def _dismiss_badge_celebration(
        self,
        event: ft.Event[ft.Button],
    ) -> None:
        """Dismiss the badge celebration dialog."""

        del event
        self.page.pop_dialog()
        self._reset_badge_celebration_state()
        self.page.update()

    def _clear_badge_celebration_state(self) -> None:
        """Clear animation references after blur-dismissal."""

        self._reset_badge_celebration_state()

    def _reset_badge_celebration_state(self) -> None:
        """Release transient celebration controls."""

        self._badge_celebration_badge = None
        self._badge_celebration_shine = None
        self._badge_celebration_sparkles = []

    async def _set_item_quantity(
        self,
        item_id: str,
        quantity: int,
    ) -> None:
        required = self._required_item_quantity(item_id)
        if required <= 0:
            return

        bounded_quantity = max(0, min(quantity, required))
        previous_state = deepcopy(self.item_objectives)
        record = self.item_objectives.setdefault(
            item_id,
            {
                "quantity_obtained": 0,
                "manual_quantity_required": 0,
            },
        )
        previous = int(record.get("quantity_obtained", 0))
        if bounded_quantity == previous:
            return

        record["quantity_obtained"] = bounded_quantity
        save_succeeded = await self.app_state.save_item_checklist(
            self._serialized_item_objectives()
        )
        if not save_succeeded:
            self.item_objectives = previous_state
            self._show_save_error("Item progress could not be saved.")
            return

        self.item_quantities[item_id] = bounded_quantity
        self._refresh()

    async def _add_item_objective(
        self,
        item_id: str,
        quantity: int,
    ) -> None:
        """Add or increment a manual checklist objective."""

        if quantity <= 0:
            return

        previous_state = deepcopy(self.item_objectives)
        record = self.item_objectives.setdefault(
            item_id,
            {
                "quantity_obtained": 0,
                "manual_quantity_required": 0,
            },
        )
        record["manual_quantity_required"] = (
            int(record.get("manual_quantity_required", 0))
            + quantity
        )

        save_succeeded = await self.app_state.save_item_checklist(
            self._serialized_item_objectives()
        )
        if not save_succeeded:
            self.item_objectives = previous_state
            self._show_save_error(
                "The checklist objective could not be added."
            )
            return

        self.item_quantities[item_id] = int(
            record.get("quantity_obtained", 0)
        )
        self._refresh()

    async def _remove_manual_item_objective(
        self,
        item_id: str,
    ) -> None:
        """Remove the manual portion while retaining team-required quantity."""

        record = self.item_objectives.get(item_id)
        if record is None:
            return

        manual = int(record.get("manual_quantity_required", 0))
        if manual <= 0:
            return

        previous_state = deepcopy(self.item_objectives)
        record["manual_quantity_required"] = 0

        required = self._required_item_quantity(item_id)
        record["quantity_obtained"] = min(
            int(record.get("quantity_obtained", 0)),
            required,
        )

        if required <= 0:
            self.item_objectives.pop(item_id, None)

        save_succeeded = await self.app_state.save_item_checklist(
            self._serialized_item_objectives()
        )
        if not save_succeeded:
            self.item_objectives = previous_state
            self._show_save_error(
                "The checklist objective could not be removed."
            )
            return

        self.item_quantities = {
            objective_id: int(
                objective.get("quantity_obtained", 0)
            )
            for objective_id, objective in self.item_objectives.items()
        }
        self._refresh()

    def _show_save_error(self, message: str) -> None:
        """Show a concise error when Journey progress cannot be saved."""

        self.page.show_dialog(
            ft.SnackBar(
                content=ft.Text(message),
            )
        )

    def _item_checkbox_handler(
        self,
        checkbox: ft.Checkbox,
        item_id: str,
        required: int,
    ) -> None:
        """Persist a single-quantity item's checked or unchecked state."""

        quantity = required if checkbox.value is True else 0
        self.page.run_task(
            self._set_item_quantity,
            item_id,
            quantity,
        )

    @staticmethod
    def _pokemon_family_stages(
        pokemon: dict[str, Any],
    ) -> list[str]:
        """Return catchable/evolution stages in acquisition order."""

        stages: list[str] = []

        acquire_as = str(pokemon.get("acquire_as") or "").strip()
        if acquire_as:
            stages.append(acquire_as)

        for step in pokemon.get("evolution_steps", []):
            if not isinstance(step, dict):
                continue
            from_name = str(step.get("from") or "").strip()
            to_name = str(step.get("to") or "").strip()
            if from_name and from_name not in stages:
                stages.append(from_name)
            if to_name and to_name not in stages:
                stages.append(to_name)

        final_name = str(pokemon.get("pokemon") or "").strip()
        if final_name and final_name not in stages:
            stages.append(final_name)

        return stages or ["Pokémon"]

    def _show_pokemon_acquired_prompt(
        self,
        pokemon: dict[str, Any],
    ) -> None:
        """Choose the caught evolution stage, then open a prefilled editor row."""

        stages = self._pokemon_family_stages(pokemon)
        default_stage = stages[0]

        self._caught_stage_selector = ft.Dropdown(
            label="Which Pokémon did you catch?",
            value=default_stage,
            options=[
                ft.DropdownOption(key=stage, text=stage)
                for stage in stages
            ],
            width=320,
        )

        dialog = ft.AlertDialog()
        dialog.modal = True
        dialog.title = ft.Text(
            "Congratulations!",
            weight=ft.FontWeight.BOLD,
        )
        dialog.content = ft.Column(
            controls=[
                ft.Text(
                    (
                        "Choose the evolution stage you caught. My Team will "
                        "open with that Pokémon's name already entered so you "
                        "can add the rest of its information."
                    ),
                    color=TEXT_SECONDARY,
                ),
                self._caught_stage_selector,
                ft.Text(
                    (
                        "Saving the Pokémon to either your active party or "
                        "My Box will mark this Journey objective as acquired."
                    ),
                    color=TEXT_MUTED,
                    size=12,
                ),
            ],
            spacing=14,
            tight=True,
        )

        actions: list[ft.Control] = [
            ft.Button(
                content="Not Yet",
                on_click=self._close_pokemon_acquired_prompt,
            )
        ]
        if self.on_go_to_my_team is not None:
            actions.append(
                ft.Button(
                    content="Add in My Team",
                    icon=ft.Icons.GROUP_ROUNDED,
                    bgcolor=PRIMARY_BLUE,
                    color=TEXT_PRIMARY,
                    icon_color=TEXT_PRIMARY,
                    on_click=self._go_to_my_team_from_prompt,
                )
            )
        dialog.actions = actions
        dialog.actions_alignment = ft.MainAxisAlignment.END
        self.page.show_dialog(dialog)

    def _close_pokemon_acquired_prompt(
        self,
        event: ft.Event[ft.Button] | None = None,
    ) -> None:
        del event
        self._caught_stage_selector = None
        self.page.pop_dialog()
        self.page.update()

    def _go_to_my_team_from_prompt(
        self,
        event: ft.Event[ft.Button],
    ) -> None:
        del event

        selected_stage = ""
        if self._caught_stage_selector is not None:
            selected_stage = str(
                self._caught_stage_selector.value or ""
            ).strip()

        if not selected_stage:
            return

        self._caught_stage_selector = None
        self.page.pop_dialog()

        if self.on_go_to_my_team is not None:
            self.on_go_to_my_team(selected_stage)

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
        item_id = str(item.get("id", ""))
        required = self._required_item_quantity(item_id)
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

        for item in self._checklist_items():
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
                    action=self._build_pokemon_obtained_action(
                        pokemon,
                        "available",
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
        """Build the layered Sword badge coin."""

        coin_size = 390

        # Normalized visual centers of the manually traced badge polygons.
        # These keep the action button centered on whichever badge is next.
        badge_button_centers = [
            (0.631, 0.808),  # Grass
            (0.783, 0.279),  # Water
            (0.535, 0.534),  # Fire
            (0.268, 0.740),  # Fighting
            (0.834, 0.548),  # Fairy
            (0.541, 0.137),  # Rock
            (0.379, 0.367),  # Dark
            (0.177, 0.367),  # Dragon
        ]

        coin_layers: list[ft.Control] = [
            ft.Image(
                src=BADGE_FRAME_ASSET,
                width=coin_size,
                height=coin_size,
                fit=ft.BoxFit.CONTAIN,
                semantics_label="Galar badge coin frame",
            )
        ]

        for index, (badge_name, badge_asset) in enumerate(
            BADGE_LAYERS
        ):
            earned = index < self.earned_badges
            next_badge = (
                index == self.earned_badges
                and self.earned_badges < len(BADGE_LAYERS)
            )

            if earned:
                opacity = 1.0
            elif next_badge:
                opacity = 0.28
            else:
                opacity = 0.0

            coin_layers.append(
                ft.Image(
                    src=badge_asset,
                    width=coin_size,
                    height=coin_size,
                    fit=ft.BoxFit.CONTAIN,
                    opacity=opacity,
                    semantics_label=(
                        badge_name
                        if earned or next_badge
                        else "Hidden future badge"
                    ),
                )
            )

        if self.earned_badges < len(BADGE_LAYERS):
            center_x, center_y = badge_button_centers[
                self.earned_badges
            ]
            button_width = 112
            button_height = 55

            badge_button = ft.Container(
                content=ft.Button(
                    content=ft.Text(
                        "I've earned\nthis badge!",
                        size=8.5,
                        weight=ft.FontWeight.BOLD,
                        text_align=ft.TextAlign.CENTER,
                    ),
                    icon=ft.Icons.MILITARY_TECH_ROUNDED,
                    style=ft.ButtonStyle(
                        bgcolor={
                            ft.ControlState.DEFAULT: ft.Colors.with_opacity(
                                0.68,
                                SUCCESS,
                            ),
                            ft.ControlState.HOVERED: SUCCESS,
                            ft.ControlState.PRESSED: ft.Colors.with_opacity(
                                0.86,
                                SUCCESS,
                            ),
                        },
                        color={
                            ft.ControlState.DEFAULT: "#07120B",
                            ft.ControlState.HOVERED: "#07120B",
                            ft.ControlState.PRESSED: "#07120B",
                        },
                        icon_color={
                            ft.ControlState.DEFAULT: "#07120B",
                            ft.ControlState.HOVERED: "#07120B",
                            ft.ControlState.PRESSED: "#07120B",
                        },
                        mouse_cursor=ft.MouseCursor.CLICK,
                        animation_duration=160,
                    ),
                    on_click=lambda: self.page.run_task(
                        self._earn_next_badge
                    ),
                ),
                width=button_width,
                height=button_height,
            )
            badge_button.left = (
                center_x * coin_size - button_width / 2
            )
            badge_button.top = (
                center_y * coin_size - button_height / 2
            )
            coin_layers.append(badge_button)

        controls: list[ft.Control] = [
            ft.Container(
                content=ft.Stack(
                    controls=coin_layers,
                    width=coin_size,
                    height=coin_size,
                ),
                alignment=ft.Alignment.CENTER,
            )
        ]

        if self.earned_badges < len(BADGE_LAYERS):
            next_badge_name = BADGE_LAYERS[
                self.earned_badges
            ][0]
            controls.append(
                ft.Text(
                    f"Next: {next_badge_name}",
                    size=14,
                    weight=ft.FontWeight.W_600,
                    color=TEXT_SECONDARY,
                    text_align=ft.TextAlign.CENTER,
                )
            )
        else:
            controls.append(
                ft.Text(
                    "All 8 badges earned",
                    size=14,
                    weight=ft.FontWeight.BOLD,
                    color=SUCCESS,
                    text_align=ft.TextAlign.CENTER,
                )
            )

        controls.append(
            ft.Text(
                f"{self.earned_badges} of 8 badges earned",
                size=13,
                color=TEXT_SECONDARY,
                text_align=ft.TextAlign.CENTER,
            )
        )

        return self._build_card(
            title="Badge Tracker",
            icon=ft.Icons.MILITARY_TECH_OUTLINED,
            subtitle=(
                "Earn badges in order. Select the button on the "
                "ghosted badge when it has been earned."
            ),
            body=ft.Column(
                controls=controls,
                spacing=12,
                horizontal_alignment=ft.CrossAxisAlignment.CENTER,
            ),
            col={"xs": 12, "lg": 6},
        )

    def _build_journey_checklist_card(self) -> ft.Control:
        rows: list[ft.DataRow] = []
        for item in self._checklist_items():
            item_id = str(item.get("id", ""))
            status = self._item_status(item)
            manual_quantity = int(
                self.item_objectives.get(item_id, {}).get(
                    "manual_quantity_required",
                    0,
                )
            )
            derived_quantity = self.derived_item_requirements.get(
                item_id,
                0,
            )

            if manual_quantity > 0:
                remove_control: ft.Control = ft.IconButton(
                    icon=ft.Icons.DELETE_OUTLINE_ROUNDED,
                    icon_color=DANGER,
                    tooltip="Remove from Journey Checklist",
                    on_click=(
                        lambda event, objective_id=item_id:
                        self._request_remove_item_objective(
                            event,
                            objective_id,
                        )
                    ),
                )
            else:
                remove_control = ft.IconButton(
                    icon=ft.Icons.LINK_ROUNDED,
                    disabled=True,
                    tooltip=(
                        "Required by the Team Planner"
                        if derived_quantity > 0
                        else "Cannot remove"
                    ),
                )

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
                            self._build_item_obtained_action(
                                item,
                                status,
                            )
                        ),
                        ft.DataCell(remove_control),
                    ],
                )
            )

        table = ft.DataTable(
            columns=[
                self._column("Status"),
                self._column("Item"),
                self._column("Location"),
                self._column("Mark as obtained"),
                self._column("Remove"),
            ],
            rows=rows,
            border=ft.Border.all(1, BORDER_DEFAULT),
            border_radius=12,
            heading_row_color=SURFACE_RAISED,
            column_spacing=18,
            data_row_min_height=52,
            data_row_max_height=72,
        )

        body_controls: list[ft.Control] = [
            ft.Row(
                controls=[
                    ft.Button(
                        content="Add Objective",
                        icon=ft.Icons.ADD_ROUNDED,
                        bgcolor=SUCCESS,
                        color="#07120B",
                        icon_color="#07120B",
                        on_click=self._show_add_item_dialog,
                    )
                ],
                alignment=ft.MainAxisAlignment.END,
            ),
            ft.Row(
                controls=[table],
                scroll=ft.ScrollMode.AUTO,
            ),
        ]

        return self._build_card(
            title="Journey Checklist",
            icon=ft.Icons.CHECKLIST_ROUNDED,
            subtitle=(
                "Add items, TMs, and TRs to your Journey and track "
                "their completion."
            ),
            body=ft.Column(
                controls=body_controls,
                spacing=12,
            ),
            col={"xs": 12, "lg": 6},
        )

    def _show_add_item_dialog(
        self,
        event: ft.Event[ft.Button],
    ) -> None:
        del event

        options = [
            ft.DropdownOption(
                key=str(item.get("id", "")),
                text=str(item.get("name", "Unknown item")),
            )
            for item in self.items
            if item.get("id")
        ]
        if not options:
            return

        self._add_item_selector = ft.Dropdown(
            label="Item, TM, or TR",
            value=options[0].key,
            options=options,
            width=360,
        )
        self._add_item_quantity = ft.TextField(
            label="Quantity",
            value="1",
            keyboard_type=ft.KeyboardType.NUMBER,
            width=120,
        )

        dialog = ft.AlertDialog()
        dialog.modal = True
        dialog.title = ft.Text(
            "Add Journey Objective",
            weight=ft.FontWeight.BOLD,
        )
        dialog.content = ft.Column(
            controls=[
                ft.Text(
                    (
                        "Choose an objective from the current Sword "
                        "reference catalog. Adding an item already on the "
                        "checklist increases its required quantity."
                    ),
                    color=TEXT_SECONDARY,
                ),
                self._add_item_selector,
                self._add_item_quantity,
            ],
            spacing=14,
            tight=True,
        )
        dialog.actions = [
            ft.Button(
                content="Cancel",
                on_click=self._close_add_item_dialog,
            ),
            ft.Button(
                content="Add Objective",
                icon=ft.Icons.ADD_ROUNDED,
                bgcolor=SUCCESS,
                color="#07120B",
                icon_color="#07120B",
                on_click=self._confirm_add_item_objective,
            ),
        ]
        dialog.actions_alignment = ft.MainAxisAlignment.END
        self.page.show_dialog(dialog)

    def _close_add_item_dialog(
        self,
        event: ft.Event[ft.Button] | None = None,
    ) -> None:
        del event
        self._add_item_selector = None
        self._add_item_quantity = None
        self.page.pop_dialog()
        self.page.update()

    def _confirm_add_item_objective(
        self,
        event: ft.Event[ft.Button],
    ) -> None:
        del event

        item_id = ""
        if self._add_item_selector is not None:
            item_id = str(
                self._add_item_selector.value or ""
            ).strip()

        quantity_text = "1"
        if self._add_item_quantity is not None:
            quantity_text = str(
                self._add_item_quantity.value or "1"
            ).strip()

        try:
            quantity = int(quantity_text)
        except ValueError:
            quantity = 0

        if not item_id or quantity <= 0:
            self.page.show_dialog(
                ft.SnackBar(
                    content=ft.Text(
                        "Choose an objective and enter a quantity "
                        "greater than zero."
                    )
                )
            )
            return

        self._add_item_selector = None
        self._add_item_quantity = None
        self.page.pop_dialog()
        self.page.run_task(
            self._add_item_objective,
            item_id,
            quantity,
        )

    def _request_remove_item_objective(
        self,
        event: ft.Event[ft.IconButton],
        item_id: str,
    ) -> None:
        del event

        item = next(
            (
                entry
                for entry in self.items
                if str(entry.get("id", "")) == item_id
            ),
            None,
        )
        if item is None:
            return

        item_name = str(item.get("name", "this objective"))
        derived = self.derived_item_requirements.get(item_id, 0)

        dialog = ft.AlertDialog()
        dialog.modal = True
        dialog.title = ft.Text(
            f"Remove {item_name}?",
            weight=ft.FontWeight.BOLD,
        )
        dialog.content = ft.Text(
            (
                "This removes the manually added checklist objective."
                + (
                    f" The Team Planner still requires {derived}, so "
                    "that linked quantity will remain."
                    if derived > 0
                    else ""
                )
            ),
            color=TEXT_SECONDARY,
        )
        dialog.actions = [
            ft.Button(
                content="Cancel",
                on_click=lambda: self.page.pop_dialog(),
            ),
            ft.Button(
                content="Remove",
                icon=ft.Icons.DELETE_OUTLINE_ROUNDED,
                bgcolor=DANGER,
                color=TEXT_PRIMARY,
                icon_color=TEXT_PRIMARY,
                on_click=(
                    lambda event, objective_id=item_id:
                    self._confirm_remove_item_objective(
                        event,
                        objective_id,
                    )
                ),
            ),
        ]
        dialog.actions_alignment = ft.MainAxisAlignment.END
        self.page.show_dialog(dialog)

    def _confirm_remove_item_objective(
        self,
        event: ft.Event[ft.Button],
        item_id: str,
    ) -> None:
        del event
        self.page.pop_dialog()
        self.page.run_task(
            self._remove_manual_item_objective,
            item_id,
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

    def _item_display_name(self, item: dict[str, Any]) -> str:
        item_id = str(item.get("id", ""))
        quantity = self._required_item_quantity(item_id)
        name = str(item.get("name", "Unknown item"))
        return f"{name} ×{quantity}" if quantity > 1 else name

    def _item_status_tooltip(
        self,
        item: dict[str, Any],
        status: str,
    ) -> str:
        item_id = str(item.get("id", ""))
        required = self._required_item_quantity(item_id)
        obtained = self.item_quantities.get(item_id, 0)
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
        if status == "obtained":
            return ft.Text(
                "Acquired",
                color=PRIMARY_BLUE,
                size=12,
                weight=ft.FontWeight.W_600,
            )
        return ft.Button(
            content="I caught one!",
            icon=ft.Icons.CATCHING_POKEMON_ROUNDED,
            on_click=lambda: self._show_pokemon_acquired_prompt(pokemon),
        )

    def _build_item_progress_control(
        self,
        item: dict[str, Any],
        *,
        compact: bool = False,
    ) -> ft.Control:
        item_id = str(item.get("id", ""))
        required = self._required_item_quantity(item_id)
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