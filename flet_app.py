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

    def show_onboarding(
        *,
        show_welcome: bool = False,
    ) -> None:
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
            show_welcome=show_welcome,
        )

        page.controls.clear()
        page.add(
            onboarding_view.build()
        )
        page.update()

    def start_new_journey_from_app() -> None:
        """Open the established starter onboarding flow."""

        show_onboarding(show_welcome=False)

    def close_journey_loaded_dialog(
                event: ft.Event[ft.Button],
    ) -> None:
        """Close the successful Journey-load confirmation."""

        del event
        page.pop_dialog()
        page.update()

    def show_loaded_application() -> None:
        """
        Rebuild the application after a Journey import and confirm success.

        A Journey exported from My Team restores My Team as its active page,
        so rebuilding refreshes all views without navigating the player away.
        """

        show_main_application()

        page.show_dialog(
            ft.AlertDialog(
                modal=True,
                title=ft.Text(
                    "Journey Loaded!",
                    weight=ft.FontWeight.BOLD,
                ),
                content=ft.Text(
                    "Your saved Journey has been restored."
                ),
                actions=[
                    ft.Button(
                        content="OK",
                        icon=ft.Icons.CHECK_ROUNDED,
                        on_click=close_journey_loaded_dialog,
                    ),
                ],
                actions_alignment=ft.MainAxisAlignment.END,
            )
        )

    def show_main_application() -> None:
        """Display the normal Battle Compass application shell."""

        battle_compass_view = BattleCompassView(
            page,
            app_state=app_state,
            team_data=app_state.team_data,
            selected_starter=app_state.starter,
            on_start_new_journey=start_new_journey_from_app,
        )

        my_team_view = MyTeamView(
            page,
            app_state=app_state,
            moves_data=app_state.moves_data,
            on_team_updated=(
                battle_compass_view.refresh_team_data
            ),
            on_journey_loaded=show_loaded_application,
        )

        about_view = AboutView(
            page
        )

        def persist_active_view(
            view_name: str,
        ) -> None:
            """Schedule persistence of the newly active primary view."""

            page.run_task(
                app_state.save_active_view,
                view_name,
            )                   

        app_shell = AppShell(
            page=page,
            battle_compass_view=(
                battle_compass_view.build
            ),
            my_team_view=my_team_view.build,
            about_view=about_view.build,
            initial_view=app_state.active_view,
            on_view_changed=persist_active_view,
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
        show_onboarding(show_welcome=not app_state.has_journey)


if __name__ == "__main__":
    ft.run(
        main,
        assets_dir=str(ASSETS_DIR),
    )