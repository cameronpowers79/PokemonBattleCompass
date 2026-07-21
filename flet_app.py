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
from ui.views.about_view import AboutView
from ui.views.battle_compass_view import BattleCompassView
from ui.views.my_team_view import MyTeamView
from ui.views.onboarding_view import OnboardingView


PROJECT_ROOT = Path(__file__).resolve().parent
ASSETS_DIR = PROJECT_ROOT / "assets"


async def main(page: ft.Page) -> None:
    configure_page(page)

    page.window.icon = str(
        ASSETS_DIR / "icon_windows.ico"
    )

    reference_data = load_reference_data()

    app_state = AppState(
        page,
        reference_data=reference_data,
    )

    await app_state.initialize()

    def show_onboarding() -> None:
        """
        Display onboarding without clearing or replacing the saved Journey.

        The existing Journey remains persistent until the player completes
        starter details and clicks Prepare My Journey.
        """

        page.on_resize = None

        onboarding_view = OnboardingView(
            page,
            app_state=app_state,
            on_complete=show_main_application,
        )

        page.controls.clear()
        page.add(
            onboarding_view.build()
        )
        page.update()

    def show_main_application() -> None:
        """Display the normal Battle Compass application shell."""

        battle_compass_view = BattleCompassView(
    page,
    app_state=app_state,
    team_data=app_state.team_data,
    selected_starter=app_state.starter,
    on_start_new_journey=show_onboarding,
)

        my_team_view = MyTeamView(
            page,
            app_state=app_state,
            moves_data=app_state.moves_data,
            on_team_updated=(
                battle_compass_view.refresh_team_data
            ),
        )

        about_view = AboutView(
            page
        )

        app_shell = AppShell(
            page=page,
            battle_compass_view=(
                battle_compass_view.build
            ),
            my_team_view=my_team_view.build,
            about_view=about_view.build,
            my_team_has_unsaved_changes=(
                lambda:
                my_team_view.has_unsaved_changes
            ),
            discard_my_team_changes=(
                my_team_view.discard_unsaved_changes
            ),
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

    if app_state.is_ready:
        show_main_application()
    else:
        show_onboarding()


if __name__ == "__main__":
    ft.run(
        main,
        assets_dir=str(ASSETS_DIR),
    )
