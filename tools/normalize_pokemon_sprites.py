from __future__ import annotations

import shutil
from pathlib import Path

from PIL import Image

PROJECT_ROOT = Path(__file__).resolve().parents[1]

SOURCE_ROOT = (
    PROJECT_ROOT
    / "assets"
    / "raw"
    / "pokesprite"
    / "pokemon-gen8"
    / "regular"
)

OUTPUT_ROOT = (
    PROJECT_ROOT
    / "assets"
    / "runtime"
    / "pokemon-gen8"
    / "regular"
)

PADDING = 4


def normalize_sprite(
    source_path: Path,
    output_path: Path,
) -> None:
    image = Image.open(source_path).convert("RGBA")

    alpha = image.getchannel("A")
    bbox = alpha.getbbox()

    if bbox:
        image = image.crop(bbox)

    width, height = image.size

    canvas = Image.new(
        "RGBA",
        (
            width + (PADDING * 2),
            height + (PADDING * 2),
        ),
        (0, 0, 0, 0),
    )

    canvas.paste(
        image,
        (PADDING, PADDING),
        image,
    )

    output_path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )
    canvas.save(output_path)


def main() -> int:
    if not SOURCE_ROOT.is_dir():
        raise FileNotFoundError(
            f"Source sprite directory not found: {SOURCE_ROOT}"
        )

    if OUTPUT_ROOT.exists():
        shutil.rmtree(OUTPUT_ROOT)

    count = 0

    for source_path in SOURCE_ROOT.rglob("*.png"):
        relative_path = source_path.relative_to(SOURCE_ROOT)
        output_path = OUTPUT_ROOT / relative_path
        normalize_sprite(source_path, output_path)
        count += 1

    print(
        f"Normalized {count} Pokémon sprites into {OUTPUT_ROOT}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())