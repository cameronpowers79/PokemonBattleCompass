from pathlib import Path

import flet as ft

from ui.components.recommendation_card import (
    build_recommendation_card,
)
from ui.rendering import get_sprite_path


PROJECT_ROOT = Path(__file__).resolve().parent
ASSETS_DIR = PROJECT_ROOT / "assets"


def resolve_project_path(
    file_path: str | Path,
) -> Path:
    path = Path(file_path)

    if not path.is_absolute():
        path = PROJECT_ROOT / path

    return path.resolve()


def require_asset_path(
    file_path: str | Path | None,
    asset_name: str,
) -> Path:
    if file_path is None:
        raise FileNotFoundError(
            f"Could not locate the {asset_name} asset."
        )

    return resolve_project_path(file_path)


def asset_src(
    file_path: str | Path,
) -> str:
    resolved_path = resolve_project_path(file_path)

    return resolved_path.relative_to(
        ASSETS_DIR.resolve()
    ).as_posix()


def main(page: ft.Page):
    page.title = "Battle Compass Recommendation Card Test"
    page.theme_mode = ft.ThemeMode.DARK
    page.bgcolor = "#0B0F16"
    page.padding = 24
    page.scroll = ft.ScrollMode.AUTO

    corviknight_texture = require_asset_path(
        get_sprite_path(
            "Corviknight",
            gender=None,
            use_gmax=False,
            use_texture=True,
        ),
        "Corviknight texture",
    )

    flying_badge = (
        ASSETS_DIR
        / "raw"
        / "type-badges"
        / "Flying.png"
    )

    steel_badge = (
        ASSETS_DIR
        / "raw"
        / "type-badges"
        / "Steel.png"
    )

    recommendation_card = build_recommendation_card(
        pokemon_name="Corviknight",
        sprite_src=asset_src(corviknight_texture),
        type_badges=[
            ("Flying", asset_src(flying_badge)),
            ("Steel", asset_src(steel_badge)),
        ],
    )

    page.add(
        ft.SafeArea(
            content=ft.Column(
                controls=[
                    ft.Text(
                        "Resize the window to test the card.",
                        size=14,
                        color=ft.Colors.WHITE70,
                    ),
                    recommendation_card,
                ],
                spacing=16,
                horizontal_alignment=(
                    ft.CrossAxisAlignment.CENTER
                ),
            )
        )
    )


if __name__ == "__main__":
    ft.run(
        main,
        assets_dir=str(ASSETS_DIR),
    )