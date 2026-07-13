from pathlib import Path

import flet as ft

from ui.rendering import get_sprite_path


PROJECT_ROOT = Path(__file__).resolve().parent
ASSETS_DIR = PROJECT_ROOT / "assets"


def resolve_project_path(file_path: str | Path) -> Path:
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


def asset_src(file_path: str | Path) -> str:
    resolved_path = resolve_project_path(file_path)

    return resolved_path.relative_to(
        ASSETS_DIR.resolve()
    ).as_posix()


def main(page: ft.Page):
    page.title = "Battle Compass Asset Test"
    page.theme_mode = ft.ThemeMode.DARK
    page.padding = 30
    page.scroll = ft.ScrollMode.AUTO
    page.horizontal_alignment = ft.CrossAxisAlignment.CENTER

    logo_path = ASSETS_DIR / "raw" / "BattleCompassLogo.png"
    wordmark_path = ASSETS_DIR / "raw" / "WordMarkLogoBlock.png"

    corviknight_sprite_path = require_asset_path(
        get_sprite_path(
            "Corviknight",
            gender=None,
            use_gmax=False,
            use_texture=False,
        ),
        "Corviknight box sprite",
    )

    corviknight_texture_path = require_asset_path(
        get_sprite_path(
            "Corviknight",
            gender=None,
            use_gmax=False,
            use_texture=True,
        ),
        "Corviknight texture artwork",
    )

    branding = ft.Column(
        controls=[
            ft.Image(
                src=asset_src(logo_path),
                width=122,
                fit=ft.BoxFit.CONTAIN,
                semantics_label="Battle Compass logo",
            ),
            ft.Image(
                src=asset_src(wordmark_path),
                width=760,
                fit=ft.BoxFit.CONTAIN,
                semantics_label="Pokémon Battle Compass wordmark",
            ),
            ft.Text(
                "Navigate every matchup with confidence.",
                size=18,
                color=ft.Colors.WHITE70,
                text_align=ft.TextAlign.CENTER,
            ),
        ],
        horizontal_alignment=ft.CrossAxisAlignment.CENTER,
        spacing=8,
    )

    asset_card = ft.Container(
        content=ft.Column(
            controls=[
                ft.Text(
                    "Local Asset Test",
                    size=24,
                    weight=ft.FontWeight.BOLD,
                ),
                ft.Row(
                    controls=[
                        ft.Image(
                            src=asset_src(corviknight_sprite_path),
                            width=96,
                            height=96,
                            fit=ft.BoxFit.CONTAIN,
                            semantics_label="Corviknight box sprite",
                        ),
                        ft.Column(
                            controls=[
                                ft.Text(
                                    "Corviknight",
                                    size=30,
                                    weight=ft.FontWeight.BOLD,
                                ),
                                ft.Text(
                                    "Box sprite",
                                    color=ft.Colors.WHITE70,
                                ),
                                ft.Text(
                                    asset_src(corviknight_sprite_path),
                                    size=12,
                                    color=ft.Colors.WHITE54,
                                ),
                            ],
                            spacing=4,
                        ),
                    ],
                    vertical_alignment=ft.CrossAxisAlignment.CENTER,
                    spacing=18,
                ),
                ft.Divider(),
                ft.Row(
                    controls=[
                        ft.Image(
                            src=asset_src(corviknight_texture_path),
                            width=180,
                            height=180,
                            fit=ft.BoxFit.CONTAIN,
                            semantics_label="Corviknight texture artwork",
                        ),
                        ft.Column(
                            controls=[
                                ft.Text(
                                    "Texture artwork",
                                    size=22,
                                    weight=ft.FontWeight.BOLD,
                                ),
                                ft.Text(
                                    asset_src(corviknight_texture_path),
                                    size=12,
                                    color=ft.Colors.WHITE54,
                                ),
                            ],
                            spacing=4,
                        ),
                    ],
                    vertical_alignment=ft.CrossAxisAlignment.CENTER,
                    spacing=18,
                ),
            ],
            spacing=16,
        ),
        width=760,
        padding=24,
        bgcolor="#151923",
        border=ft.Border.all(
            1,
            ft.Colors.BLUE_400,
        ),
        border_radius=16,
    )

    page.add(
        ft.SafeArea(
            content=ft.Column(
                controls=[
                    branding,
                    ft.Divider(),
                    asset_card,
                ],
                spacing=24,
                horizontal_alignment=ft.CrossAxisAlignment.CENTER,
            )
        )
    )


if __name__ == "__main__":
    ft.run(
        main,
        assets_dir=str(ASSETS_DIR),
    )