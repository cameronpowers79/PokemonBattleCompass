"""
Pokémon Battle Compass Flet application entry point.

Configures application state, loads the player's Journey, and supplies
the primary views.
"""

from __future__ import annotations

from pathlib import Path

import flet as ft

from ui.components.app_shell import AppShell
from ui.theme import configure_page
from ui.viewmodels.app_state import AppState
from ui.viewmodels.battle_compass_vm import load_reference_data
from ui.views.battle_compass_view import BattleCompassView
from ui.views.my_team_view import MyTeamView


PROJECT_ROOT = Path(__file__).resolve().parent
ASSETS_DIR = PROJECT_ROOT / "assets"

TEMPORARY_EXAMPLE_STARTER = "Grookey"


async def main(page: ft.Page) -> None:
    configure_page(page)

    reference_data = load_reference_data()

    app_state = AppState(
        page,
        reference_data=reference_data,
    )

    await app_state.initialize()

    if not app_state.has_journey:
        if app_state.load_error:
            print(
                "Unable to load the saved Journey: "
                f"{app_state.load_error}"
            )
            print(
                "Using the bundled example team for this session."
            )

        app_state.use_example_journey(
            starter=TEMPORARY_EXAMPLE_STARTER,
            team_data=reference_data["team_data"],
        )

    battle_compass_view = BattleCompassView(
        page,
        team_data=app_state.team_data,
    )

    my_team_view = MyTeamView(
        page,
        app_state=app_state,
        moves_data=app_state.moves_data,
        on_team_updated=(
            battle_compass_view.refresh_team_data
        ),
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