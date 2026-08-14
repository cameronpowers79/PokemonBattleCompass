import base64
import re
import sys
from io import BytesIO
from pathlib import Path

from PIL import Image

from ui.constants import SPRITE_DIR, TYPE_BADGE_DIR

try:
    from ui.asset_manifest import BUNDLED_ASSETS
except ImportError:
    BUNDLED_ASSETS = frozenset()


PROJECT_ROOT = Path(__file__).resolve().parents[1]
ASSETS_DIR = PROJECT_ROOT / "assets"

IS_WEB = sys.platform == "emscripten"

HELD_ITEM_SPRITE_DIR = (
    ASSETS_DIR
    / "raw"
    / "pokesprite"
    / "items"
    / "hold-item"
)

PLATE_SPRITE_DIR = (
    ASSETS_DIR
    / "raw"
    / "pokesprite"
    / "items"
    / "plate"
)

INCENSE_SPRITE_DIR = (
    ASSETS_DIR
    / "raw"
    / "pokesprite"
    / "items"
    / "incense"
)

NORMALIZED_SPRITE_DIR = (
    ASSETS_DIR
    / "runtime"
    / "pokemon-gen8"
    / "regular"
)


def _asset_src(path: Path) -> str:
    """Return a browser/Flet asset path relative to the asset root."""

    return path.relative_to(ASSETS_DIR).as_posix()


def asset_exists(path: Path) -> bool:
    """Return whether an app asset exists on the active platform.

    Native builds can query the real filesystem directly. Static web builds
    cannot see Flet's published asset tree from Pyodide, so they use the
    generated asset manifest instead of making blocking HTTP probe requests.
    """

    if not IS_WEB:
        return path.exists()

    try:
        asset_src = _asset_src(path)
    except ValueError:
        return False

    return asset_src in BUNDLED_ASSETS


def image_to_base64(
    path,
    crop_transparency=False,
    output_size=None,
    resampling=Image.Resampling.NEAREST
):
    if not crop_transparency and output_size is None:
        with open(path, "rb") as file:
            return base64.b64encode(file.read()).decode("utf-8")

    image = Image.open(path).convert("RGBA")

    if crop_transparency:
        alpha = image.getchannel("A")
        bbox = alpha.getbbox()

        if bbox:
            image = image.crop(bbox)

    if output_size:
        image.thumbnail(
            (output_size, output_size),
            resampling
        )

    buffer = BytesIO()
    image.save(buffer, format="PNG")

    return base64.b64encode(buffer.getvalue()).decode("utf-8")


def get_badge_img_html(pokemon_type, height=22):
    badge = TYPE_BADGE_DIR / f"{pokemon_type}.png"

    if not asset_exists(badge):
        return f"<span>{pokemon_type}</span>"

    if IS_WEB:
        badge_src = _asset_src(badge)
        return (
            f"<img "
            f"src='{badge_src}' "
            f"alt='{pokemon_type}' "
            f"class='type-badge' "
            f"style='height:{height}px;width:auto;' "
            f"/>"
        )

    encoded = image_to_base64(badge)

    return (
        f"<img "
        f"src='data:image/png;base64,{encoded}' "
        f"alt='{pokemon_type}' "
        f"class='type-badge' "
        f"style='height:{height}px;width:auto;' "
        f"/>"
    )


def slugify_pokemon_name(pokemon_name):
    return (
        pokemon_name
        .lower()
        .replace("♀", "-f")
        .replace("♂", "-m")
        .replace(".", "")
        .replace("'", "")
        .replace(" ", "-")
    )


def get_sprite_path(
    pokemon_name,
    gender=None,
    use_gmax=False,
    use_texture=True,
    sprite_dir=None,
):
    sprite_name = slugify_pokemon_name(pokemon_name)

    is_female = (
        str(gender).strip().lower() == "female"
    )

    base_dir = sprite_dir or SPRITE_DIR
    female_dir = base_dir / "female"

    candidates = []

    if use_texture:
        if is_female:
            if use_gmax:
                candidates.append(
                    female_dir / f"{sprite_name}-gmax-texture.png"
                )

            candidates.extend([
                female_dir / f"{sprite_name}-galar-texture.png",
                female_dir / f"{sprite_name}-texture.png",
            ])

        if use_gmax:
            candidates.append(
                base_dir / f"{sprite_name}-gmax-texture.png"
            )

        candidates.extend([
            base_dir / f"{sprite_name}-galar-texture.png",
            base_dir / f"{sprite_name}-texture.png",
        ])

    if is_female:
        if use_gmax:
            candidates.append(
                female_dir / f"{sprite_name}-gmax.png"
            )

        candidates.extend([
            female_dir / f"{sprite_name}-galar.png",
            female_dir / f"{sprite_name}.png",
        ])

    if use_gmax:
        candidates.append(
            base_dir / f"{sprite_name}-gmax.png"
        )

    candidates.extend([
        base_dir / f"{sprite_name}-galar.png",
        base_dir / f"{sprite_name}.png",
    ])

    for candidate in candidates:
        if asset_exists(candidate):
            return candidate

    return None

def get_sprite_src(
    pokemon_name: str,
    gender=None,
    use_gmax=False,
    use_texture=True,
    normalized=False,
) -> str | None:
    source_path = get_sprite_path(
        pokemon_name,
        gender=gender,
        use_gmax=use_gmax,
        use_texture=use_texture,
    )

    if source_path is None:
        return None

    if normalized:
        try:
            relative_path = source_path.relative_to(
                SPRITE_DIR
            )
        except ValueError:
            return _asset_src(source_path)

        normalized_path = (
            NORMALIZED_SPRITE_DIR
            / relative_path
        )

        if IS_WEB:
            return _asset_src(normalized_path)

        if normalized_path.exists():
            return _asset_src(normalized_path)

    return _asset_src(source_path)


def get_sprite_img_html(
    pokemon_name,
    size=64,
    texture_size=None,
    gender=None,
    use_gmax=False,
    use_texture=True
):

    sprite_path = get_sprite_path(
        pokemon_name,
        gender=gender,
        use_gmax=use_gmax,
        use_texture=use_texture
    )

    if sprite_path is None:
        return (
            f"<div class='sprite-placeholder' "
            f"style='width:{size}px;height:{size}px;'>?</div>"
        )

    is_texture = "-texture" in sprite_path.stem

    if is_texture:
        display_size = texture_size or size

        if IS_WEB:
            image_src = _asset_src(sprite_path)
        else:
            encoded = image_to_base64(
                sprite_path,
                crop_transparency=True,
                output_size=display_size,
                resampling=Image.Resampling.LANCZOS
            )
            image_src = f"data:image/png;base64,{encoded}"

        image_style = (
            f"width:{display_size}px;"
            f"height:{display_size}px;"
            "object-fit:contain;"
            "padding-top:0.5rem;"
            "margin-bottom:1.0rem;"
        )

    else:
        if IS_WEB:
            image_src = _asset_src(sprite_path)
        else:
            encoded = image_to_base64(sprite_path)
            image_src = f"data:image/png;base64,{encoded}"

        image_style = (
            f"max-width:{size}px;"
            f"max-height:{size}px;"
            "width:auto;"
            "height:auto;"
        )

    return (
        f"<img "
        f"src='{image_src}' "
        f"alt='{pokemon_name}' "
        f"class='pokemon-sprite' "
        f"style='{image_style}' "
        f"/>"
    )


def slugify_item_name(
    item_name: str,
) -> str:
    """Convert a held-item name into a PokéSprite filename slug."""

    normalized = (
        item_name
        .strip()
        .lower()
        .replace("’", "")
        .replace("'", "")
    )

    normalized = re.sub(
        r"[^a-z0-9]+",
        "-",
        normalized,
    )

    return normalized.strip("-")


def get_item_sprite_path(
    item_name: object,
) -> Path | None:
    """Return the bundled sprite for a held item, when available."""

    if not isinstance(item_name, str):
        return None

    item_name = item_name.strip()

    if not item_name:
        return None

    sprite_name = slugify_item_name(
        item_name
    )

    candidates = [
        HELD_ITEM_SPRITE_DIR
        / f"{sprite_name}.png",
        PLATE_SPRITE_DIR
        / f"{sprite_name}.png",
        INCENSE_SPRITE_DIR
        / f"{sprite_name}.png",
    ]

    if sprite_name.endswith("-plate"):
        candidates.append(
            PLATE_SPRITE_DIR
            / f"{sprite_name.removesuffix('-plate')}.png"
        )

    if sprite_name.endswith("-incense"):
        candidates.append(
            INCENSE_SPRITE_DIR
            / f"{sprite_name.removesuffix('-incense')}.png"
        )

    for candidate in candidates:
        if asset_exists(candidate):
            return candidate

    return None


def get_item_sprite_src(
    item_name: object,
) -> str | None:
    """Return an asset-relative item sprite source for Flet."""

    sprite_path = get_item_sprite_path(
        item_name
    )

    if sprite_path is None:
        return None

    return _asset_src(sprite_path)


def opponent_uses_gmax(opponent):
    return any(
        str(opponent.get(f"Move{slot}", "")).startswith("G-Max")
        for slot in range(1, 5)
    )