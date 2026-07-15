"""
Held-item recommendation logic.

Evaluates a Pokémon's current build and returns unranked modeled items
that fit its moves, typing, stats, and longer-battle play patterns.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable


DAMAGING_CATEGORIES = {
    "Physical",
    "Special",
}

LONGEVITY_TAGS = {
    "RecoveryMove",
    "HPStealingMove",
    "Protection",
    "DefenseSetup",
    "SpecialDefenseSetup",
    "MixedDefenseSetup",
    "Screen",
    "Hazard",
    "DirectStatus",
    "PassiveDamage",
    "Substitute",
    "StatReset",
}

NON_HP_STATS = (
    "ATK",
    "DEF",
    "SPA",
    "SPD",
    "SPE",
)


@dataclass(frozen=True)
class ItemRecommendation:
    """One applicable modeled held-item recommendation."""

    item: str
    description: str
    reasons: tuple[str, ...]


def recommend_held_items(
    *,
    pokemon: dict,
    moves_data: list[dict],
    items_data: list[dict],
) -> list[ItemRecommendation]:
    """
    Return every modeled held item that fits the Pokémon's current build.

    Recommendations are intentionally unranked. The order follows the
    modeled item data so the UI does not imply unsupported confidence or
    an objectively best build.
    """

    move_lookup = _build_move_lookup(
        moves_data
    )

    moves = _pokemon_moves(
        pokemon,
        move_lookup,
    )

    damaging_moves = [
        move
        for move in moves
        if move.get("Category")
        in DAMAGING_CATEGORIES
    ]

    recommendations: list[
        ItemRecommendation
    ] = []

    for item in items_data:
        item_name = _string_value(
            item.get("Item")
        )

        if not item_name or item_name == "None":
            continue

        rule = _string_value(
            item.get("RecommendationRule")
        )

        description = _string_value(
            item.get("Description")
        )

        reasons = _evaluate_rule(
            rule=rule,
            pokemon=pokemon,
            item=item,
            moves=moves,
            damaging_moves=damaging_moves,
        )

        if reasons:
            recommendations.append(
                ItemRecommendation(
                    item=item_name,
                    description=description,
                    reasons=tuple(reasons),
                )
            )

    return recommendations


def _evaluate_rule(
    *,
    rule: str,
    pokemon: dict,
    item: dict,
    moves: list[dict],
    damaging_moves: list[dict],
) -> list[str]:
    """Evaluate one item's recommendation rule."""

    if rule == "TypeFocus":
        return _type_focus_reasons(
            pokemon=pokemon,
            item=item,
            damaging_moves=damaging_moves,
        )

    if rule == "SpecialFocus":
        return _special_focus_reasons(
            pokemon=pokemon,
            damaging_moves=damaging_moves,
        )

    if rule == "Coverage":
        return _coverage_reasons(
            damaging_moves
        )

    if rule == "FieldLongevity":
        return _field_longevity_reasons(
            pokemon=pokemon,
            moves=moves,
        )

    # Eviolite remains inactive until team records contain reliable
    # evolution-eligibility metadata.
    if rule == "CanEvolve":
        return []

    return []


def _type_focus_reasons(
    *,
    pokemon: dict,
    item: dict,
    damaging_moves: list[dict],
) -> list[str]:
    """
    Recommend a type booster for concentrated offense or meaningful STAB.

    The item applies when either:
    - at least two damaging moves share the boosted type; or
    - the type is STAB and represents at least one-third of all damaging
      moves.
    """

    boosted_type = _string_value(
        item.get("MoveTypeAffected")
    )

    if not boosted_type:
        return []

    total_damaging_moves = len(
        damaging_moves
    )

    if total_damaging_moves == 0:
        return []

    matching_moves = [
        move
        for move in damaging_moves
        if _string_value(
            move.get("Type")
        )
        == boosted_type
    ]

    matching_count = len(
        matching_moves
    )

    if matching_count == 0:
        return []

    pokemon_types = {
        _string_value(
            pokemon.get("Type1")
        ),
        _string_value(
            pokemon.get("Type2")
        ),
    }

    is_stab = (
        boosted_type in pokemon_types
    )

    has_multiple_attacks = (
        matching_count >= 2
    )

    has_meaningful_stab_share = (
        is_stab
        and (
            matching_count
            / total_damaging_moves
        )
        >= (1 / 3)
    )

    if not (
        has_multiple_attacks
        or has_meaningful_stab_share
    ):
        return []

    if has_multiple_attacks:
        return [
            (
                f"Knows {matching_count} "
                f"{boosted_type}-type attacks."
            )
        ]

    return [
        (
            f"{boosted_type} is one of its types "
            f"and represents {matching_count} of "
            f"its {total_damaging_moves} damaging "
            "moves."
        )
    ]


def _special_focus_reasons(
    *,
    pokemon: dict,
    damaging_moves: list[dict],
) -> list[str]:
    """Recommend Wise Glasses for a Special-focused moveset."""

    special_count = sum(
        1
        for move in damaging_moves
        if move.get("Category")
        == "Special"
    )

    if special_count < 3:
        return []

    special_attack = _numeric_value(
        pokemon.get("SPA")
    )

    reasons = [
        (
            f"Knows {special_count} "
            "Special attacks."
        )
    ]

    if special_attack > 0:
        reasons.append(
            f"Special Attack: {special_attack}."
        )

    return reasons


def _coverage_reasons(
    damaging_moves: list[dict],
) -> list[str]:
    """Recommend Expert Belt for broad offensive type coverage."""

    damaging_types = {
        move_type
        for move in damaging_moves
        if (
            move_type := _string_value(
                move.get("Type")
            )
        )
    }

    type_count = len(
        damaging_types
    )

    if type_count < 3:
        return []

    return [
        (
            "Knows damaging attacks of "
            f"{type_count} different types."
        )
    ]


def _field_longevity_reasons(
    *,
    pokemon: dict,
    moves: list[dict],
) -> list[str]:
    """
    Recommend Leftovers when multiple build signals suggest field longevity.

    No individual stat pattern or move mechanic is required. At least two
    independent signals must apply.
    """

    reasons: list[str] = []

    non_hp_values = {
        stat_name: _numeric_value(
            pokemon.get(stat_name)
        )
        for stat_name in NON_HP_STATS
    }

    non_hp_total = sum(
        non_hp_values.values()
    )

    defense_total = (
        non_hp_values["DEF"]
        + non_hp_values["SPD"]
    )

    if (
        non_hp_total > 0
        and (
            defense_total
            / non_hp_total
        )
        >= 0.45
    ):
        defensive_share = round(
            (
                defense_total
                / non_hp_total
            )
            * 100
        )

        reasons.append(
            (
                "Defense and Special Defense "
                f"make up {defensive_share}% of "
                "its non-HP stats."
            )
        )

    hp = _numeric_value(
        pokemon.get("HP")
    )

    all_current_stats = [
        hp,
        *non_hp_values.values(),
    ]

    if (
        hp > 0
        and hp == max(
            all_current_stats,
            default=0,
        )
    ):
        reasons.append(
            (
                "HP is its highest current "
                "stat."
            )
        )

    longevity_tags = sorted(
        {
            tag
            for move in moves
            for tag in _mechanics_tags(
                move
            )
            if tag in LONGEVITY_TAGS
        }
    )

    if longevity_tags:
        reasons.append(
            _longevity_tag_reason(
                longevity_tags
            )
        )

    if len(reasons) < 2:
        return []

    return reasons


def _longevity_tag_reason(
    tags: list[str],
) -> str:
    """Return a concise explanation for longer-field move mechanics."""

    if "RecoveryMove" in tags:
        return "Knows a recovery move."

    if "HPStealingMove" in tags:
        return "Knows an HP-stealing attack."

    if "Protection" in tags:
        return "Knows a protection move."

    if (
        "DefenseSetup" in tags
        or "SpecialDefenseSetup" in tags
        or "MixedDefenseSetup" in tags
    ):
        return (
            "Knows a move that strengthens "
            "its defenses."
        )

    if "Screen" in tags:
        return "Knows a protective screen move."

    if "Hazard" in tags:
        return "Supports longer battles with an entry hazard."

    if (
        "PassiveDamage" in tags
        or "DirectStatus" in tags
    ):
        return (
            "Uses status or passive damage "
            "to support longer battles."
        )

    if "Substitute" in tags:
        return "Uses Substitute to remain active longer."

    if "StatReset" in tags:
        return (
            "Can reset stat changes during "
            "longer battles."
        )

    return "Its moves support longer battles."


def _pokemon_moves(
    pokemon: dict,
    move_lookup: dict[str, dict],
) -> list[dict]:
    """Return the Pokémon's four recognized move records."""

    moves: list[dict] = []

    for slot in range(1, 5):
        move_name = _string_value(
            pokemon.get(
                f"Move{slot}"
            )
        )

        if not move_name:
            continue

        move = move_lookup.get(
            move_name
        )

        if move is not None:
            moves.append(
                move
            )

    return moves


def _build_move_lookup(
    moves_data: Iterable[dict],
) -> dict[str, dict]:
    """Build a move-name lookup from bundled move data."""

    return {
        move_name: move
        for move in moves_data
        if (
            move_name := _string_value(
                move.get("Move")
            )
        )
    }


def _mechanics_tags(
    move: dict,
) -> set[str]:
    """Return normalized MechanicsTags for one move."""

    raw_tags = move.get(
        "MechanicsTags"
    )

    if isinstance(
        raw_tags,
        list,
    ):
        return {
            tag.strip()
            for tag in raw_tags
            if (
                isinstance(tag, str)
                and tag.strip()
            )
        }

    # Temporary compatibility with any locally edited record still using
    # semicolon-delimited text.
    if isinstance(
        raw_tags,
        str,
    ):
        return {
            tag.strip()
            for tag in raw_tags.split(";")
            if tag.strip()
        }

    return set()


def _numeric_value(
    value: object,
) -> int:
    """Convert a stored stat value to an integer."""

    if isinstance(
        value,
        bool,
    ):
        return int(value)

    if isinstance(
        value,
        int,
    ):
        return value

    if isinstance(
        value,
        float,
    ):
        return int(value)

    if isinstance(
        value,
        str,
    ):
        try:
            return int(
                value.strip()
            )
        except ValueError:
            return 0

    return 0


def _string_value(
    value: object,
) -> str:
    """Return a clean string or an empty string."""

    if not isinstance(
        value,
        str,
    ):
        return ""

    return value.strip()