"""My Journey view with persistent badge and objective progression.

Badge, item, and planned-Pokémon changes save immediately. The graphical badge
tracker includes earned-badge celebrations. Map markers use unobstructed,
full-opacity sprites with larger Pokémon rendering and tap details.
"""

from __future__ import annotations

import asyncio
import json
import re
from copy import deepcopy
from pathlib import Path
from typing import Any, Awaitable, Callable

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

from ..viewmodels.app_state import AppState


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

TOP_JOURNEY_CARD_HEIGHT = 650

MAP_IMAGE_WIDTH = 1025
MAP_IMAGE_HEIGHT = 2490
MAP_RENDER_WIDTH = 520
MAP_RENDER_HEIGHT = MAP_RENDER_WIDTH * MAP_IMAGE_HEIGHT / MAP_IMAGE_WIDTH

# Initial calibration set. Coordinates are normalized against Galar_Map_Base.png.
# Additional locations can be added without changing marker rendering.
MAP_LOCATION_COORDINATES: dict[str, tuple[float, float]] = {
    "slumbering_weald": (0.282, 0.968),
    "postwick": (0.477, 0.969),
    "route_1": (0.477, 0.925),
    "wedgehurst": (0.477, 0.887),
    "route_2": (0.609, 0.873),
    "route_2_lake": (0.562, 0.846),
    "meetup_spot": (0.421, 0.801),
    "rolling_fields": (0.356, 0.779),
    "dappled_grove": (0.319, 0.794),
    "west_lake_axewell": (0.319, 0.745),
    "east_lake_axewell": (0.440, 0.716),
    "north_lake_miloch": (0.553, 0.706),
    "south_lake_miloch": (0.535, 0.733),
    "watchtower_ruins": (0.337, 0.716),
    "giants_seat": (0.572, 0.755),
    "axews_eye": (0.393, 0.745),
    "motostoke": (0.438, 0.642),
    "motostoke_outskirts": (0.542, 0.642),
    "route_3": (0.258, 0.625),
    "galar_mine": (0.151, 0.610),
    "route_4": (0.150, 0.588),
    "turffield": (0.205, 0.545),
    "route_5": (0.337, 0.559),
    "hulbury": (0.712, 0.559),
    "galar_mine_no_2": (0.675, 0.610),
    "motostoke_riverbank": (0.534, 0.657),
    "bridge_field": (0.525, 0.618),
    "stony_wilderness": (0.506, 0.559),
    "dusty_bowl": (0.468, 0.539),
    "giants_mirror": (0.515, 0.539),
    "giants_cap": (0.412, 0.539),
    "hammerlocke_hills": (0.506, 0.500),
    "lake_of_outrage": (0.375, 0.510),
    "hammerlocke": (0.455, 0.474),
    "route_6": (0.267, 0.468),
    "stow_on_side": (0.176, 0.440),
    "glimwood_tangle": (0.220, 0.370),
    "ballonlea": (0.180, 0.335),
    "route_7": (0.610, 0.475),
    "route_8": (0.650, 0.420),
    "circhester": (0.758, 0.372),
    "route_9": (0.820, 0.420),
    "route_9_circhester_bay": (0.790, 0.430),
    "route_9_tunnel": (0.690, 0.475),
    "spikemuth": (0.845, 0.475),
    "route_10": (0.480, 0.315),
    "wyndon": (0.448, 0.165),
}





MAP_LOCATION_LABELS: dict[str, str] = {
    "slumbering_weald": "Slumbering Weald",
    "postwick": "Postwick",
    "route_1": "Route 1",
    "wedgehurst": "Wedgehurst",
    "route_2": "Route 2",
    "route_2_lake": "Route 2 lakeside alcove",
    "meetup_spot": "Meetup Spot",
    "rolling_fields": "Rolling Fields",
    "dappled_grove": "Dappled Grove",
    "west_lake_axewell": "West Lake Axewell",
    "east_lake_axewell": "East Lake Axewell",
    "north_lake_miloch": "North Lake Miloch",
    "south_lake_miloch": "South Lake Miloch",
    "watchtower_ruins": "Watchtower Ruins",
    "giants_seat": "Giant's Seat",
    "axews_eye": "Axew's Eye",
    "motostoke": "Motostoke",
    "motostoke_outskirts": "Motostoke Outskirts",
    "route_3": "Route 3",
    "galar_mine": "Galar Mine",
    "route_4": "Route 4",
    "turffield": "Turffield",
    "route_5": "Route 5",
    "hulbury": "Hulbury",
    "galar_mine_no_2": "Galar Mine No. 2",
    "motostoke_riverbank": "Motostoke Riverbank",
    "bridge_field": "Bridge Field",
    "stony_wilderness": "Stony Wilderness",
    "dusty_bowl": "Dusty Bowl",
    "giants_mirror": "Giant's Mirror",
    "giants_cap": "Giant's Cap",
    "hammerlocke_hills": "Hammerlocke Hills",
    "lake_of_outrage": "Lake of Outrage",
    "hammerlocke": "Hammerlocke",
    "route_6": "Route 6",
    "stow_on_side": "Stow-on-Side",
    "glimwood_tangle": "Glimwood Tangle",
    "ballonlea": "Ballonlea",
    "route_7": "Route 7",
    "route_8": "Route 8",
    "circhester": "Circhester",
    "route_9": "Route 9",
    "route_9_circhester_bay": "Route 9 — Circhester Bay",
    "route_9_tunnel": "Route 9 Tunnel",
    "spikemuth": "Spikemuth",
    "route_10": "Route 10",
    "wyndon": "Wyndon",
}

ITEM_MARKER_ASSETS: dict[str, str] = {'absorb_bulb': 'raw/pokesprite/items/hold-item/absorb-bulb.png', 'air_balloon': 'raw/pokesprite/items/hold-item/air-balloon.png', 'amulet_coin': 'raw/pokesprite/items/hold-item/amulet-coin.png', 'assault_vest': 'raw/pokesprite/items/hold-item/assault-vest.png', 'berry_sweet': 'raw/pokesprite/items/evo-item/berry-sweet.png', 'big_root': 'raw/pokesprite/items/hold-item/big-root.png', 'binding_band': 'raw/pokesprite/items/hold-item/binding-band.png', 'black_belt': 'raw/pokesprite/items/hold-item/black-belt.png', 'black_glasses': 'raw/pokesprite/items/hold-item/black-glasses.png', 'black_sludge': 'raw/pokesprite/items/hold-item/black-sludge.png', 'blunder_policy': 'raw/pokesprite/items/hold-item/blunder-policy.png', 'bright_powder': 'raw/pokesprite/items/hold-item/bright-powder.png', 'cell_battery': 'raw/pokesprite/items/hold-item/cell-battery.png', 'charcoal': 'raw/pokesprite/items/hold-item/charcoal.png', 'chipped_pot': 'raw/pokesprite/items/evo-item/chipped-pot.png', 'choice_band': 'raw/pokesprite/items/hold-item/choice-band.png', 'choice_scarf': 'raw/pokesprite/items/hold-item/choice-scarf.png', 'choice_specs': 'raw/pokesprite/items/hold-item/choice-specs.png', 'cleanse_tag': 'raw/pokesprite/items/hold-item/cleanse-tag.png', 'clover_sweet': 'raw/pokesprite/items/evo-item/clover-sweet.png', 'cracked_pot': 'raw/pokesprite/items/evo-item/cracked-pot.png', 'damp_rock': 'raw/pokesprite/items/hold-item/damp-rock.png', 'dawn_stone': 'raw/pokesprite/items/evo-item/dawn-stone.png', 'destiny_knot': 'raw/pokesprite/items/hold-item/destiny-knot.png', 'dusk_stone': 'raw/pokesprite/items/evo-item/dusk-stone.png', 'eject_button': 'raw/pokesprite/items/hold-item/eject-button.png', 'eject_pack': 'raw/pokesprite/items/hold-item/eject-pack.png', 'electric_seed': 'raw/pokesprite/items/hold-item/electric-seed.png', 'everstone': 'raw/pokesprite/items/hold-item/everstone.png', 'eviolite': 'raw/pokesprite/items/hold-item/eviolite.png', 'expert_belt': 'raw/pokesprite/items/hold-item/expert-belt.png', 'fire_stone': 'raw/pokesprite/items/evo-item/fire-stone.png', 'flame_orb': 'raw/pokesprite/items/hold-item/flame-orb.png', 'float_stone': 'raw/pokesprite/items/hold-item/float-stone.png', 'flower_sweet': 'raw/pokesprite/items/evo-item/flower-sweet.png', 'focus_band': 'raw/pokesprite/items/hold-item/focus-band.png', 'focus_sash': 'raw/pokesprite/items/hold-item/focus-sash.png', 'full_incense': 'raw/pokesprite/items/incense/full.png', 'grip_claw': 'raw/pokesprite/items/hold-item/grip-claw.png', 'hard_stone': 'raw/pokesprite/items/hold-item/hard-stone.png', 'heat_rock': 'raw/pokesprite/items/hold-item/heat-rock.png', 'heavy_duty_boots': 'raw/pokesprite/items/hold-item/heavy-duty-boots.png', 'ice_stone': 'raw/pokesprite/items/evo-item/ice-stone.png', 'icy_rock': 'raw/pokesprite/items/hold-item/icy-rock.png', 'iron_ball': 'raw/pokesprite/items/hold-item/iron-ball.png', 'kings_rock': 'raw/pokesprite/items/hold-item/kings-rock.png', 'lagging_tail': 'raw/pokesprite/items/hold-item/lagging-tail.png', 'lax_incense': 'raw/pokesprite/items/incense/lax.png', 'leaf_stone': 'raw/pokesprite/items/evo-item/leaf-stone.png', 'leftovers': 'raw/pokesprite/items/hold-item/leftovers.png', 'life_orb': 'raw/pokesprite/items/hold-item/life-orb.png', 'light_ball': 'raw/pokesprite/items/hold-item/light-ball.png', 'light_clay': 'raw/pokesprite/items/hold-item/light-clay.png', 'love_sweet': 'raw/pokesprite/items/evo-item/love-sweet.png', 'luck_incense': 'raw/pokesprite/items/incense/luck.png', 'lucky_egg': 'raw/pokesprite/items/hold-item/lucky-egg.png', 'luminous_moss': 'raw/pokesprite/items/hold-item/luminous-moss.png', 'macho_brace': 'raw/pokesprite/items/ev-item/macho-brace.png', 'magnet': 'raw/pokesprite/items/hold-item/magnet.png', 'mental_herb': 'raw/pokesprite/items/hold-item/mental-herb.png', 'metal_coat': 'raw/pokesprite/items/hold-item/metal-coat.png', 'metronome': 'raw/pokesprite/items/hold-item/metronome.png', 'miracle_seed': 'raw/pokesprite/items/hold-item/miracle-seed.png', 'moon_stone': 'raw/pokesprite/items/evo-item/moon-stone.png', 'muscle_band': 'raw/pokesprite/items/hold-item/muscle-band.png', 'mystic_water': 'raw/pokesprite/items/hold-item/mystic-water.png', 'never_melt_ice': 'raw/pokesprite/items/hold-item/never-melt-ice.png', 'normal_gem': 'raw/pokesprite/items/gem/normal.png', 'odd_incense': 'raw/pokesprite/items/incense/odd.png', 'pixie_plate': 'raw/pokesprite/items/plate/pixie.png', 'poison_barb': 'raw/pokesprite/items/hold-item/poison-barb.png', 'power_anklet': 'raw/pokesprite/items/ev-item/power-anklet.png', 'power_band': 'raw/pokesprite/items/ev-item/power-band.png', 'power_belt': 'raw/pokesprite/items/ev-item/power-belt.png', 'power_bracer': 'raw/pokesprite/items/ev-item/power-bracer.png', 'power_lens': 'raw/pokesprite/items/ev-item/power-lens.png', 'power_weight': 'raw/pokesprite/items/ev-item/power-weight.png', 'prism_scale': 'raw/pokesprite/items/evo-item/prism-scale.png', 'protective_pads': 'raw/pokesprite/items/hold-item/protective-pads.png', 'protector': 'raw/pokesprite/items/evo-item/protector.png', 'pure_incense': 'raw/pokesprite/items/incense/pure.png', 'quick_claw': 'raw/pokesprite/items/hold-item/quick-claw.png', 'quick_powder': 'raw/pokesprite/items/hold-item/quick-powder.png', 'razor_claw': 'raw/pokesprite/items/evo-item/razor-claw.png', 'reaper_cloth': 'raw/pokesprite/items/evo-item/reaper-cloth.png', 'red_card': 'raw/pokesprite/items/hold-item/red-card.png', 'ring_target': 'raw/pokesprite/items/hold-item/ring-target.png', 'rock_incense': 'raw/pokesprite/items/incense/rock.png', 'rocky_helmet': 'raw/pokesprite/items/hold-item/rocky-helmet.png', 'room_service': 'raw/pokesprite/items/hold-item/room-service.png', 'rose_incense': 'raw/pokesprite/items/incense/rose.png', 'rusted_sword': 'raw/pokesprite/items/hold-item/rusted-sword.png', 'sachet': 'raw/pokesprite/items/evo-item/sachet.png', 'safety_goggles': 'raw/pokesprite/items/hold-item/safety-goggles.png', 'scope_lens': 'raw/pokesprite/items/hold-item/scope-lens.png', 'sea_incense': 'raw/pokesprite/items/incense/sea.png', 'sharp_beak': 'raw/pokesprite/items/hold-item/sharp-beak.png', 'shed_shell': 'raw/pokesprite/items/hold-item/shed-shell.png', 'shell_bell': 'raw/pokesprite/items/hold-item/shell-bell.png', 'shiny_stone': 'raw/pokesprite/items/evo-item/shiny-stone.png', 'silk_scarf': 'raw/pokesprite/items/hold-item/silk-scarf.png', 'silver_powder': 'raw/pokesprite/items/hold-item/silver-powder.png', 'smoke_ball': 'raw/pokesprite/items/hold-item/smoke-ball.png', 'smooth_rock': 'raw/pokesprite/items/hold-item/smooth-rock.png', 'soft_sand': 'raw/pokesprite/items/hold-item/soft-sand.png', 'soothe_bell': 'raw/pokesprite/items/other-item/soothe-bell.png', 'spell_tag': 'raw/pokesprite/items/hold-item/spell-tag.png', 'sticky_barb': 'raw/pokesprite/items/hold-item/sticky-barb.png', 'strawberry_sweet': 'raw/pokesprite/items/evo-item/strawberry-sweet.png', 'sun_stone': 'raw/pokesprite/items/evo-item/sun-stone.png', 'tart_apple': 'raw/pokesprite/items/evo-item/tart-apple.png', 'terrain_extender': 'raw/pokesprite/items/hold-item/terrain-extender.png', 'throat_spray': 'raw/pokesprite/items/hold-item/throat-spray.png', 'thunder_stone': 'raw/pokesprite/items/evo-item/thunder-stone.png', 'toxic_orb': 'raw/pokesprite/items/hold-item/toxic-orb.png', 'twisted_spoon': 'raw/pokesprite/items/hold-item/twisted-spoon.png', 'utility_umbrella': 'raw/pokesprite/items/hold-item/utility-umbrella.png', 'water_stone': 'raw/pokesprite/items/evo-item/water-stone.png', 'wave_incense': 'raw/pokesprite/items/incense/wave.png', 'weakness_policy': 'raw/pokesprite/items/hold-item/weakness-policy.png', 'whipped_dream': 'raw/pokesprite/items/evo-item/whipped-dream.png', 'white_herb': 'raw/pokesprite/items/hold-item/white-herb.png', 'wide_lens': 'raw/pokesprite/items/hold-item/wide-lens.png', 'wise_glasses': 'raw/pokesprite/items/hold-item/wise-glasses.png', 'zoom_lens': 'raw/pokesprite/items/hold-item/zoom-lens.png'}

class MyJourneyView:
    """Render My Journey fixture data with saved badge progression."""

    def __init__(
        self,
        page: ft.Page,
        *,
        app_state: AppState,
        on_go_to_my_team: Callable[[str], None] | None = None,
        on_scroll_to: (
            Callable[..., Awaitable[None]] | None
        ) = None,
    ) -> None:
        self.page = page
        self.app_state = app_state
        self.on_go_to_my_team = on_go_to_my_team
        self.on_scroll_to = on_scroll_to
        self.items = self._load_json(DATA_DIR / "journey_items.json")
        self.pokemon_catalog = self._load_json(
            DATA_DIR / "journey_pokemon.json"
        )
        self.planned_pokemon_ids = self._load_planned_pokemon_ids()
        self.pokemon = self._planned_pokemon_records()
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
            for pokemon in self.pokemon_catalog
        }
        self._root: ft.Column | None = None
        self._caught_stage_selector: ft.Dropdown | None = None
        self._add_item_selector: ft.AutoComplete | None = None
        self._add_item_quantity: ft.TextField | None = None
        self._add_item_button: ft.Button | None = None
        self._add_item_validation_text: ft.Text | None = None
        self._add_item_name_to_id: dict[str, str] = {}
        self._move_type_by_name = self._load_move_type_lookup()
        self._add_pokemon_selector: ft.AutoComplete | None = None
        self._add_pokemon_button: ft.Button | None = None
        self._add_pokemon_validation_text: ft.Text | None = None
        self._add_pokemon_name_to_id: dict[str, str] = {}

        self._badge_celebration_badge: ft.Container | None = None
        self._badge_celebration_shine: ft.Container | None = None
        self._badge_celebration_sparkles: list[ft.Container] = []

        self._move_to_map_enabled = True
        self._selected_map_objective_id: str | None = None
        self._map_stack: ft.Stack | None = None
        self._map_host: ft.Container | None = None
        self._map_image: ft.Image | None = None
        self._map_render_width = float(MAP_RENDER_WIDTH)
        self._map_render_height = float(MAP_RENDER_HEIGHT)
        self._map_marker_records: list[dict[str, Any]] = []
        self._map_marker_filter = "all"
        self._objective_row_containers: dict[str, list[ft.Container]] = {}
        self._objective_data_rows: dict[str, list[ft.DataRow]] = {}
        self._move_to_map_overlay: ft.Container | None = None
        self._map_markers_by_objective: dict[str, list[ft.Container]] = {}
        self._map_marker_generation = 0
        self._map_marker_pulse_token = 0
        self._selected_marker_pulse_scale = 1.16
        self._selected_marker_y: float | None = None
        self._selected_marker_record: dict[str, Any] | None = None

    @staticmethod
    def _load_json(path: Path) -> list[dict[str, Any]]:
        with path.open("r", encoding="utf-8") as file:
            data = json.load(file)
        if not isinstance(data, list):
            raise ValueError(f"Expected a list in {path.name}.")
        return data

    def _load_move_type_lookup(self) -> dict[str, str]:
        """Load move types so TM/TR marker sprites do not depend on duplicate JSON fields."""

        path = DATA_DIR / "moves.json"
        try:
            raw = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, UnicodeError, json.JSONDecodeError):
            return {}

        records: list[dict[str, Any]] = []
        if isinstance(raw, list):
            records = [row for row in raw if isinstance(row, dict)]
        elif isinstance(raw, dict):
            for key, value in raw.items():
                if isinstance(value, dict):
                    row = dict(value)
                    row.setdefault("name", key)
                    records.append(row)

        lookup: dict[str, str] = {}
        for row in records:
            name = str(
                row.get("name")
                or row.get("Name")
                or row.get("move")
                or row.get("Move")
                or ""
            ).strip()
            move_type = str(
                row.get("type")
                or row.get("Type")
                or row.get("move_type")
                or row.get("Move Type")
                or ""
            ).strip().lower()
            if name and move_type:
                lookup[name.casefold()] = move_type
        return lookup

    def _load_planned_pokemon_ids(self) -> list[str]:
        """Load the saved planner roster; a new Journey starts empty."""

        journey_state = self.app_state.my_journey_data
        catalog_ids = [
            str(pokemon.get("id", "")).strip()
            for pokemon in self.pokemon_catalog
            if str(pokemon.get("id", "")).strip()
        ]
        catalog_id_set = set(catalog_ids)

        if journey_state.get("planner_initialized") is not True:
            return []

        raw_ids = journey_state.get("planned_pokemon_ids", [])
        if not isinstance(raw_ids, list):
            return []

        planned_ids: list[str] = []
        for raw_id in raw_ids:
            pokemon_id = str(raw_id).strip()
            if (
                pokemon_id
                and pokemon_id in catalog_id_set
                and pokemon_id not in planned_ids
            ):
                planned_ids.append(pokemon_id)
        return planned_ids

    def _planned_pokemon_records(self) -> list[dict[str, Any]]:
        """Return catalog records in the player's saved planner order."""

        records_by_id = {
            str(pokemon.get("id", "")).strip(): pokemon
            for pokemon in self.pokemon_catalog
            if str(pokemon.get("id", "")).strip()
        }
        return [
            records_by_id[pokemon_id]
            for pokemon_id in self.planned_pokemon_ids
            if pokemon_id in records_by_id
        ]

    def _reload_planner_dependencies(self) -> None:
        """Rebuild planner records, ownership state, and linked requirements."""

        self.pokemon = self._planned_pokemon_records()

        # Ownership may have changed while the user was on My Team. Always
        # resolve acquired state from current AppState when the planner roster
        # changes instead of reusing the view's older cached values.
        self.pokemon_obtained = {
            str(pokemon.get("id", "")):
            self.app_state.is_pokemon_obtained(
                str(pokemon.get("id", ""))
            )
            for pokemon in self.pokemon_catalog
        }

        self.derived_item_requirements = (
            self._build_derived_item_requirements()
        )
        self.item_objectives = self._load_item_objectives()
        self.item_quantities = {
            item_id: int(record.get("quantity_obtained", 0))
            for item_id, record in self.item_objectives.items()
        }

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
        """Load persisted checklist rows; a new Journey starts empty."""

        journey_state = self.app_state.my_journey_data
        stored_records = journey_state.get("item_objectives", [])

        stored_by_id: dict[str, dict[str, Any]] = {
            str(record.get("id")): record
            for record in stored_records
            if isinstance(record, dict) and record.get("id")
        }

        objectives: dict[str, dict[str, int]] = {}

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
        self._ensure_move_to_map_overlay()

        self._root = ft.Column(
            controls=self._build_page_controls(),
            spacing=24,
            width=CONTENT_MAX_WIDTH,
            horizontal_alignment=ft.CrossAxisAlignment.CENTER,
        )
        return self._root

    def _build_page_controls(self) -> list[ft.Control]:
        self._objective_row_containers = {}
        self._objective_data_rows = {}

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
        self.planned_pokemon_ids = self._load_planned_pokemon_ids()
        self._reload_planner_dependencies()
        self.pokemon_obtained = {
            str(pokemon.get("id")): self.app_state.is_pokemon_obtained(
                str(pokemon.get("id"))
            )
            for pokemon in self.pokemon_catalog
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

    def _request_item_completion(
        self,
        item: dict[str, Any],
        quantity: int,
    ) -> None:
        """Confirm completion before removing an item's map marker."""

        item_id = str(item.get("id", "")).strip()
        if not item_id:
            return

        required = self._required_item_quantity(item_id)
        current = min(
            self.item_quantities.get(item_id, 0),
            required,
        )

        # Only completion needs confirmation. Decrementing or clearing an
        # obtained item restores its marker and remains immediate.
        if quantity < required or current >= required:
            self.page.run_task(
                self._set_item_quantity,
                item_id,
                quantity,
            )
            return

        objective_name = self._item_display_name(item)

        dialog = ft.AlertDialog()
        dialog.modal = True
        dialog.title = ft.Text(
            f"You got the {objective_name}!",
            weight=ft.FontWeight.BOLD,
        )
        dialog.content = ft.Text(
            (
                "Its marker will be removed from the map, but the objective "
                "will remain in your Journey Checklist."
            ),
            color=TEXT_SECONDARY,
        )
        dialog.actions = [
            ft.Button(
                content="Not Yet",
                on_click=lambda: self.page.pop_dialog(),
            ),
            ft.Button(
                content="Mark as Obtained",
                icon=ft.Icons.CHECK_ROUNDED,
                bgcolor=PRIMARY_BLUE,
                color=TEXT_PRIMARY,
                icon_color=TEXT_PRIMARY,
                on_click=lambda: self._confirm_item_completion(
                    item_id,
                    quantity,
                ),
            ),
        ]
        dialog.actions_alignment = ft.MainAxisAlignment.END
        self.page.show_dialog(dialog)

    def _confirm_item_completion(
        self,
        item_id: str,
        quantity: int,
    ) -> None:
        """Close the confirmation and persist completed item progress."""

        self.page.pop_dialog()
        self.page.run_task(
            self._set_item_quantity,
            item_id,
            quantity,
        )

    def _item_checkbox_handler(
        self,
        checkbox: ft.Checkbox,
        item_id: str,
        required: int,
    ) -> None:
        """Persist a single-quantity item's checked or unchecked state."""

        quantity = required if checkbox.value is True else 0
        item = next(
            (
                candidate
                for candidate in self.items
                if str(candidate.get("id", "")) == item_id
            ),
            None,
        )
        if item is None:
            return

        self._request_item_completion(
            item,
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
                        "My Box will mark this Journey objective as acquired. "
                        "Its marker will then be removed from the map, but the "
                        "objective will remain in your Team Planner."
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

    @staticmethod
    def _pokemon_acquisitions(
        pokemon: dict[str, Any],
    ) -> list[dict[str, Any]]:
        """Return primary and alternate acquisition sources."""

        acquisitions: list[dict[str, Any]] = []

        primary = pokemon.get("primary_acquisition")
        if isinstance(primary, dict):
            acquisitions.append(primary)

        alternates = pokemon.get("alternate_acquisitions", [])
        if isinstance(alternates, list):
            acquisitions.extend(
                acquisition
                for acquisition in alternates
                if isinstance(acquisition, dict)
            )

        return acquisitions

    @staticmethod
    def _pokemon_acquisition_required_badge(
        pokemon: dict[str, Any],
        acquisition: dict[str, Any],
    ) -> int:
        """Resolve one acquisition source's badge requirement."""

        source_badge = acquisition.get("required_badge")
        if (
            isinstance(source_badge, int)
            and not isinstance(source_badge, bool)
        ):
            return source_badge

        return int(pokemon.get("required_badge", 0))

    def _pokemon_status(self, pokemon: dict[str, Any]) -> str:
        pokemon_id = str(pokemon.get("id", ""))
        if self.pokemon_obtained.get(pokemon_id, False):
            return "obtained"

        acquisitions = self._pokemon_acquisitions(pokemon)
        required_badges = [
            self._pokemon_acquisition_required_badge(
                pokemon,
                acquisition,
            )
            for acquisition in acquisitions
        ]
        required_badge = (
            min(required_badges)
            if required_badges
            else int(pokemon.get("required_badge", 0))
        )

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

    def _current_objective_ids(self) -> list[str]:
        """Return the prioritized objective IDs shown in Current Objectives."""

        objective_ids: list[str] = []

        # 1. Currently catchable Pokémon.
        for pokemon in self.pokemon:
            if self._pokemon_status(pokemon) != "available":
                continue

            objective_ids.append(
                f"pokemon:{pokemon.get('id', '')}"
            )

        available_items = [
            item
            for item in self._checklist_items()
            if self._item_status(item) == "available"
        ]

        prioritized_item_groups = [
            [
                item
                for item in available_items
                if str(item.get("category", "")) == "evolution_item"
            ],
            [
                item
                for item in available_items
                if str(item.get("category", "")) == "held_item"
            ],
            [
                item
                for item in available_items
                if str(item.get("category", ""))
                not in {"evolution_item", "held_item"}
            ],
        ]

        for item_group in prioritized_item_groups:
            for item in item_group:
                objective_ids.append(
                    f"item:{item.get('id', '')}"
                )

        return objective_ids[:6]

    def _build_current_objectives_card(self) -> ft.Control:
        """Build the six highest-priority objectives available right now."""

        objectives: list[ft.Control] = []
        current_objective_ids = set(self._current_objective_ids())

        # 1. Currently catchable Pokémon.
        for pokemon in self.pokemon:
            objective_id = f"pokemon:{pokemon.get('id', '')}"
            if objective_id not in current_objective_ids:
                continue

            objectives.append(
                self._build_objective_row(
                    objective_id=objective_id,
                    status="available",
                    title=str(pokemon.get("pokemon", "Unknown Pokémon")),
                    detail=self._pokemon_acquisition_text(pokemon),
                    sprite_asset=(
                        str(pokemon.get("marker_asset") or "").strip()
                        or None
                    ),
                    action=self._build_pokemon_obtained_action(
                        pokemon,
                        "available",
                    ),
                )
            )

        available_items = [
            item
            for item in self._checklist_items()
            if self._item_status(item) == "available"
        ]

        # 2. Evolution items required by planned Pokémon.
        prioritized_item_groups = [
            [
                item
                for item in available_items
                if str(item.get("category", "")) == "evolution_item"
            ],
            # 3. Currently attainable held items.
            [
                item
                for item in available_items
                if str(item.get("category", "")) == "held_item"
            ],
            # 4. Any other currently attainable checklist items.
            [
                item
                for item in available_items
                if str(item.get("category", ""))
                not in {"evolution_item", "held_item"}
            ],
        ]

        for item_group in prioritized_item_groups:
            for item in item_group:
                objective_id = f"item:{item.get('id', '')}"
                if objective_id not in current_objective_ids:
                    continue

                objectives.append(
                    self._build_objective_row(
                        objective_id=objective_id,
                        status="available",
                        title=self._item_display_name(item),
                        detail=self._current_item_source_text(item),
                        sprite_asset=self._marker_asset_for_record(
                            {
                                "marker_asset": item.get("marker_asset"),
                                "item_id": item.get("id"),
                                "category": item.get("category"),
                                "move_type": item.get("move_type"),
                                "title": self._item_display_name(item),
                            }
                        ),
                        action=self._build_item_progress_control(
                            item,
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
            subtitle="Highest-priority goals available at your current Badge count.",
            body=ft.Column(
                controls=objectives,
                spacing=10,
            ),
            col={"xs": 12, "lg": 6},
            height=TOP_JOURNEY_CARD_HEIGHT,
        )

    def _ensure_move_to_map_overlay(self) -> None:
        """Add the persistent Move to Map control to the page overlay."""

        if self._move_to_map_overlay is not None:
            return

        move_to_map_toggle = ft.Switch(
            label="Move to Map",
            value=self._move_to_map_enabled,
            active_color=PRIMARY_BLUE,
            tooltip=(
                "When enabled, selecting an item or Pokémon moves the "
                "page to its map location."
            ),
        )
        move_to_map_toggle.on_change = lambda: (
            self._set_move_to_map_enabled(move_to_map_toggle)
        )

        overlay = ft.Container(
            key="my-journey-move-to-map-overlay",
            content=move_to_map_toggle,
            padding=ft.Padding.symmetric(horizontal=14, vertical=8),
            bgcolor=ft.Colors.with_opacity(0.94, SURFACE_RAISED),
            border=ft.Border.all(1, BORDER_DEFAULT),
            border_radius=24,
            shadow=ft.BoxShadow(
                blur_radius=18,
                spread_radius=1,
                color=ft.Colors.with_opacity(0.35, ft.Colors.BLACK),
                offset=ft.Offset(0, 6),
            ),
        )
        overlay.right = 24
        overlay.bottom = 24

        self._move_to_map_overlay = overlay
        self.page.overlay.append(overlay)

    def _set_move_to_map_enabled(
        self,
        toggle: ft.Switch,
    ) -> None:
        """Remember whether objective selection should move to the map."""

        self._move_to_map_enabled = toggle.value is True

    def _select_objective_for_map(
        self,
        objective_id: str,
    ) -> None:
        """Select an item or Pokémon and rebuild the live marker controls."""

        if not objective_id:
            return

        previous_objective_id = self._selected_map_objective_id
        self._selected_map_objective_id = objective_id
        self._map_marker_pulse_token += 1
        self._selected_marker_pulse_scale = 1.16
        previous_id = previous_objective_id or ""

        # Marker controls may be replaced by a filter change, a page refresh, or
        # a responsive map-size event. Rebuild from selection state instead of
        # mutating references that may already have been frozen by Flet.
        self._refresh_visible_map_markers()

        for row_container in self._objective_row_containers.get(
            previous_id,
            [],
        ):
            row_container.bgcolor = self._selected_row_color(False)
            row_container.border = self._selected_row_border(False)

        for row_container in self._objective_row_containers.get(
            objective_id,
            [],
        ):
            row_container.bgcolor = self._selected_row_color(True)
            row_container.border = self._selected_row_border(True)

        for data_row in self._objective_data_rows.get(previous_id, []):
            data_row.color = None

        for data_row in self._objective_data_rows.get(objective_id, []):
            data_row.color = ft.Colors.with_opacity(0.16, PRIMARY_BLUE)

        self.page.update()
        self.page.run_task(self._focus_selected_map_objective)

    async def _focus_selected_map_objective(self) -> None:
        """Scroll to the selected marker, then animate the live controls."""

        if self._move_to_map_enabled:
            await self._scroll_to_selected_marker()
            await asyncio.sleep(0.10)

        await self._pulse_selected_markers()

    async def _pulse_selected_markers(self) -> None:
        """Bounce selected markers by rebuilding from transient scale state.

        Marker controls are never mutated after mounting. Each animation frame
        changes a view-state value and rebuilds the live marker layer, so map
        filtering and responsive size changes cannot leave this task holding
        frozen controls. A token cancels an older pulse when another objective
        is selected.
        """

        objective_id = self._selected_map_objective_id
        if not objective_id:
            return

        pulse_token = self._map_marker_pulse_token
        frames = [
            (0.82, 0.18),
            (1.38, 0.40),
            (1.05, 0.18),
            (1.24, 0.28),
            (1.16, 0.0),
        ]

        for scale, delay in frames:
            if (
                pulse_token != self._map_marker_pulse_token
                or objective_id != self._selected_map_objective_id
            ):
                return

            self._selected_marker_pulse_scale = scale
            self._refresh_visible_map_markers()

            if delay > 0:
                await asyncio.sleep(delay)

    async def _scroll_to_selected_marker(self) -> None:
        """Center the selected marker vertically as closely as possible."""

        marker_y = self._selected_marker_y
        if marker_y is None:
            return

        page_width = float(self.page.width or 0)
        viewport_height = float(self.page.height or 760)

        if page_width >= 1000:
            # Includes the page intro, top row, second-row spacing, and
            # the map card's heading/padding.
            map_top = 1320.0
        else:
            checklist_rows = len(self._checklist_items())

            # Narrow DataTable rows wrap into much taller records than they do
            # on desktop. Estimate from the actual phone layout rather than the
            # compact desktop row height.
            checklist_height = 250.0 + checklist_rows * 145.0

            page_intro_height = 90.0
            section_spacing = 24.0
            top_row_height = TOP_JOURNEY_CARD_HEIGHT * 2 + 20.0

            # Includes the map card title, subtitle, divider, marker filter,
            # spacing, and padding above the image itself.
            map_card_header_height = 300.0

            map_top = (
                page_intro_height
                + section_spacing
                + top_row_height
                + section_spacing
                + checklist_height
                + section_spacing
                + map_card_header_height
            )

        target_offset = max(
            0.0,
            map_top
            + marker_y * self._map_render_height
            - viewport_height * 0.50,
        )

        scroll_to = self.on_scroll_to or self.page.scroll_to
        await scroll_to(
            offset=target_offset,
            duration=520,
            curve=ft.AnimationCurve.EASE_OUT_CUBIC,
        )

    @staticmethod
    def _map_location_ids(
        acquisition: dict[str, Any],
    ) -> list[str]:
        """Return canonical map-location IDs from Journey data."""

        raw_locations = acquisition.get("map_locations", [])
        if not isinstance(raw_locations, list):
            return []

        return [
            str(location_id).strip()
            for location_id in raw_locations
            if str(location_id).strip()
        ]

    @staticmethod
    def _source_marker_status(
        objective_status: str,
        required_badge: int,
        earned_badges: int,
    ) -> str:
        """Resolve marker state for one specific acquisition source."""

        if objective_status == "obtained":
            return "obtained"
        if required_badge <= earned_badges:
            return "available"
        return "unavailable"

    def _marker_asset_for_record(
        self,
        record: dict[str, Any],
    ) -> str | None:
        """Resolve a sprite from the catalog ID, or derive TM/TR type at runtime."""

        explicit_asset = str(record.get("marker_asset") or "").strip()
        if explicit_asset:
            return explicit_asset

        item_id = str(record.get("item_id") or "").strip()
        if item_id in ITEM_MARKER_ASSETS:
            return ITEM_MARKER_ASSETS[item_id]

        category = str(record.get("category", "")).strip().lower()
        if category not in {"tm", "tr"}:
            return None

        move_type = str(record.get("move_type") or "").strip().lower()
        if not move_type:
            title = str(record.get("title") or "").strip()
            move_name = re.sub(r"^(?:TM|TR)\d{2}\s+", "", title).strip()
            move_type = self._move_type_by_name.get(move_name.casefold(), "")

        if move_type:
            return f"raw/pokesprite/items/{category}/{move_type}.png"
        return None

    @staticmethod
    def _record_objective_ids(
        record: dict[str, Any],
    ) -> list[str]:
        """Return every objective represented by one map marker."""

        raw_ids = record.get("objective_ids")
        if isinstance(raw_ids, list):
            objective_ids = [
                str(objective_id).strip()
                for objective_id in raw_ids
                if str(objective_id).strip()
            ]
            if objective_ids:
                return objective_ids

        objective_id = str(record.get("objective_id", "")).strip()
        return [objective_id] if objective_id else []

    def _record_matches_selected_objective(
        self,
        record: dict[str, Any],
    ) -> bool:
        """Return whether a marker represents the selected objective."""

        selected_id = self._selected_map_objective_id
        return bool(
            selected_id
            and selected_id in self._record_objective_ids(record)
        )

    @staticmethod
    def _watt_price_from_source(source: dict[str, Any]) -> str:
        """Extract a display-ready Watt price from a trader source."""

        detail = str(source.get("location_detail", ""))
        match = re.search(
            r"(?:costs?|for)\s+([\d,]+)\s*W\b",
            detail,
            flags=re.IGNORECASE,
        )
        return f"{match.group(1)} W" if match else "Price varies"

    def _show_map_marker_details(
        self,
        record: dict[str, Any],
    ) -> None:
        """Show marker details in a tap-friendly dialog."""

        self._selected_marker_record = record

        dialog = ft.AlertDialog()
        dialog.modal = False
        dialog.title = ft.Text(
            str(record.get("title", "Journey objective")),
            weight=ft.FontWeight.BOLD,
            color=TEXT_PRIMARY,
        )
        dialog_controls: list[ft.Control] = [
            ft.Text(
                str(record.get("location", "Location unavailable")),
                size=15,
                weight=ft.FontWeight.W_600,
                color=TEXT_SECONDARY,
            ),
            ft.Text(
                str(record.get("detail", "")),
                size=13,
                color=TEXT_MUTED,
            ),
        ]

        watts_trader_items = record.get("watts_trader_items")
        if isinstance(watts_trader_items, list) and watts_trader_items:
            dialog_controls.append(ft.Divider(height=10))
            dialog_controls.append(
                ft.Text(
                    "Journey Checklist TRs",
                    size=13,
                    weight=ft.FontWeight.W_600,
                    color=TEXT_SECONDARY,
                )
            )
            for trader_item in watts_trader_items:
                if not isinstance(trader_item, dict):
                    continue
                dialog_controls.append(
                    ft.Text(
                        (
                            f"{str(trader_item.get('title', 'TR'))}"
                            f" — {str(trader_item.get('price', 'Price varies'))}"
                        ),
                        size=13,
                        color=TEXT_PRIMARY,
                    )
                )
        else:
            status = str(record.get("status", "")).strip().lower()
            required_badge = record.get("required_badge", 0)

            if (
                status == "unavailable"
                and isinstance(required_badge, int)
                and not isinstance(required_badge, bool)
                and required_badge > self.earned_badges
            ):
                badge_word = (
                    "Gym Badge"
                    if required_badge == 1
                    else "Gym Badges"
                )
                status_text = (
                    f"Status: Unavailable — "
                    f"{required_badge} {badge_word} required"
                )
            else:
                status_text = f"Status: {status.title()}"

            dialog_controls.append(
                ft.Text(
                    status_text,
                    size=13,
                    color=TEXT_SECONDARY,
                )
            )

        if record.get("map_display_mode") == "representative":
            dialog_controls.append(
                ft.Text(
                    "Representative location; additional sources are available.",
                    size=12,
                    color=TEXT_MUTED,
                    italic=True,
                )
            )

        dialog.content = ft.Column(
            controls=dialog_controls,
            spacing=8,
            tight=True,
        )
        dialog.actions = [
            ft.Button(
                content="Close",
                on_click=lambda: self.page.pop_dialog(),
            )
        ]
        dialog.actions_alignment = ft.MainAxisAlignment.END
        self.page.show_dialog(dialog)

    def _marker_records(self) -> list[dict[str, Any]]:
        """Build markers directly from canonical map_locations IDs."""

        records: list[dict[str, Any]] = []
        watts_trader_items: list[dict[str, str]] = []

        for item in self._checklist_items():
            item_id = str(item.get("id", "")).strip()
            if not item_id:
                continue

            objective_id = f"item:{item_id}"
            objective_status = self._item_status(item)
            if objective_status == "obtained":
                continue

            title = self._item_display_name(item)
            category = str(item.get("category", "item"))
            seen_locations: set[str] = set()

            for source in item.get("sources", []):
                if not isinstance(source, dict):
                    continue

                required_badge = int(source.get("required_badge", 0))
                marker_status = self._source_marker_status(
                    objective_status,
                    required_badge,
                    self.earned_badges,
                )
                source_method = str(source.get("method", ""))

                if (
                    category.lower() == "tr"
                    and source_method == "watt_trader"
                ):
                    watts_trader_items.append({
                        "objective_id": objective_id,
                        "title": title,
                        "price": self._watt_price_from_source(source),
                        "status": marker_status,
                    })
                    continue

                map_location_ids = self._map_location_ids(source)

                raw_display_locations = source.get(
                    "map_display_locations",
                    [],
                )
                if isinstance(raw_display_locations, list):
                    display_locations = [
                        str(location_id).strip()
                        for location_id in raw_display_locations
                        if str(location_id).strip()
                    ]
                    if display_locations:
                        map_location_ids = display_locations

                map_display_mode = str(
                    source.get("map_display_mode") or "all"
                ).strip()

                for location_id in map_location_ids:
                    if location_id in seen_locations:
                        continue

                    coordinates = MAP_LOCATION_COORDINATES.get(location_id)
                    if coordinates is None:
                        continue

                    seen_locations.add(location_id)
                    x, y = coordinates
                    records.append({
                        "objective_id": objective_id,
                        "title": title,
                        "location_id": location_id,
                        "location": MAP_LOCATION_LABELS.get(
                            location_id,
                            location_id.replace("_", " ").title(),
                        ),
                        "detail": str(source.get("location_detail", "")),
                        "source_method": source_method,
                        "map_display_mode": map_display_mode,
                        "status": marker_status,
                        "required_badge": required_badge,
                        "kind": "item",
                        "item_id": item_id,
                        "category": category,
                        "move_type": str(item.get("move_type") or ""),
                        "marker_asset": str(item.get("marker_asset") or ""),
                        "x": x,
                        "y": y,
                    })

        if watts_trader_items:
            coordinates = MAP_LOCATION_COORDINATES.get("meetup_spot")
            if coordinates is not None:
                x, y = coordinates
                represented_ids = [
                    item["objective_id"]
                    for item in watts_trader_items
                ]
                statuses = {
                    item["status"]
                    for item in watts_trader_items
                }
                shared_status = (
                    "available"
                    if "available" in statuses
                    else "unavailable"
                    if "unavailable" in statuses
                    else "obtained"
                )
                records.append({
                    "objective_id": "group:watts_traders",
                    "objective_ids": represented_ids,
                    "title": "Watts Traders",
                    "location_id": "meetup_spot",
                    "location": "Meetup Spot",
                    "detail": (
                        "Available from Watts Traders, located at the "
                        "Meetup Spot, Dappled Grove, East Lake Axewell, "
                        "Giant's Seat, Bridge Field, Giant's Cap, and "
                        "Hammerlocke Hills."
                    ),
                    "source_method": "watt_trader_group",
                    "map_display_mode": "representative",
                    "status": shared_status,
                    "required_badge": 0,
                    "kind": "item",
                    "category": "tr",
                    "marker_asset": "",
                    "watts_trader_items": watts_trader_items,
                    "x": x,
                    "y": y,
                })

        for pokemon in self.pokemon:
            pokemon_id = str(pokemon.get("id", "")).strip()
            if not pokemon_id:
                continue

            acquisitions = self._pokemon_acquisitions(pokemon)
            if not acquisitions:
                continue

            objective_id = f"pokemon:{pokemon_id}"
            objective_status = self._pokemon_status(pokemon)
            if objective_status == "obtained":
                continue

            title = str(pokemon.get("pokemon", "Unknown Pokémon"))

            for acquisition in acquisitions:
                required_badge = (
                    self._pokemon_acquisition_required_badge(
                        pokemon,
                        acquisition,
                    )
                )
                marker_status = self._source_marker_status(
                    objective_status,
                    required_badge,
                    self.earned_badges,
                )

                for location_id in self._map_location_ids(acquisition):
                    coordinates = MAP_LOCATION_COORDINATES.get(location_id)
                    if coordinates is None:
                        continue

                    x, y = coordinates
                    records.append({
                        "objective_id": objective_id,
                        "title": title,
                        "location_id": location_id,
                        "location": MAP_LOCATION_LABELS.get(
                            location_id,
                            location_id.replace("_", " ").title(),
                        ),
                        "detail": str(
                            acquisition.get("availability_note", "")
                        ),
                        "status": marker_status,
                        "required_badge": required_badge,
                        "kind": "pokemon",
                        "category": "pokemon",
                        "source_method": str(
                            acquisition.get("method", "")
                        ),
                        "minimum_star_level": acquisition.get(
                            "minimum_star_level"
                        ),
                        "marker_pokemon": str(
                            pokemon.get("marker_pokemon")
                            or pokemon.get("acquire_as")
                            or pokemon.get("pokemon")
                            or ""
                        ),
                        "marker_asset": str(
                            pokemon.get("marker_asset") or ""
                        ),
                        "x": x,
                        "y": y,
                    })

        return records

    @staticmethod
    def _map_marker_shadow(selected: bool) -> ft.BoxShadow:
        """Return the persistent visual treatment for a map marker."""

        return ft.BoxShadow(
            blur_radius=20 if selected else 7,
            spread_radius=4 if selected else 0,
            color=ft.Colors.with_opacity(
                0.72 if selected else 0.30,
                PRIMARY_BLUE if selected else ft.Colors.BLACK,
            ),
        )

    def _build_map_marker(
        self,
        record: dict[str, Any],
        marker_index: int,
    ) -> ft.Container:
        """Render one persistent sprite-based map marker."""

        objective_id = str(record["objective_id"])
        status = str(record["status"])
        selected = self._record_matches_selected_objective(record)

        if status == "obtained":
            status_icon = ft.Icons.CHECK_ROUNDED
            marker_color = PRIMARY_BLUE
        elif status == "available":
            status_icon = ft.Icons.PRIORITY_HIGH_ROUNDED
            marker_color = SUCCESS
        else:
            status_icon = ft.Icons.BLOCK_ROUNDED
            marker_color = DANGER

        marker_asset = self._marker_asset_for_record(record)

        # Pokémon sprites generally occupy less of their source canvas than
        # item sprites, so give them a larger rendered footprint.
        if record["kind"] == "pokemon":
            marker_size = 56
            sprite_size = 52
        else:
            marker_size = 48
            sprite_size = 42

        collision_index = int(record.get("collision_index", 0))
        collision_count = int(record.get("collision_count", 1))
        collision_x = 0.0
        collision_y = 0.0

        if collision_count > 1:
            collision_offsets = [
                (-23.0, -17.0),
                (23.0, 17.0),
                (23.0, -17.0),
                (-23.0, 17.0),
                (0.0, -29.0),
                (0.0, 29.0),
            ]
            collision_x, collision_y = collision_offsets[
                collision_index % len(collision_offsets)
            ]

        if record.get("source_method") == "watt_trader_group":
            main_visual: ft.Control = ft.Icon(
                ft.Icons.BOLT_ROUNDED,
                size=28,
                color="#FFD54F",
            )
        elif marker_asset is not None:
            main_visual = ft.Image(
                src=marker_asset,
                width=sprite_size,
                height=sprite_size,
                fit=ft.BoxFit.CONTAIN,
                error_content=ft.Icon(
                    ft.Icons.LOCATION_ON_ROUNDED,
                    size=22,
                    color="#07120B",
                ),
            )
        else:
            main_visual = ft.Icon(
                ft.Icons.LOCATION_ON_ROUNDED,
                size=22,
                color="#07120B",
            )

        marker = ft.Container(
            key=f"map-marker-{objective_id}-{marker_index}",
            content=ft.Stack(
                controls=[
                    ft.Container(
                        content=main_visual,
                        width=marker_size,
                        height=marker_size,
                        alignment=ft.Alignment.CENTER,
                        shadow=ft.BoxShadow(
                            blur_radius=7,
                            spread_radius=0,
                            color=ft.Colors.with_opacity(
                                0.30,
                                ft.Colors.BLACK,
                            ),
                        ),
                    ),
                    ft.Container(
                        content=ft.Icon(
                            status_icon,
                            size=11,
                            color=ft.Colors.WHITE,
                        ),
                        width=18,
                        height=18,
                        bgcolor=marker_color,
                        border=ft.Border.all(1.5, ft.Colors.WHITE),
                        border_radius=10,
                        right=0,
                        bottom=0,
                        alignment=ft.Alignment.CENTER,
                    ),
                ],
                width=marker_size + 5,
                height=marker_size + 5,
                clip_behavior=ft.ClipBehavior.NONE,
            ),
            width=marker_size + 5,
            height=marker_size + 5,
            left=(
                float(record["x"]) * self._map_render_width
                - marker_size / 2
                + collision_x
            ),
            top=(
                float(record["y"]) * self._map_render_height
                - marker_size / 2
                + collision_y
            ),
            opacity=1.0,
            scale=(
                self._selected_marker_pulse_scale
                if selected
                else 1.0
            ),
            shadow=self._map_marker_shadow(selected),
            animate_scale=ft.Animation(
                220,
                ft.AnimationCurve.EASE_OUT_BACK,
            ),
            on_click=lambda: self._handle_map_marker_click(record),
        )

        for represented_objective_id in self._record_objective_ids(record):
            self._map_markers_by_objective.setdefault(
                represented_objective_id,
                [],
            ).append(marker)

        return marker

    def _handle_map_marker_click(
        self,
        record: dict[str, Any],
    ) -> None:
        """Select a marker and open its mobile-friendly details."""

        represented_ids = self._record_objective_ids(record)
        selected_id = self._selected_map_objective_id
        if selected_id not in represented_ids and represented_ids:
            self._select_objective_for_map(represented_ids[0])
        self._show_map_marker_details(record)

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
            height=TOP_JOURNEY_CARD_HEIGHT
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

            objective_id = f"item:{item_id}"
            rows.append(
                self._register_objective_data_row(
                    objective_id,
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
                    color=(
                        ft.Colors.with_opacity(0.16, PRIMARY_BLUE)
                        if objective_id == self._selected_map_objective_id
                        else None
                    ),
                    on_select_change=(
                        lambda event, objective_id=objective_id:
                        self._select_objective_for_map(objective_id)
                    ),
                    ),
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
            show_checkbox_column=False,
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

        available_items = [
            item for item in self.items
            if str(item.get("id", "")).strip()
        ]
        if not available_items:
            return

        self._add_item_name_to_id = {
            str(item.get("name", "")).strip().casefold():
            str(item.get("id", "")).strip()
            for item in available_items
            if str(item.get("name", "")).strip()
        }
        suggestions = [
            ft.AutoCompleteSuggestion(
                key=str(item.get("name", "Unknown item")),
                value=str(item.get("name", "Unknown item")),
            )
            for item in available_items
        ]

        self._add_item_selector = ft.AutoComplete(
            value="",
            suggestions=suggestions,
            suggestions_max_height=280,
            width=420,
            on_change=self._handle_add_item_search_change,
            on_select=self._handle_add_item_search_select,
        )
        self._add_item_quantity = ft.TextField(
            label="Quantity",
            value="1",
            keyboard_type=ft.KeyboardType.NUMBER,
            width=120,
        )
        self._add_item_validation_text = ft.Text(
            "Choose an exact match from the suggestions.",
            color=TEXT_MUTED,
            size=12,
        )
        self._add_item_button = ft.Button(
            content="Add Objective",
            icon=ft.Icons.ADD_ROUNDED,
            bgcolor=SUCCESS,
            color="#07120B",
            icon_color="#07120B",
            disabled=True,
            on_click=self._confirm_add_item_objective,
        )

        dialog = ft.AlertDialog()
        dialog.modal = True
        dialog.title = ft.Text("Add Journey Objective", weight=ft.FontWeight.BOLD)
        dialog.content = ft.Column(
            controls=[
                ft.Text(
                    "Search the current Sword item catalog. Start typing an item, TM, or TR name, then choose an exact suggestion. Adding an item already on the checklist increases its required quantity.",
                    color=TEXT_SECONDARY,
                ),
                ft.Text(
                    "Start typing an item, TM, or TR name here",
                    color=TEXT_PRIMARY,
                    size=13,
                    weight=ft.FontWeight.W_600,
                ),
                self._add_item_selector,
                self._add_item_validation_text,
                self._add_item_quantity,
            ],
            spacing=10,
            tight=True,
        )
        dialog.actions = [
            ft.Button(content="Cancel", on_click=self._close_add_item_dialog),
            self._add_item_button,
        ]
        dialog.actions_alignment = ft.MainAxisAlignment.END
        self.page.show_dialog(dialog)

    def _selected_add_item_id(self) -> str:
        if self._add_item_selector is None:
            return ""
        entered_name = str(self._add_item_selector.value or "").strip().casefold()
        return self._add_item_name_to_id.get(entered_name, "")

    def _sync_add_item_validation(self) -> None:
        item_id = self._selected_add_item_id()
        has_input = bool(
            self._add_item_selector
            and str(self._add_item_selector.value or "").strip()
        )
        if self._add_item_button is not None:
            self._add_item_button.disabled = not bool(item_id)
        if self._add_item_validation_text is not None:
            if item_id:
                self._add_item_validation_text.value = "Ready to add to the Journey Checklist."
                self._add_item_validation_text.color = SUCCESS
            elif has_input:
                self._add_item_validation_text.value = "Choose an exact item name from the suggestions."
                self._add_item_validation_text.color = TEXT_MUTED
            else:
                self._add_item_validation_text.value = "Choose an exact match from the suggestions."
                self._add_item_validation_text.color = TEXT_MUTED
        if self._add_item_button is not None:
            self._add_item_button.update()
        if self._add_item_validation_text is not None:
            self._add_item_validation_text.update()

    def _handle_add_item_search_change(self, event: ft.Event[ft.AutoComplete]) -> None:
        del event
        self._sync_add_item_validation()

    def _handle_add_item_search_select(self, event: ft.AutoCompleteSelectEvent) -> None:
        del event
        self._sync_add_item_validation()

    def _clear_add_item_dialog_state(self) -> None:
        self._add_item_selector = None
        self._add_item_quantity = None
        self._add_item_button = None
        self._add_item_validation_text = None
        self._add_item_name_to_id = {}

    def _close_add_item_dialog(
        self,
        event: ft.Event[ft.Button] | None = None,
    ) -> None:
        del event
        self._clear_add_item_dialog_state()
        self.page.pop_dialog()
        self.page.update()

    def _confirm_add_item_objective(
        self,
        event: ft.Event[ft.Button],
    ) -> None:
        del event
        item_id = self._selected_add_item_id()
        quantity_text = str(
            self._add_item_quantity.value if self._add_item_quantity else "1"
        ).strip()
        try:
            quantity = int(quantity_text)
        except ValueError:
            quantity = 0

        if not item_id or quantity <= 0:
            self.page.show_dialog(ft.SnackBar(content=ft.Text(
                "Choose an exact objective and enter a quantity greater than zero."
            )))
            return

        self._clear_add_item_dialog_state()
        self.page.pop_dialog()
        self.page.run_task(self._add_item_objective, item_id, quantity)

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

    def _prepare_map_marker_records(self) -> list[dict[str, Any]]:
        """Build visible marker records and assign collision fan-out metadata."""

        marker_records = self._marker_records()

        if self._map_marker_filter == "items":
            marker_records = [
                record
                for record in marker_records
                if record.get("kind") == "item"
            ]
        elif self._map_marker_filter == "pokemon":
            marker_records = [
                record
                for record in marker_records
                if record.get("kind") == "pokemon"
            ]
        elif self._map_marker_filter == "available":
            marker_records = [
                record
                for record in marker_records
                if record.get("status") == "available"
            ]
        elif self._map_marker_filter == "unavailable":
            marker_records = [
                record
                for record in marker_records
                if record.get("status") == "unavailable"
            ]
        elif self._map_marker_filter == "current":
            current_objective_ids = set(
                self._current_objective_ids()
            )
            marker_records = [
                record
                for record in marker_records
                if any(
                    objective_id in current_objective_ids
                    for objective_id in self._record_objective_ids(record)
                )
            ]
        elif self._map_marker_filter == "highlighted":
            marker_records = [
                record
                for record in marker_records
                if self._record_matches_selected_objective(record)
            ]

        location_groups: dict[str, list[dict[str, Any]]] = {}
        for record in marker_records:
            location_id = str(record.get("location_id", ""))
            location_groups.setdefault(location_id, []).append(record)

        for grouped_records in location_groups.values():
            collision_count = len(grouped_records)
            for collision_index, record in enumerate(grouped_records):
                record["collision_index"] = collision_index
                record["collision_count"] = collision_count

        return marker_records

    def _build_responsive_map_stack(self) -> ft.Stack:
        """Build the map and markers against one shared measured canvas."""

        self._map_marker_generation += 1
        self._map_markers_by_objective = {}
        self._selected_marker_y = None

        marker_controls: list[ft.Control] = []
        for marker_index, record in enumerate(self._map_marker_records):
            marker_controls.append(
                self._build_map_marker(record, marker_index)
            )

            if (
                self._record_matches_selected_objective(record)
                and self._selected_marker_y is None
            ):
                self._selected_marker_y = float(record["y"])

        self._map_image = ft.Image(
            src="Galar_Map_Base.png",
            width=self._map_render_width,
            height=self._map_render_height,
            fit=ft.BoxFit.FILL,
            semantics_label="Base-game map of the Galar region",
        )

        self._map_stack = ft.Stack(
            controls=[
                self._map_image,
                *marker_controls,
            ],
            width=self._map_render_width,
            height=self._map_render_height,
            clip_behavior=ft.ClipBehavior.HARD_EDGE,
        )
        return self._map_stack

    def _handle_map_size_change(
        self,
        event: ft.LayoutSizeChangeEvent[ft.LayoutControl],
    ) -> None:
        """Keep the marker canvas synchronized with the rendered map width."""

        measured_width = min(float(event.width), float(MAP_RENDER_WIDTH))
        if measured_width <= 0:
            return

        measured_height = (
            measured_width * MAP_IMAGE_HEIGHT / MAP_IMAGE_WIDTH
        )

        if (
            abs(measured_width - self._map_render_width) < 0.5
            and abs(measured_height - self._map_render_height) < 0.5
        ):
            return

        self._map_render_width = measured_width
        self._map_render_height = measured_height

        if self._map_host is None:
            return

        self._map_host.height = measured_height
        self._map_host.content = self._build_responsive_map_stack()
        self._map_host.update()

    def _refresh_visible_map_markers(self) -> None:
        """Rebuild only marker controls while preserving the rendered map."""

        if self._map_stack is None or self._map_image is None:
            return

        self._map_marker_records = self._prepare_map_marker_records()
        self._map_marker_generation += 1
        self._map_markers_by_objective = {}
        self._selected_marker_y = None

        marker_controls: list[ft.Control] = []
        for marker_index, record in enumerate(self._map_marker_records):
            marker_controls.append(
                self._build_map_marker(record, marker_index)
            )
            if (
                self._record_matches_selected_objective(record)
                and self._selected_marker_y is None
            ):
                self._selected_marker_y = float(record["y"])

        self._map_stack.controls = [
            self._map_image,
            *marker_controls,
        ]
        self._map_stack.update()

    def _handle_map_marker_filter(
        self,
        event: ft.Event[ft.Dropdown],
    ) -> None:
        """Apply the selected map-marker visibility filter."""

        selected_filter = str(event.control.value or "all")
        if selected_filter not in {
            "all",
            "items",
            "pokemon",
            "available",
            "unavailable",
            "current",
            "highlighted",
        }:
            selected_filter = "all"

        if selected_filter == self._map_marker_filter:
            return

        self._map_marker_filter = selected_filter
        self._refresh_visible_map_markers()
        self.page.update()

    def _build_map_card(self) -> ft.Control:
        """Build the responsive Galar map and persistent objective markers."""

        self._map_marker_records = self._prepare_map_marker_records()

        # Start at the desktop cap. The host's measured-size event immediately
        # recalculates the canvas when the card is narrower.
        self._map_render_width = float(MAP_RENDER_WIDTH)
        self._map_render_height = float(MAP_RENDER_HEIGHT)

        self._map_host = ft.Container(
            key="journey-map-anchor",
            content=self._build_responsive_map_stack(),
            width=MAP_RENDER_WIDTH,
            height=MAP_RENDER_HEIGHT,
            border=ft.Border.all(1, BORDER_DEFAULT),
            border_radius=12,
            alignment=ft.Alignment.TOP_CENTER,
            clip_behavior=ft.ClipBehavior.ANTI_ALIAS,
            size_change_interval=80,
            on_size_change=self._handle_map_size_change,
        )

        mapped_count = len(self._map_marker_records)
        subtitle = (
            f"{mapped_count} objective marker"
            f"{'' if mapped_count == 1 else 's'} shown. "
            "Select a row or marker to focus it."
        )

        marker_filter = ft.Dropdown(
            label="Show markers",
            value=self._map_marker_filter,
            options=[
                ft.DropdownOption(
                    key="all",
                    text="Everything",
                ),
                ft.DropdownOption(
                    key="items",
                    text="Items",
                ),
                ft.DropdownOption(
                    key="pokemon",
                    text="Pokémon",
                ),
                ft.DropdownOption(
                    key="available",
                    text="All Available Objectives",
                ),
                ft.DropdownOption(
                    key="unavailable",
                    text="All Unavailable Objectives",
                ),
                ft.DropdownOption(
                    key="current",
                    text="Current Objectives Only",
                ),
                ft.DropdownOption(
                    key="highlighted",
                    text="Highlighted Marker Only",
                ),
            ],
            width=280,
            on_select=self._handle_map_marker_filter,
        )

        return self._build_card(
            title="Galar Map",
            icon=ft.Icons.MAP_OUTLINED,
            subtitle=subtitle,
            body=ft.Column(
                controls=[
                    ft.Container(
                        content=marker_filter,
                        alignment=ft.Alignment.CENTER_LEFT,
                    ),
                    self._map_host,
                ],
                spacing=12,
                horizontal_alignment=ft.CrossAxisAlignment.CENTER,
            ),
            col={"xs": 12, "lg": 6},
        )

    def _show_add_pokemon_dialog(
        self,
        event: ft.Event[ft.Button],
    ) -> None:
        """Search the unplanned catalog and add one exact Pokémon match."""

        del event
        available_pokemon = [
            pokemon
            for pokemon in self.pokemon_catalog
            if str(pokemon.get("id", "")).strip()
            not in self.planned_pokemon_ids
        ]
        if not available_pokemon:
            self.page.show_dialog(
                ft.SnackBar(
                    content=ft.Text(
                        "Every Pokémon in the current Journey catalog "
                        "is already in the Team Planner."
                    )
                )
            )
            return

        self._add_pokemon_name_to_id = {
            str(pokemon.get("pokemon", "")).strip().casefold():
            str(pokemon.get("id", "")).strip()
            for pokemon in available_pokemon
            if (
                str(pokemon.get("pokemon", "")).strip()
                and str(pokemon.get("id", "")).strip()
            )
        }

        suggestions: list[ft.AutoCompleteSuggestion] = []
        for pokemon in available_pokemon:
            pokemon_name = str(
                pokemon.get("pokemon", "Unknown Pokémon")
            ).strip()
            acquire_as = str(pokemon.get("acquire_as") or "").strip()

            search_key_parts = [pokemon_name]
            if (
                acquire_as
                and acquire_as.casefold() != pokemon_name.casefold()
            ):
                search_key_parts.append(acquire_as)

            suggestions.append(
                ft.AutoCompleteSuggestion(
                    key=" ".join(search_key_parts),
                    value=pokemon_name,
                )
            )

        self._add_pokemon_validation_text = ft.Text(
            "Choose an exact match from the suggestions.",
            color=TEXT_MUTED,
            size=12,
        )

        self._add_pokemon_selector = ft.AutoComplete(
            value="",
            suggestions=suggestions,
            suggestions_max_height=260,
            width=380,
            on_change=self._handle_add_pokemon_search_change,
            on_select=self._handle_add_pokemon_search_select,
        )

        self._add_pokemon_button = ft.Button(
            content="Add Pokémon",
            icon=ft.Icons.ADD_ROUNDED,
            bgcolor=SUCCESS,
            color="#07120B",
            icon_color="#07120B",
            disabled=True,
            on_click=self._confirm_add_pokemon,
        )

        dialog = ft.AlertDialog()
        dialog.modal = True
        dialog.title = ft.Text(
            "Add Pokémon to Team Planner",
            weight=ft.FontWeight.BOLD,
        )
        dialog.content = ft.Column(
            controls=[
                ft.Text(
                    (
                        "Search the current Sword Journey catalog. Its "
                        "objective, map marker, and linked evolution items "
                        "will be added automatically."
                    ),
                    color=TEXT_SECONDARY,
                ),
                ft.Text(
                    "Start typing a Pokémon name here",
                    color=TEXT_PRIMARY,
                    size=13,
                    weight=ft.FontWeight.W_600,
                ),
                self._add_pokemon_selector,
                self._add_pokemon_validation_text,
            ],
            spacing=10,
            tight=True,
        )
        dialog.actions = [
            ft.Button(
                content="Cancel",
                on_click=self._close_add_pokemon_dialog,
            ),
            self._add_pokemon_button,
        ]
        dialog.actions_alignment = ft.MainAxisAlignment.END
        self.page.show_dialog(dialog)

    def _selected_add_pokemon_id(self) -> str:
        """Resolve the current text only when it exactly matches a name."""

        if self._add_pokemon_selector is None:
            return ""

        entered_name = str(
            self._add_pokemon_selector.value or ""
        ).strip().casefold()
        return self._add_pokemon_name_to_id.get(entered_name, "")

    def _sync_add_pokemon_validation(self) -> None:
        """Enable Add only for an exact, currently unplanned catalog match."""

        pokemon_id = self._selected_add_pokemon_id()
        has_input = bool(
            self._add_pokemon_selector
            and str(self._add_pokemon_selector.value or "").strip()
        )

        if self._add_pokemon_button is not None:
            self._add_pokemon_button.disabled = not bool(pokemon_id)

        if self._add_pokemon_validation_text is not None:
            if pokemon_id:
                self._add_pokemon_validation_text.value = (
                    "Ready to add to the Team Planner."
                )
                self._add_pokemon_validation_text.color = SUCCESS
            elif has_input:
                self._add_pokemon_validation_text.value = (
                    "Choose an exact Pokémon name from the suggestions."
                )
                self._add_pokemon_validation_text.color = TEXT_MUTED
            else:
                self._add_pokemon_validation_text.value = (
                    "Choose an exact match from the suggestions."
                )
                self._add_pokemon_validation_text.color = TEXT_MUTED

        if self._add_pokemon_button is not None:
            self._add_pokemon_button.update()
        if self._add_pokemon_validation_text is not None:
            self._add_pokemon_validation_text.update()

    def _handle_add_pokemon_search_change(
        self,
        event: ft.Event[ft.AutoComplete],
    ) -> None:
        """Validate lightweight text input without refreshing My Journey."""

        del event
        self._sync_add_pokemon_validation()

    def _handle_add_pokemon_search_select(
        self,
        event: ft.AutoCompleteSelectEvent,
    ) -> None:
        """Validate a selected autocomplete suggestion immediately."""

        del event
        self._sync_add_pokemon_validation()

    def _clear_add_pokemon_dialog_state(self) -> None:
        """Release transient autocomplete dialog controls."""

        self._add_pokemon_selector = None
        self._add_pokemon_button = None
        self._add_pokemon_validation_text = None
        self._add_pokemon_name_to_id = {}

    def _close_add_pokemon_dialog(
        self,
        event: ft.Event[ft.Button] | None = None,
    ) -> None:
        del event
        self._clear_add_pokemon_dialog_state()
        self.page.pop_dialog()
        self.page.update()

    def _confirm_add_pokemon(
        self,
        event: ft.Event[ft.Button],
    ) -> None:
        del event
        pokemon_id = self._selected_add_pokemon_id()
        if not pokemon_id:
            self._sync_add_pokemon_validation()
            return

        self._clear_add_pokemon_dialog_state()
        self.page.pop_dialog()
        self.page.run_task(self._add_planned_pokemon, pokemon_id)

    async def _add_planned_pokemon(self, pokemon_id: str) -> None:
        """Persist one new Team Planner Pokémon."""

        if pokemon_id in self.planned_pokemon_ids:
            return

        updated_ids = [*self.planned_pokemon_ids, pokemon_id]
        save_succeeded = await self.app_state.save_planned_pokemon_ids(
            updated_ids
        )
        if not save_succeeded:
            self._show_save_error(
                "The Pokémon could not be added to the Team Planner."
            )
            return

        self.planned_pokemon_ids = updated_ids
        self._reload_planner_dependencies()
        self._refresh()

    def _request_remove_planned_pokemon(
        self,
        event: ft.Event[ft.IconButton],
        pokemon_id: str,
    ) -> None:
        """Always confirm removal and explain linked-item changes."""

        del event
        pokemon = next(
            (
                record
                for record in self.pokemon
                if str(record.get("id", "")) == pokemon_id
            ),
            None,
        )
        if pokemon is None:
            return

        pokemon_name = str(
            pokemon.get("pokemon", "this Pokémon")
        )
        impact_lines = [
            "This will remove its Current Objective and map marker.",
            (
                "Your acquired Pokémon data in My Team or My Box "
                "will not be deleted."
            ),
        ]

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

            current_required = self._required_item_quantity(item_id)
            new_required = max(0, current_required - quantity)
            item_name = next(
                (
                    str(item.get("name", item_id))
                    for item in self.items
                    if str(item.get("id", "")) == item_id
                ),
                item_id.replace("_", " ").title(),
            )
            impact_lines.append(
                (
                    f"The {item_name} requirement will change "
                    f"from {current_required} to {new_required}."
                )
            )

        dialog = ft.AlertDialog()
        dialog.modal = True
        dialog.title = ft.Text(
            f"Remove {pokemon_name} from the Team Planner?",
            weight=ft.FontWeight.BOLD,
        )
        dialog.content = ft.Column(
            controls=[
                ft.Text(line, color=TEXT_SECONDARY)
                for line in impact_lines
            ],
            spacing=8,
            tight=True,
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
                    lambda event, objective_id=pokemon_id:
                    self._confirm_remove_planned_pokemon(
                        event,
                        objective_id,
                    )
                ),
            ),
        ]
        dialog.actions_alignment = ft.MainAxisAlignment.END
        self.page.show_dialog(dialog)

    def _confirm_remove_planned_pokemon(
        self,
        event: ft.Event[ft.Button],
        pokemon_id: str,
    ) -> None:
        del event
        self.page.pop_dialog()
        self.page.run_task(
            self._remove_planned_pokemon,
            pokemon_id,
        )

    async def _remove_planned_pokemon(self, pokemon_id: str) -> None:
        """Persist removal without deleting acquired Pokémon history."""

        if pokemon_id not in self.planned_pokemon_ids:
            return

        updated_ids = [
            planned_id
            for planned_id in self.planned_pokemon_ids
            if planned_id != pokemon_id
        ]
        save_succeeded = await self.app_state.save_planned_pokemon_ids(
            updated_ids
        )
        if not save_succeeded:
            self._show_save_error(
                "The Pokémon could not be removed from the Team Planner."
            )
            return

        self.planned_pokemon_ids = updated_ids
        if self._selected_map_objective_id == f"pokemon:{pokemon_id}":
            self._selected_map_objective_id = None
            self._selected_marker_y = None

        self._reload_planner_dependencies()
        self._refresh()

    def _build_team_planner_card(self) -> ft.Control:
        rows: list[ft.DataRow] = []

        for pokemon in self.pokemon:
            pokemon_id = str(pokemon.get("id", ""))
            status = self._pokemon_status(pokemon)

            marker_asset = str(
                pokemon.get("marker_asset") or ""
            ).strip()

            pokemon_identity_controls: list[ft.Control] = []

            if marker_asset:
                pokemon_identity_controls.append(
                    ft.Image(
                        src=marker_asset,
                        width=58,
                        height=58,
                        fit=ft.BoxFit.CONTAIN,
                        semantics_label=(
                            f"{pokemon.get('acquire_as') or pokemon.get('pokemon')}"
                            " sprite"
                        ),
                    )
                )

            pokemon_identity_controls.extend(
                [
                    ft.Text(
                        str(pokemon.get("pokemon", "Unknown")),
                        color=TEXT_PRIMARY,
                        weight=ft.FontWeight.BOLD,
                        size=15,
                        text_align=ft.TextAlign.CENTER,
                    ),
                    ft.Text(
                        self._pokemon_acquisition_text(pokemon),
                        color=TEXT_SECONDARY,
                        size=13,
                        text_align=ft.TextAlign.CENTER,
                    ),
                    ft.Text(
                        str(pokemon.get("evolution_summary", "")),
                        color=TEXT_MUTED,
                        size=12,
                        italic=True,
                        text_align=ft.TextAlign.CENTER,
                    ),
                ]
            )

            pokemon_cell_controls: list[ft.Control] = [
                ft.Container(
                    content=self._status_icon(status),
                    width=52,
                    alignment=ft.Alignment.CENTER,
                ),
                ft.Container(
                    content=ft.Column(
                        controls=pokemon_identity_controls,
                        spacing=2,
                        horizontal_alignment=(
                            ft.CrossAxisAlignment.CENTER
                        ),
                        alignment=ft.MainAxisAlignment.CENTER,
                    ),
                    width=300,
                    alignment=ft.Alignment.CENTER,
                ),
            ]

            objective_id = f"pokemon:{pokemon_id}"
            rows.append(
                self._register_objective_data_row(
                    objective_id,
                    ft.DataRow(
                        cells=[
                            ft.DataCell(
                                ft.Container(
                                    content=ft.Row(
                                        controls=pokemon_cell_controls,
                                        spacing=8,
                                        vertical_alignment=(
                                            ft.CrossAxisAlignment.CENTER
                                        ),
                                    ),
                                    width=360,
                                    height=150,
                                    alignment=ft.Alignment.CENTER_LEFT,
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
                                self._pokemon_encounter_options_control(
                                    pokemon
                                )
                            ),
                            ft.DataCell(
                                self._pokemon_more_locations_control(
                                    pokemon
                                )
                            ),
                            ft.DataCell(
                                self._build_pokemon_obtained_action(
                                    pokemon,
                                    status,
                                )
                            ),
                            ft.DataCell(
                                ft.IconButton(
                                    icon=ft.Icons.DELETE_OUTLINE_ROUNDED,
                                    icon_color=DANGER,
                                    tooltip="Remove from Team Planner",
                                    on_click=(
                                        lambda event,
                                        objective_id=pokemon_id:
                                        self._request_remove_planned_pokemon(
                                            event,
                                            objective_id,
                                        )
                                    ),
                                )
                            ),
                        ],
                        color=(
                            ft.Colors.with_opacity(
                                0.16,
                                PRIMARY_BLUE,
                            )
                            if (
                                objective_id
                                == self._selected_map_objective_id
                            )
                            else None
                        ),
                        on_select_change=(
                            lambda event, objective_id=objective_id:
                            self._select_objective_for_map(objective_id)
                        ),
                    ),
                )
            )

        table = ft.DataTable(
            columns=[
                self._column("Pokémon"),
                self._column("Location"),
                self._column("Encounter Options"),
                self._column("More Locations"),
                self._column("Mark as acquired"),
                self._column("Remove"),
            ],
            rows=rows,
            border=ft.Border.all(1, BORDER_DEFAULT),
            border_radius=12,
            heading_row_color=SURFACE_RAISED,
            column_spacing=24,
            data_row_min_height=150,
            data_row_max_height=220,
            show_checkbox_column=False,
        )

        return self._build_card(
            title="Team Planner",
            icon=ft.Icons.GROUP_ADD_OUTLINED,
            subtitle=(
                "Planned final team members with acquisition, encounter, "
                "and evolution guidance."
            ),
            body=ft.Column(
                controls=[
                    ft.Row(
                        controls=[
                            ft.Button(
                                content="Add Pokémon",
                                icon=ft.Icons.ADD_ROUNDED,
                                bgcolor=SUCCESS,
                                color="#07120B",
                                icon_color="#07120B",
                                on_click=self._show_add_pokemon_dialog,
                            )
                        ],
                        alignment=ft.MainAxisAlignment.END,
                    ),
                    ft.Row(
                        controls=[table],
                        scroll=ft.ScrollMode.AUTO,
                    ),
                ],
                spacing=12,
            ),
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

    @staticmethod
    def _selected_row_color(selected: bool) -> str:
        """Return the persistent background used for the selected objective."""

        return (
            ft.Colors.with_opacity(0.16, PRIMARY_BLUE)
            if selected
            else SURFACE_RAISED
        )

    @staticmethod
    def _selected_row_border(selected: bool) -> ft.Border:
        """Return a subtle blue border for the selected objective."""

        return ft.Border.all(
            2 if selected else 1,
            (
                ft.Colors.with_opacity(0.85, PRIMARY_BLUE)
                if selected
                else BORDER_DEFAULT
            ),
        )

    def _register_objective_data_row(
        self,
        objective_id: str,
        row: ft.DataRow,
    ) -> ft.DataRow:
        self._objective_data_rows.setdefault(objective_id, []).append(row)
        return row

    def _build_objective_row(
        self,
        *,
        objective_id: str,
        status: str,
        title: str,
        detail: str,
        sprite_asset: str | None = None,
        action: ft.Control | None = None,
    ) -> ft.Control:
        """Build a selectable Current Objectives row."""

        selected = objective_id == self._selected_map_objective_id

        row_container = ft.Container(
            content=ft.Row(
                controls=[
                    ft.Container(
                        content=self._status_icon(status),
                        width=34,
                        alignment=ft.Alignment.CENTER,
                    ),
                    ft.Container(
                        content=(
                            ft.Image(
                                src=sprite_asset,
                                width=42,
                                height=42,
                                fit=ft.BoxFit.CONTAIN,
                                semantics_label=f"{title} sprite",
                            )
                            if sprite_asset
                            else ft.Container(width=42, height=42)
                        ),
                        width=48,
                        height=48,
                        alignment=ft.Alignment.CENTER,
                    ),
                    ft.Column(
                        controls=[
                            ft.Text(
                                title,
                                color=TEXT_PRIMARY,
                                weight=ft.FontWeight.W_600,
                                size=14,
                            ),
                            ft.Text(
                                detail,
                                color=TEXT_SECONDARY,
                                size=12,
                            ),
                        ],
                        spacing=2,
                        expand=True,
                        alignment=ft.MainAxisAlignment.CENTER,
                    ),
                    *([action] if action is not None else []),
                ],
                spacing=8,
                vertical_alignment=ft.CrossAxisAlignment.CENTER,
            ),
            padding=12,
            bgcolor=self._selected_row_color(selected),
            border=self._selected_row_border(selected),
            border_radius=12,
            ink=True,
            on_click=lambda: self._select_objective_for_map(
                objective_id
            ),
        )
        self._objective_row_containers.setdefault(
            objective_id,
            [],
        ).append(row_container)
        return row_container

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
            on_click=lambda: self._request_item_completion(
                item,
                obtained + 1,
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
    def _pokemon_encounter_option_line(
        pokemon: dict[str, Any],
        encounter: dict[str, Any],
    ) -> str:
        """Format one normalized encounter variant for Team Planner."""

        acquisition = pokemon.get("primary_acquisition", {})
        raw_method = encounter.get("method") or acquisition.get("method", "")
        method = (
            str(raw_method).replace("_", " ").title()
            if raw_method
            else "Encounter"
        )
        method = method.replace("Max Raid Battle", "Max Raid")

        weather = str(encounter.get("weather") or "").strip()

        rarity = encounter.get("rarity_percent")
        rarity_text = f"{rarity}%" if rarity is not None else ""

        min_level = encounter.get("level_min")
        max_level = encounter.get("level_max")
        if min_level is None and max_level is None:
            level_text = ""
        elif min_level == max_level:
            level_text = f"Lv. {min_level}"
        elif min_level is None:
            level_text = f"Lv. {max_level}"
        elif max_level is None:
            level_text = f"Lv. {min_level}"
        else:
            level_text = f"Lv. {min_level}–{max_level}"

        details = [
            value
            for value in (rarity_text, level_text, weather)
            if value
        ]
        return (
            f"{method}: {' · '.join(details)}"
            if details
            else method
        )

    @classmethod
    def _pokemon_encounter_options_control(
        cls,
        pokemon: dict[str, Any],
    ) -> ft.Control:
        """Render every encounter variant for the curated acquisition."""

        acquisition = pokemon.get("primary_acquisition", {})
        raw_encounters = acquisition.get("encounters", [])
        encounters = (
            [
                encounter
                for encounter in raw_encounters
                if isinstance(encounter, dict)
            ]
            if isinstance(raw_encounters, list)
            else []
        )

        if encounters:
            return ft.Container(
                content=ft.Column(
                    controls=[
                        ft.Text(
                            cls._pokemon_encounter_option_line(
                                pokemon,
                                encounter,
                            ),
                            color=TEXT_SECONDARY,
                            size=13,
                            width=380,
                        )
                        for encounter in encounters
                    ],
                    spacing=5,
                    tight=True,
                ),
                width=400,
                alignment=ft.Alignment.CENTER_LEFT,
            )

        raw_method = str(acquisition.get("method") or "").strip()
        method = (
            raw_method.replace("_", " ").title()
            if raw_method
            else "Details forthcoming"
        )
        method = method.replace("Max Raid Battle", "Max Raid")

        availability_note = str(
            acquisition.get("availability_note") or ""
        ).strip()

        controls: list[ft.Control] = [
            ft.Text(
                method,
                color=TEXT_SECONDARY,
                size=13,
                weight=ft.FontWeight.W_600,
                width=380,
            )
        ]
        if availability_note:
            controls.append(
                ft.Text(
                    availability_note,
                    color=TEXT_MUTED,
                    size=12,
                    italic=True,
                    width=380,
                )
            )

        return ft.Container(
            content=ft.Column(
                controls=controls,
                spacing=4,
                tight=True,
            ),
            width=400,
            alignment=ft.Alignment.CENTER_LEFT,
        )

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
        height: float | None = None,
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
            content=ft.Column(
                controls=controls,
                spacing=16,
            ),
            padding=CARD_PADDING,
            bgcolor=SURFACE,
            border=ft.Border.all(1, BORDER_DEFAULT),
            border_radius=CARD_RADIUS,
            col=col,
            height=height,
        )