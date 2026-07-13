"""
Normalize Pokémon texture artwork.

Crops transparent padding, adds a consistent proportional margin,
centers each image on a square transparent canvas, and preserves an
external backup before overwriting any source files.
"""

from __future__ import annotations

import argparse
import os
import shutil
from pathlib import Path

from PIL import Image

from ui.constants import SPRITE_DIR as RELATIVE_SPRITE_DIR


PROJECT_ROOT = Path(__file__).resolve().parents[1]
SPRITE_DIR = (PROJECT_ROOT / RELATIVE_SPRITE_DIR).resolve()

BACKUP_ROOT = (
    PROJECT_ROOT.parent
    / f"{PROJECT_ROOT.name}_texture_backup"
)

DEFAULT_PADDING_RATIO = 0.05


def find_texture_files() -> list[Path]:
    """Return every texture artwork file beneath the sprite directory."""
    return sorted(
        path
        for path in SPRITE_DIR.rglob("*-texture.png")
        if path.is_file()
    )


def build_normalized_image(
    source_path: Path,
    padding_ratio: float,
) -> tuple[Image.Image, tuple[int, int], tuple[int, int]]:
    """
    Crop transparent padding and center the artwork on a square canvas.

    Returns the normalized image, original dimensions, and new dimensions.
    """
    with Image.open(source_path) as source_image:
        image = source_image.convert("RGBA")

    original_size = image.size

    alpha = image.getchannel("A")
    bounding_box = alpha.getbbox()

    if bounding_box is None:
        raise ValueError(
            f"{source_path} contains no visible pixels."
        )

    cropped = image.crop(bounding_box)

    content_width, content_height = cropped.size
    longest_side = max(content_width, content_height)

    padding = max(
        1,
        round(longest_side * padding_ratio),
    )

    canvas_size = longest_side + (padding * 2)

    normalized = Image.new(
        "RGBA",
        (canvas_size, canvas_size),
        (0, 0, 0, 0),
    )

    paste_x = (canvas_size - content_width) // 2
    paste_y = (canvas_size - content_height) // 2

    normalized.paste(
        cropped,
        (paste_x, paste_y),
        cropped,
    )

    return normalized, original_size, normalized.size


def backup_file(source_path: Path) -> Path:
    """Copy an original texture to the external backup directory."""
    relative_path = source_path.relative_to(SPRITE_DIR)
    backup_path = BACKUP_ROOT / relative_path

    backup_path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    if not backup_path.exists():
        shutil.copy2(
            source_path,
            backup_path,
        )

    return backup_path


def save_safely(
    image: Image.Image,
    destination: Path,
) -> None:
    """Write through a temporary file to avoid partial image writes."""
    temporary_path = destination.with_suffix(
        ".normalizing.png"
    )

    image.save(
        temporary_path,
        format="PNG",
        optimize=True,
    )

    os.replace(
        temporary_path,
        destination,
    )


def normalize_textures(
    *,
    apply_changes: bool,
    padding_ratio: float,
) -> None:
    """Inspect or normalize every texture artwork file."""
    texture_files = find_texture_files()

    if not texture_files:
        raise RuntimeError(
            f"No texture artwork was found beneath {SPRITE_DIR}."
        )

    print(
        f"Found {len(texture_files)} texture files."
    )

    if apply_changes:
        print(f"Backup location: {BACKUP_ROOT}")
    else:
        print("Dry run only. No files will be changed.")

    changed_count = 0
    failed_count = 0

    for source_path in texture_files:
        try:
            normalized, original_size, new_size = (
                build_normalized_image(
                    source_path,
                    padding_ratio,
                )
            )

            relative_path = source_path.relative_to(
                PROJECT_ROOT
            )

            if original_size == new_size:
                result_text = "same dimensions"
            else:
                result_text = (
                    f"{original_size[0]}x{original_size[1]}"
                    f" -> {new_size[0]}x{new_size[1]}"
                )

            print(
                f"{relative_path}: {result_text}"
            )

            if apply_changes:
                backup_file(source_path)
                save_safely(
                    normalized,
                    source_path,
                )

            changed_count += 1

        except Exception as error:
            failed_count += 1
            print(
                f"ERROR: {source_path}: {error}"
            )

    action = (
        "Normalized"
        if apply_changes
        else "Inspected"
    )

    print()
    print(
        f"{action} {changed_count} texture files."
    )
    print(
        f"Failures: {failed_count}"
    )


def parse_arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Normalize Pokémon texture artwork framing."
        )
    )

    parser.add_argument(
        "--apply",
        action="store_true",
        help=(
            "Back up and overwrite source textures. "
            "Without this flag, the script performs a dry run."
        ),
    )

    parser.add_argument(
        "--padding",
        type=float,
        default=DEFAULT_PADDING_RATIO,
        help=(
            "Transparent margin as a proportion of the artwork's "
            "longest side. Default: 0.05."
        ),
    )

    return parser.parse_args()


def main() -> None:
    arguments = parse_arguments()

    if not 0 <= arguments.padding <= 0.25:
        raise ValueError(
            "--padding must be between 0 and 0.25."
        )

    normalize_textures(
        apply_changes=arguments.apply,
        padding_ratio=arguments.padding,
    )


if __name__ == "__main__":
    main()