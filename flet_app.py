"""
Pokémon Battle Compass Flet application entry point.

Configures the shared application shell and supplies the primary views.
"""

from __future__ import annotations

from pathlib import Path

import flet as ft

from ui.components.app_shell import AppShell
from ui.theme import configure_page
from ui.viewmodels.battle_compass_vm import load_reference_data
from ui.views.battle_compass_view import BattleCompassView
from ui.views.my_team_view import MyTeamView


PROJECT_ROOT = Path(__file__).resolve().parent
ASSETS_DIR = PROJECT_ROOT / "assets"


def main(page: ft.Page) -> None:
    configure_page(page)

    reference_data = load_reference_data()
    shared_team_data = reference_data["team_data"]
    moves_data = reference_data["moves_data"]

    battle_compass_view = BattleCompassView(
        page,
        team_data=shared_team_data,
    )

    my_team_view = MyTeamView(
    page,
    team_data=shared_team_data,
    moves_data=moves_data,
    on_team_saved=battle_compass_view.refresh_team_data,
)

    app_shell = AppShell(
        page=page,
        battle_compass_view=battle_compass_view.build,
        my_team_view=my_team_view.build,
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