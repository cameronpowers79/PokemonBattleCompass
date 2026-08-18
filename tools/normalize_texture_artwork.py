"""
Normalize Pokémon texture artwork.

Crops effectively transparent padding, adds a consistent proportional
margin, centers each image on a square transparent canvas, and preserves
an external backup before overwriting any source files.

Very low-alpha pixels can be ignored when calculating artwork bounds so
that faint shadows, antialiasing artifacts, or stray nearly-transparent
pixels do not make the visible Pokémon appear unnecessarily small.
"""

from __future__ import annotations

import argparse
import os
import shutil
import sys
from pathlib import Path

from PIL import Image


PROJECT_ROOT = Path(__file__).resolve().parents[1]

if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from ui.constants import SPRITE_DIR as RELATIVE_SPRITE_DIR


SPRITE_DIR = (PROJECT_ROOT / RELATIVE_SPRITE_DIR).resolve()

BACKUP_ROOT = (
    PROJECT_ROOT.parent
    / f"{PROJECT_ROOT.name}_texture_backup"
)

DEFAULT_PADDING_RATIO = 0.05
DEFAULT_ALPHA_THRESHOLD = 8


def find_texture_files() -> list[Path]:
    """Return every texture artwork file beneath the sprite directory."""
    return sorted(
        path
        for path in SPRITE_DIR.rglob("*-texture.png")
        if path.is_file()
    )


def build_alpha_mask(
    alpha: Image.Image,
    alpha_threshold: int,
) -> Image.Image:
    """
    Build a binary visibility mask from an alpha channel.

    Pixels whose alpha value is at least alpha_threshold count as visible.
    The mask is used only to calculate crop bounds; the original artwork
    pixels are preserved.
    """
    lookup_table = [
        255 if value >= alpha_threshold else 0
        for value in range(256)
    ]

    return alpha.point(lookup_table)


def build_normalized_image(
    source_path: Path,
    padding_ratio: float,
    alpha_threshold: int,
) -> tuple[
    Image.Image,
    tuple[int, int],
    tuple[int, int],
]:
    """
    Crop effectively transparent padding and center the artwork
    on a square canvas.

    Returns the normalized image, original dimensions, and new dimensions.
    """
    with Image.open(source_path) as source_image:
        image = source_image.convert("RGBA")

    original_size = image.size

    alpha = image.getchannel("A")

    visible_alpha = build_alpha_mask(
        alpha,
        alpha_threshold,
    )

    bounding_box = visible_alpha.getbbox()

    if bounding_box is None:
        raise ValueError(
            f"{source_path} contains no visible pixels "
            f"at alpha threshold {alpha_threshold}."
        )

    cropped = image.crop(bounding_box)

    content_width, content_height = cropped.size
    longest_side = max(
        content_width,
        content_height,
    )

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

    paste_x = (
        canvas_size - content_width
    ) // 2

    paste_y = (
        canvas_size - content_height
    ) // 2

    normalized.paste(
        cropped,
        (paste_x, paste_y),
        cropped,
    )

    return (
        normalized,
        original_size,
        normalized.size,
    )


def backup_file(
    source_path: Path,
) -> Path:
    """Copy an original texture to the external backup directory."""
    relative_path = source_path.relative_to(
        SPRITE_DIR
    )

    backup_path = (
        BACKUP_ROOT
        / relative_path
    )

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
    alpha_threshold: int,
) -> None:
    """Inspect or normalize every texture artwork file."""
    texture_files = find_texture_files()

    if not texture_files:
        raise RuntimeError(
            f"No texture artwork was found beneath "
            f"{SPRITE_DIR}."
        )

    print(
        f"Found {len(texture_files)} texture files."
    )
    print(
        f"Padding ratio: {padding_ratio:.3f}"
    )
    print(
        f"Alpha threshold: {alpha_threshold}"
    )

    if apply_changes:
        print(
            f"Backup location: {BACKUP_ROOT}"
        )
    else:
        print(
            "Dry run only. No files will be changed."
        )

    print()

    processed_count = 0
    failed_count = 0

    for source_path in texture_files:
        try:
            (
                normalized,
                original_size,
                new_size,
            ) = build_normalized_image(
                source_path,
                padding_ratio,
                alpha_threshold,
            )

            relative_path = source_path.relative_to(
                PROJECT_ROOT
            )

            if original_size == new_size:
                result_text = "same dimensions"
            else:
                result_text = (
                    f"{original_size[0]}x"
                    f"{original_size[1]}"
                    f" -> "
                    f"{new_size[0]}x"
                    f"{new_size[1]}"
                )

            print(
                f"{relative_path}: "
                f"{result_text}"
            )

            if apply_changes:
                backup_file(
                    source_path
                )

                save_safely(
                    normalized,
                    source_path,
                )

            processed_count += 1

        except Exception as error:
            failed_count += 1

            print(
                f"ERROR: "
                f"{source_path}: "
                f"{error}"
            )

    action = (
        "Normalized"
        if apply_changes
        else "Inspected"
    )

    print()
    print(
        f"{action} "
        f"{processed_count} texture files."
    )
    print(
        f"Failures: {failed_count}"
    )


def parse_arguments() -> argparse.Namespace:
    """Parse command-line arguments."""
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
            "Without this flag, the script performs "
            "a dry run."
        ),
    )

    parser.add_argument(
        "--padding",
        type=float,
        default=DEFAULT_PADDING_RATIO,
        help=(
            "Transparent margin as a proportion of "
            "the artwork's longest side. "
            "Default: 0.05."
        ),
    )

    parser.add_argument(
        "--alpha-threshold",
        type=int,
        default=DEFAULT_ALPHA_THRESHOLD,
        help=(
            "Minimum alpha value counted as visible "
            "when calculating artwork bounds. "
            "Default: 8."
        ),
    )

    return parser.parse_args()


def main() -> None:
    """Run the texture normalizer."""
    arguments = parse_arguments()

    if not 0 <= arguments.padding <= 0.25:
        raise ValueError(
            "--padding must be between "
            "0 and 0.25."
        )

    if not 1 <= arguments.alpha_threshold <= 255:
        raise ValueError(
            "--alpha-threshold must be between "
            "1 and 255."
        )

    normalize_textures(
        apply_changes=arguments.apply,
        padding_ratio=arguments.padding,
        alpha_threshold=arguments.alpha_threshold,
    )


if __name__ == "__main__":
    main()