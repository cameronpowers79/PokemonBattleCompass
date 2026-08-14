from __future__ import annotations

from pathlib import Path

from PIL import Image


PROJECT_ROOT = Path(__file__).resolve().parents[1]

SOURCE_LOGO = (
    PROJECT_ROOT
    / "assets"
    / "raw"
    / "BattleCompassLogo.png"
)

WEB_BRANDING_DIR = (
    PROJECT_ROOT
    / "assets"
    / "web_branding"
)

ICONS_DIR = WEB_BRANDING_DIR / "icons"

BACKGROUND = (11, 17, 27, 255)

ICON_SPECS = {
    "apple-touch-icon-192.png": (192, 0.84),
    "icon-192.png": (192, 0.86),
    "icon-512.png": (512, 0.86),
    "icon-maskable-192.png": (192, 0.66),
    "icon-maskable-512.png": (512, 0.66),
    "loading-animation.png": (512, 0.72),
}

FAVICON_SIZE = 256
FAVICON_LOGO_FRACTION = 0.76


def build_icon(
    source: Image.Image,
    size: int,
    logo_fraction: float,
) -> Image.Image:
    canvas = Image.new(
        "RGBA",
        (size, size),
        BACKGROUND,
    )

    logo = source.copy()
    max_logo_size = int(size * logo_fraction)

    logo.thumbnail(
        (
            max_logo_size,
            max_logo_size,
        ),
        Image.Resampling.LANCZOS,
    )

    x = (size - logo.width) // 2
    y = (size - logo.height) // 2

    canvas.alpha_composite(
        logo,
        (x, y),
    )

    return canvas


def main() -> int:
    if not SOURCE_LOGO.is_file():
        raise FileNotFoundError(
            f"Branding source logo not found: {SOURCE_LOGO}"
        )

    ICONS_DIR.mkdir(
        parents=True,
        exist_ok=True,
    )
    WEB_BRANDING_DIR.mkdir(
        parents=True,
        exist_ok=True,
    )

    with Image.open(SOURCE_LOGO) as source_file:
        source = source_file.convert("RGBA")

        for filename, (
            size,
            logo_fraction,
        ) in ICON_SPECS.items():
            output_path = ICONS_DIR / filename

            build_icon(
                source,
                size,
                logo_fraction,
            ).save(output_path)

            print(
                f"  + web branding: "
                f"{output_path.relative_to(PROJECT_ROOT)}"
            )

        favicon_path = (
            WEB_BRANDING_DIR
            / "favicon.png"
        )

        build_icon(
            source,
            FAVICON_SIZE,
            FAVICON_LOGO_FRACTION,
        ).save(favicon_path)

        print(
            f"  + web branding: "
            f"{favicon_path.relative_to(PROJECT_ROOT)}"
        )

    return 0


if __name__ == "__main__":
    raise SystemExit(main())