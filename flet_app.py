"""
Pokémon Battle Compass Flet application entry point.

Configures the shared application shell and supplies the primary views.
"""

from __future__ import annotations

from pathlib import Path
from typing import cast

import flet as ft

from ui.components.app_shell import AppShell
from ui.theme import (
    BORDER_DEFAULT,
    PRIMARY_BLUE,
    SURFACE,
    TEXT_MUTED,
    TEXT_PRIMARY,
    TEXT_SECONDARY,
    configure_page,
)
from ui.views.battle_compass_view import BattleCompassView


PROJECT_ROOT = Path(__file__).resolve().parent
ASSETS_DIR = PROJECT_ROOT / "assets"


def build_placeholder_view(
    *,
    title: str,
    description: str,
    icon: ft.IconData,
) -> ft.Control:
    controls = cast(
        list[ft.Control],
        [
            ft.Icon(
                icon,
                size=44,
                color=PRIMARY_BLUE,
            ),
            ft.Text(
                title,
                size=28,
                weight=ft.FontWeight.BOLD,
                color=TEXT_PRIMARY,
                text_align=ft.TextAlign.CENTER,
            ),
            ft.Text(
                description,
                size=16,
                color=TEXT_SECONDARY,
                text_align=ft.TextAlign.CENTER,
            ),
            ft.Text(
                "Production components will be added here next.",
                size=13,
                color=TEXT_MUTED,
                text_align=ft.TextAlign.CENTER,
            ),
        ],
    )

    return ft.Container(
        content=ft.Column(
            controls=controls,
            spacing=12,
            horizontal_alignment=ft.CrossAxisAlignment.CENTER,
        ),
        width=760,
        padding=32,
        bgcolor=SURFACE,
        border=ft.Border.all(
            1,
            BORDER_DEFAULT,
        ),
        border_radius=18,
        alignment=ft.Alignment.CENTER,
    )


def build_my_team_view() -> ft.Control:
    return build_placeholder_view(
        title="My Team",
        description=(
            "Manage Pokémon, stats, moves, abilities, "
            "and held items."
        ),
        icon=ft.Icons.GROUP_OUTLINED,
    )


def main(page: ft.Page) -> None:
    configure_page(page)

    battle_compass_view = BattleCompassView(page)

    app_shell = AppShell(
        page=page,
        battle_compass_view=battle_compass_view.build,
        my_team_view=build_my_team_view,
    )

    page.on_resize = (
        lambda event: app_shell.apply_responsive_layout(
            event.width,
        )
    )

    page.add(app_shell.build())


if __name__ == "__main__":
    ft.run(
        main,
        assets_dir=str(ASSETS_DIR),
    )