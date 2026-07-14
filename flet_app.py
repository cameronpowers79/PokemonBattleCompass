"""
Pokémon Battle Compass Flet application entry point.

Configures application state, loads the player's Journey, and supplies
either onboarding or the primary application shell.
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
from ui.views.onboarding_view import OnboardingView


PROJECT_ROOT = Path(__file__).resolve().parent
ASSETS_DIR = PROJECT_ROOT / "assets"


async def main(page: ft.Page) -> None:
    configure_page(page)

    reference_data = load_reference_data()

    app_state = AppState(
        page,
        reference_data=reference_data,
    )

    await app_state.initialize()
    # TEMPORARY: Force onboarding during development.
    await app_state.clear_current_journey()

    def show_main_application() -> None:
        battle_compass_view = BattleCompassView(
            page,
            team_data=app_state.team_data,
            selected_starter=app_state.starter,
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
            battle_compass_view=(
                battle_compass_view.build
            ),
            my_team_view=my_team_view.build,
        )

        page.on_resize = (
            lambda event:
            app_shell.apply_responsive_layout(
                event.width,
            )
        )

        page.controls.clear()
        page.add(
            app_shell.build()
        )
        page.update()

    if not app_state.is_ready:
        onboarding_view = OnboardingView(
            page,
            app_state=app_state,
            on_complete=show_main_application,
        )

        page.add(
            onboarding_view.build()
        )
        return

    show_main_application()


if __name__ == "__main__":
    ft.run(
        main,
        assets_dir=str(ASSETS_DIR),
    )