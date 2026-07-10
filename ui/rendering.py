import base64
from io import BytesIO

from PIL import Image

from ui.constants import SPRITE_DIR, TYPE_BADGE_DIR


def image_to_base64(path, crop_transparency=False, output_size=None):
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
            Image.Resampling.NEAREST
        )

    buffer = BytesIO()
    image.save(buffer, format="PNG")

    return base64.b64encode(buffer.getvalue()).decode("utf-8")


def get_badge_img_html(pokemon_type, height=22):
    badge = TYPE_BADGE_DIR / f"{pokemon_type}.png"

    if not badge.exists():
        return f"<span>{pokemon_type}</span>"

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


def get_sprite_path(pokemon_name, use_gmax=False):
    sprite_name = slugify_pokemon_name(pokemon_name)

    if use_gmax:
        gmax_path = SPRITE_DIR / f"{sprite_name}-gmax.png"

        if gmax_path.exists():
            return gmax_path

    galar_path = SPRITE_DIR / f"{sprite_name}-galar.png"

    if galar_path.exists():
        return galar_path

    sprite_path = SPRITE_DIR / f"{sprite_name}.png"

    if sprite_path.exists():
        return sprite_path

    return None


def get_sprite_img_html(pokemon_name, size=64, use_gmax=False):
    sprite_path = get_sprite_path(pokemon_name, use_gmax)

    if sprite_path is None:
        return (
            f"<div class='sprite-placeholder' "
            f"style='width:{size}px;height:{size}px;'>?</div>"
        )

    encoded = image_to_base64(sprite_path)

    return (
        f"<img "
        f"src='data:image/png;base64,{encoded}' "
        f"alt='{pokemon_name}' "
        f"class='pokemon-sprite' "
        f"style='max-width:{size}px;max-height:{size}px;' "
        f"/>"
    )


def opponent_uses_gmax(opponent):
    return any(
        str(opponent.get(f"Move{slot}", "")).startswith("G-Max")
        for slot in range(1, 5)
    )