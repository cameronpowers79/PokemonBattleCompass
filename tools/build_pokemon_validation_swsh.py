"""Build Pokémon-name validation data from packaged PokéSprite assets."""

from __future__ import annotations

import json
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
SPRITE_DIR = (
    PROJECT_ROOT
    / "assets"
    / "raw"
    / "pokesprite"
    / "pokemon-gen8"
    / "regular"
)
OUTPUT_PATH = (
    PROJECT_ROOT
    / "data"
    / "pokemon_validation_swsh.json"
)

IGNORED_SUFFIXES = (
    "-texture",
    "-gmax",
    "-galar",
)

DISPLAY_NAME_OVERRIDES = {
    "farfetchd": "Farfetch'd",
    "sirfetchd": "Sirfetch'd",
    "flabebe": "Flabébé",
    "ho-oh": "Ho-Oh",
    "jangmo-o": "Jangmo-o",
    "hakamo-o": "Hakamo-o",
    "kommo-o": "Kommo-o",
    "mime-jr": "Mime Jr.",
    "mr-mime": "Mr. Mime",
    "mr-rime": "Mr. Rime",
    "nidoran-f": "Nidoran♀",
    "nidoran-m": "Nidoran♂",
    "porygon-z": "Porygon-Z",
    "type-null": "Type: Null",
}


def strip_display_suffixes(sprite_stem: str) -> str:
    """Remove packaging/display variants that are not separate team names."""

    cleaned = sprite_stem

    suffix_removed = True

    while suffix_removed:
        suffix_removed = False

        for suffix in IGNORED_SUFFIXES:
            if cleaned.endswith(suffix):
                cleaned = cleaned.removesuffix(
                    suffix
                )
                suffix_removed = True

    return cleaned


def display_name_from_slug(slug: str) -> str:
    """Convert a PokéSprite filename slug into a player-facing name."""

    override = DISPLAY_NAME_OVERRIDES.get(
        slug
    )

    if override:
        return override

    return " ".join(
        part.capitalize()
        for part in slug.split("-")
        if part
    )


def build_validation_names() -> list[str]:
    """Return unique display names represented by regular sprite files."""

    if not SPRITE_DIR.exists():
        raise FileNotFoundError(
            f"PokéSprite directory not found: {SPRITE_DIR}"
        )

    names: set[str] = set()

    for sprite_path in SPRITE_DIR.glob(
        "*.png"
    ):
        base_slug = strip_display_suffixes(
            sprite_path.stem
        )

        if not base_slug:
            continue

        names.add(
            display_name_from_slug(
                base_slug
            )
        )

    return sorted(
        names,
        key=str.casefold,
    )


def main() -> None:
    """Write the generated validation list to the data directory."""

    names = build_validation_names()

    OUTPUT_PATH.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    OUTPUT_PATH.write_text(
        json.dumps(
            names,
            indent=2,
            ensure_ascii=False,
        )
        + "\n",
        encoding="utf-8",
    )

    print(
        f"Wrote {len(names)} Pokémon names to "
        f"{OUTPUT_PATH.relative_to(PROJECT_ROOT)}."
    )


if __name__ == "__main__":
    main()
