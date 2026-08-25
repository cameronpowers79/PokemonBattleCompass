"""Rule tables for Pokémon Sword Journey acquisition validation.

These rules intentionally model only deterministic progression gates that the
Battle Compass can validate from journey_pokemon.json. Unknown locations or
methods are reported for review rather than guessed.
"""

from __future__ import annotations

# Highest wild Pokémon level that can be caught after each badge count.
# Badge 8 removes the level restriction for the purposes of this validator.
CATCH_LEVEL_CAP_BY_BADGES: dict[int, int | None] = {
    0: 20,
    1: 25,
    2: 30,
    3: 35,
    4: 40,
    5: 45,
    6: 50,
    7: 55,
    8: None,
}

# Earliest badge count at which these Wild Area weather states can occur.
WEATHER_REQUIRED_BADGES: dict[str, int] = {
    "Sandstorm": 3,
    "Snowstorm": 3,
    "Fog": 8,
}

# Earliest badge count at which a Max Raid star tier becomes available.
RAID_STAR_REQUIRED_BADGES: dict[int, int] = {
    1: 0,
    2: 1,
    3: 3,
    4: 5,
    5: 8,
}

# Deterministic story/access gates for locations represented in
# journey_pokemon.json. Sub-area aliases are included explicitly so an
# unfamiliar future location is surfaced as REVIEW instead of silently folded
# into an incorrect parent rule.
LOCATION_REQUIRED_BADGES: dict[str, int] = {
    # Opening / pre-Milo
    "Postwick": 0,
    "Postwick — Leon's room": 0,
    "Slumbering Weald": 0,
    "Route 1": 0,
    "Route 2": 0,
    "Route 2 - Lakeside": 6,
    "Route 2 — Lake": 0,
    "Rolling Fields": 0,
    "Rolling Fields - Area 2": 0,
    "Dappled Grove": 0,
    "West Lake Axewell": 0,
    "East Lake Axewell": 0,
    "South Lake Miloch": 0,
    "North Lake Miloch": 0,
    "Watchtower Ruins": 0,
    "Giant's Seat": 0,
    "Motostoke": 0,
    "Route 3": 0,
    "Galar Mine": 0,
    "Route 4": 0,
    "Turffield": 0,
    "Turffield — in-game trade": 0,

    # After Milo
    "Route 5": 1,
    "Route 5 Pokémon Nursery": 1,
    "Route 5 — Pokémon Nursery": 1,
    "Hulbury": 1,

    # After Nessa / Kabu approach
    "Galar Mine No. 2": 2,
    "Motostoke Outskirts": 2,
    "Motostoke - Gym": 2,
    "Motostoke — Gym": 2,

    # Wild Area land regions are traversable from the initial Wild Area visit.
    # Catch-level and weather gates determine whether a particular encounter is
    # actually obtainable.
    "Motostoke Riverbank": 0,
    "Bridge Field": 0,
    "Stony Wilderness": 0,
    "Stony Wilderness — Area 2": 0,
    "Stony Wilderness — Area 3": 0,
    "Dusty Bowl": 0,
    "Giant's Mirror": 0,
    "Giant's Cap": 0,
    "Giant's Cap — Area 2": 0,
    "Hammerlocke Hills": 0,

    # Route 6 is story-gated until after Kabu.
    "Route 6": 3,
    "Route 6 — Cara Liss": 3,

    # After Bea
    "Glimwood Tangle": 4,
    "Ballonlea": 4,
    "Ballonlea — in-game trade": 4,

    # After Opal
    "Route 7": 5,
    "Route 8": 5,
    "Route 8 — Steamdrift Way": 5,
    "Circhester": 5,
    "Circhester — in-game trade": 5,

    # After Circhester badge / Water Bike route
    "Route 9": 6,
    "Route 9 — Circhester Bay": 6,
    "Route 9 — Outer Spikemuth": 6,
    "Axew's Eye": 6,
    "Lake of Outrage": 6,

    # Wyndon / endgame
    "Route 10": 8,
    "Route 10 — Winter Hill Station": 8,
    "Energy Plant — Tower Summit": 8,
    "Wyndon — Battle Tower": 8,

    # Generic Wild Area is intentionally permissive; specific northern-area
    # records should use their concrete locations. Explicit acquisition gates
    # can still raise this value.
    "Wild Area": 0,
}


# Verified one-off acquisition gates that cannot be derived reliably from the
# generic location / weather / level / raid-star rules alone.
#
# Keys are (target Pokémon, acquisition method, acquisition location).
# These are intentionally exact: a future special acquisition should surface
# for review unless it has been explicitly verified.
VERIFIED_ACQUISITION_BADGES: dict[tuple[str, str, str], int] = {
    ("Persian", "in_game_trade", "Turffield — in-game trade"): 0,
    ("Wynaut", "breeding", "Route 5 Pokémon Nursery"): 1,
    ("Throh", "in_game_trade", "Circhester — in-game trade"): 5,
    ("Toxtricity", "gift", "Route 5 — Pokémon Nursery"): 1,
    ("Runerigus", "max_raid_battle", "Watchtower Ruins"): 0,
    ("Cofagrigus", "in_game_trade", "Ballonlea — in-game trade"): 4,
    ("Charizard", "gift", "Postwick — Leon's room"): 8,
    ("Silvally", "gift", "Wyndon — Battle Tower"): 8,
    ("Zacian", "story_encounter", "Energy Plant — Tower Summit"): 8,
    ("Eternatus", "story_encounter", "Energy Plant — Tower Summit"): 8,
}

# Methods for which the wild catch-level restriction should be evaluated.
WILD_CATCH_METHODS: set[str] = {
    "wild_encounter",
    "wandering_encounter",
}

# Encounter labels that still represent wild catches when nested under a
# wild acquisition.
WILD_ENCOUNTER_METHOD_LABELS: set[str] = {
    "Random",
    "Overworld",
    "Fishing",
    "Wandering",
    "Underground",
    "Surf",
    "Flying",
    "Berry Tree",
    "Interact",
}


def badges_needed_for_wild_level(level: int | float | None) -> int | None:
    """Return the first badge count whose catch cap includes *level*.

    None means there is no usable level to evaluate.
    """

    if level is None:
        return None

    try:
        numeric_level = int(level)
    except (TypeError, ValueError):
        return None

    for badges in range(0, 9):
        cap = CATCH_LEVEL_CAP_BY_BADGES[badges]
        if cap is None or numeric_level <= cap:
            return badges

    return 8


# These acquisition methods can have story, trade-partner, or parent-access
# requirements that are not derivable from the current encounter fields alone.
METHODS_WITH_POSSIBLE_UNMODELED_GATES: set[str] = {
    "gift",
    "story_encounter",
    "in_game_trade",
    "breeding",
}