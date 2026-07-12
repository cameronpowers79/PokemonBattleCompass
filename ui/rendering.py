import base64
from io import BytesIO

from PIL import Image

from ui.constants import SPRITE_DIR, TYPE_BADGE_DIR


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


def get_sprite_path(
    pokemon_name,
    gender=None,
    use_gmax=False,
    use_texture=True
):
    sprite_name = slugify_pokemon_name(pokemon_name)

    is_female = (
        str(gender).strip().lower() == "female"
    )

    candidates = []

    if use_texture:
        if is_female:
            female_dir = SPRITE_DIR / "female"

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
                SPRITE_DIR / f"{sprite_name}-gmax-texture.png"
            )

        candidates.extend([
            SPRITE_DIR / f"{sprite_name}-galar-texture.png",
            SPRITE_DIR / f"{sprite_name}-texture.png",
        ])

    if use_gmax:
        candidates.append(
            SPRITE_DIR / f"{sprite_name}-gmax-texture.png"
        )

    candidates.extend([
        SPRITE_DIR / f"{sprite_name}-galar-texture.png",
        SPRITE_DIR / f"{sprite_name}-texture.png",
    ])

    if is_female:
        female_dir = SPRITE_DIR / "female"

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
            SPRITE_DIR / f"{sprite_name}-gmax.png"
        )

    candidates.extend([
        SPRITE_DIR / f"{sprite_name}-galar.png",
        SPRITE_DIR / f"{sprite_name}.png",
    ])

    for candidate in candidates:
        if candidate.exists():
            return candidate

    return None


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

        encoded = image_to_base64(
            sprite_path,
            crop_transparency=True,
            output_size=display_size,
            resampling=Image.Resampling.LANCZOS
        )

        image_style = (
            f"width:{display_size}px;"
            f"height:{display_size}px;"
            "object-fit:contain;"
            "padding-top:0.5rem;"
            "margin-bottom:1.0rem;"
        )

    else:
        encoded = image_to_base64(sprite_path)

        image_style = (
            f"max-width:{size}px;"
            f"max-height:{size}px;"
            "width:auto;"
            "height:auto;"
        )

    return (
        f"<img "
        f"src='data:image/png;base64,{encoded}' "
        f"alt='{pokemon_name}' "
        f"class='pokemon-sprite' "
        f"style='{image_style}' "
        f"/>"
    )


def opponent_uses_gmax(opponent):
    return any(
        str(opponent.get(f"Move{slot}", "")).startswith("G-Max")
        for slot in range(1, 5)
    )