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
from ui.views.my_journey_view import MyJourneyView
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
        page.scroll = ft.ScrollMode.AUTO

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

        journey_loaded_dialog = ft.AlertDialog()
        journey_loaded_dialog.modal = True
        journey_loaded_dialog.title = ft.Text(
            "Journey Loaded!",
            weight=ft.FontWeight.BOLD,
        )
        journey_loaded_dialog.content = ft.Text(
            "Your saved Journey has been restored."
        )
        journey_loaded_dialog.actions = [
            ft.Button(
                content="OK",
                icon=ft.Icons.CHECK_ROUNDED,
                on_click=close_journey_loaded_dialog,
            ),
        ]
        journey_loaded_dialog.actions_alignment = ft.MainAxisAlignment.END

        page.show_dialog(journey_loaded_dialog)

    def show_main_application() -> None:
        """Display the normal Battle Compass application shell."""

        # AppShell owns scrolling so its on_scroll handler can drive the
        # threshold-based Return to Top control.
        page.scroll = None

        battle_compass_view = BattleCompassView(
            page,
            app_state=app_state,
            team_data=app_state.team_data,
            selected_starter=app_state.starter,
            on_start_new_journey=start_new_journey_from_app,
        )

        app_shell: AppShell

        def go_to_my_team_with_prefill(
            pokemon_name: str,
        ) -> None:
            my_team_view.begin_prefilled_pokemon_entry(
                pokemon_name
            )
            app_shell.show_view("my_team")

        async def scroll_app_shell(
            **scroll_kwargs,
        ) -> None:
            await app_shell.scroll_to(**scroll_kwargs)

        my_journey_view = MyJourneyView(
            page,
            app_state=app_state,
            on_go_to_my_team=go_to_my_team_with_prefill,
            on_scroll_to=scroll_app_shell,
        )

        def refresh_after_team_update(
            team_data: list[dict],
        ) -> None:
            battle_compass_view.refresh_team_data(team_data)
            my_journey_view.refresh_from_app_state()

        my_team_view = MyTeamView(
            page,
            app_state=app_state,
            moves_data=app_state.moves_data,
            on_team_updated=refresh_after_team_update,
            on_journey_loaded=show_loaded_application,
            on_journey_updated=(
                my_journey_view.refresh_from_app_state
            ),
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
            my_journey_view=my_journey_view.build,
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