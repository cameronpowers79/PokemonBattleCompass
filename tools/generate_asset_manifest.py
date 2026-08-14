"""
Generate the static-web asset manifest used by ui.rendering.

Run this after adding/removing relevant image assets and before publishing
the static web build:

    python tools/generate_asset_manifest.py
"""

from __future__ import annotations

from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
ASSETS_DIR = PROJECT_ROOT / "assets"
OUTPUT_PATH = PROJECT_ROOT / "ui" / "asset_manifest.py"

ASSET_ROOTS = (
    ASSETS_DIR / "type_badges",
    ASSETS_DIR / "raw" / "pokesprite" / "pokemon-gen8" / "regular",
    ASSETS_DIR / "raw" / "pokesprite" / "items" / "hold-item",
    ASSETS_DIR / "raw" / "pokesprite" / "items" / "plate",
    ASSETS_DIR / "raw" / "pokesprite" / "items" / "incense",
)


def collect_asset_paths() -> list[str]:
    """Return sorted asset-relative PNG paths needed by runtime lookups."""

    paths: set[str] = set()

    for root in ASSET_ROOTS:
        if not root.exists():
            continue

        for file_path in root.rglob("*.png"):
            paths.add(
                file_path.relative_to(ASSETS_DIR).as_posix()
            )

    return sorted(paths)


def build_manifest_source(asset_paths: list[str]) -> str:
    """Return Python source for the generated manifest module."""

    lines = [
        '"""Generated static-web asset manifest. Do not edit by hand."""',
        "",
        "BUNDLED_ASSETS = frozenset({",
    ]

    lines.extend(
        f"    {asset_path!r},"
        for asset_path in asset_paths
    )

    lines.extend([
        "})",
        "",
    ])

    return "\n".join(lines)


def main() -> None:
    asset_paths = collect_asset_paths()

    OUTPUT_PATH.write_text(
        build_manifest_source(asset_paths),
        encoding="utf-8",
    )

    print(
        f"Wrote {len(asset_paths):,} asset paths to "
        f"{OUTPUT_PATH.relative_to(PROJECT_ROOT)}"
    )


if __name__ == "__main__":
    main()