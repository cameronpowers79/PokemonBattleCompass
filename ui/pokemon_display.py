"""Player-facing name for an owned Pokémon; never use for species mechanics."""

def pokemon_display_name(pokemon: dict) -> str:
    return str(pokemon.get("Nickname") or "").strip() or str(pokemon.get("Pokemon") or "").strip()
