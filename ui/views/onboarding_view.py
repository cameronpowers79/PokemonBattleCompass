"""
Journey onboarding view.

Coordinates the welcome screen, Journey import, starter selection, starter
entry, and Journey completion. The existing Journey is not replaced until
the player confirms a valid import or finishes and validates new starter data.
"""

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path
from typing import cast

import flet as ft

from ui.components.journey_ready import JourneyReady
from ui.components.starter_details import StarterDetails
from ui.components.starter_selection import StarterSelection
from ui.storage.journey_storage import parse_journey_export
from ui.theme import (
    APP_BACKGROUND,
    CONTENT_MAX_WIDTH,
    PRIMARY_BLUE,
    SURFACE,
    SURFACE_RAISED,
    TEXT_PRIMARY,
    TEXT_SECONDARY,
    TEXT_SIZE_PAGE_TITLE,
    TEXT_SIZE_LABEL,
    TEXT_SIZE_BODY_LARGE,
    FONT_FAMILY_HEADER,
)
from ui.viewmodels.app_state import AppState


STARTER_DEFAULTS = {
    "Grookey": {
        "Type1": "Grass",
        "Ability": "Overgrow",
        "Move1": "Scratch",
        "Move2": "Growl",
    },
    "Scorbunny": {
        "Type1": "Fire",
        "Ability": "Blaze",
        "Move1": "Tackle",
        "Move2": "Growl",
    },
    "Sobble": {
        "Type1": "Water",
        "Ability": "Torrent",
        "Move1": "Pound",
        "Move2": "Growl",
    },
}


class OnboardingView:
    """Coordinate first-use welcome and Journey onboarding."""

    def __init__(
        self,
        page: ft.Page,
        *,
        app_state: AppState,
        on_complete: Callable[[], None],
        show_welcome: bool = False,
    ) -> None:
        self.page = page
        self.app_state = app_state
        self.on_complete = on_complete
        self.show_welcome = show_welcome

        self.pending_starter: str | None = None
        self.starter_details: StarterDetails | None = None
        self.pending_import_journey: dict | None = None

        self.file_picker = ft.FilePicker()
        self.page.services.append(self.file_picker)

        initial_content: ft.Control

        if show_welcome:
            initial_content = self._build_welcome_screen()
        elif (
            not app_state.has_team_member
            and app_state.starter in STARTER_DEFAULTS
        ):
            self.pending_starter = app_state.starter
            initial_content = self._build_starter_details(
                app_state.starter
            )
        else:
            initial_content = self._build_starter_selection()

        self.content_host = ft.Container(
            content=initial_content,
            width=CONTENT_MAX_WIDTH,
            alignment=ft.Alignment.TOP_CENTER,
        )

    def build(self) -> ft.Control:
        """Return the complete onboarding view."""

        return ft.Container(
            content=ft.SafeArea(
                content=ft.Column(
                    controls=cast(
                        list[ft.Control],
                        [
                            self._build_branding_header(),
                            self.content_host,
                        ],
                    ),
                    spacing=28,
                    horizontal_alignment=(
                        ft.CrossAxisAlignment.CENTER
                    ),
                ),
            ),
            expand=True,
            bgcolor=APP_BACKGROUND,
            padding=28,
            alignment=ft.Alignment.TOP_CENTER,
        )

    @staticmethod
    def _build_branding_header() -> ft.Control:
        """Build the onboarding branding header."""

        return ft.Column(
            controls=cast(
                list[ft.Control],
                [
                    ft.Image(
                        src="raw/BattleCompassLogo.png",
                        width=112,
                        fit=ft.BoxFit.CONTAIN,
                        semantics_label="Battle Compass logo",
                    ),
                    ft.Image(
                        src="raw/WordMarkLogoBlock.png",
                        width=620,
                        fit=ft.BoxFit.CONTAIN,
                        semantics_label="Pokémon Battle Compass",
                    ),
                ],
            ),
            spacing=8,
            horizontal_alignment=ft.CrossAxisAlignment.CENTER,
        )

    def _build_welcome_screen(self) -> ft.Control:
        """Offer new-Journey onboarding or portable Journey import."""

        return ft.Container(
            content=ft.Column(
                controls=cast(
                    list[ft.Control],
                    [
                        ft.Text(
                            "Welcome to Pokémon Battle Compass",
                            size=TEXT_SIZE_PAGE_TITLE,
                            weight=ft.FontWeight.BOLD,
                            font_family=FONT_FAMILY_HEADER,
                            color=TEXT_PRIMARY,
                            text_align=ft.TextAlign.CENTER,
                        ),
                        ft.Text(
                            (
                                "Start a new adventure, or restore a "
                                "Journey you previously exported."
                            ),
                            size=TEXT_SIZE_LABEL,
                            color=TEXT_SECONDARY,
                            text_align=ft.TextAlign.CENTER,
                        ),
                        ft.Row(
                            controls=cast(
                                list[ft.Control],
                                [
                                    ft.Button(
                                        content="Start a New Journey",
                                        icon=ft.Icons.EXPLORE_OUTLINED,
                                        bgcolor=PRIMARY_BLUE,
                                        color=TEXT_PRIMARY,
                                        icon_color=TEXT_PRIMARY,
                                        on_click=self._start_new_journey,
                                    ),
                                    ft.Button(
                                        content="Load a Journey",
                                        icon=ft.Icons.UPLOAD_FILE_OUTLINED,
                                        on_click=self._select_journey_file,
                                    ),
                                ],
                            ),
                            alignment=ft.MainAxisAlignment.CENTER,
                            spacing=14,
                            wrap=True,
                        ),
                    ],
                ),
                spacing=18,
                horizontal_alignment=ft.CrossAxisAlignment.CENTER,
            ),
            width=720,
            padding=28,
            bgcolor=SURFACE,
            border_radius=16,
            alignment=ft.Alignment.CENTER,
        )

    def _start_new_journey(
        self,
        event: ft.Event[ft.Button],
    ) -> None:
        """Continue from Welcome into starter selection."""

        del event
        self.show_welcome = False
        self.content_host.content = self._build_starter_selection()
        self.page.update()

    async def _select_journey_file(
        self,
        event: ft.Event[ft.Button],
    ) -> None:
        """Select and validate a portable Journey export."""

        del event

        if self.page.web:
            try:
                await ft.UrlLauncher().launch_url(
                    ft.Url(
                        url="./import.html",
                        target=ft.UrlTarget.SELF,
                    )
                )
            except (RuntimeError, ValueError) as error:
                self._show_load_error(
                    "The Journey import helper could not be opened: "
                    f"{error}"
                )
            return

        try:
            selected_files = await self.file_picker.pick_files(
                dialog_title="Load Journey",
                allow_multiple=False,
                file_type=ft.FilePickerFileType.CUSTOM,
                allowed_extensions=["json"],
                with_data=True,
            )

            if not selected_files:
                return

            selected_file = selected_files[0]

            if selected_file.bytes is not None:
                serialized_export = selected_file.bytes.decode("utf-8")
            elif selected_file.path:
                serialized_export = Path(selected_file.path).read_text(
                    encoding="utf-8"
                )
            else:
                self._show_load_error(
                    "The selected file could not be accessed."
                )
                return
        except (OSError, UnicodeError) as error:
            self._show_load_error(
                f"The selected Journey file could not be read: {error}"
            )
            return

        import_result = parse_journey_export(serialized_export)

        if (
            import_result.status != "valid"
            or import_result.journey is None
        ):
            self._show_load_error(
                import_result.error
                or "The selected Journey file is invalid."
            )
            return

        self.pending_import_journey = import_result.journey
        self._show_load_confirmation(import_result.journey)

    def _show_load_confirmation(self, journey: dict) -> None:
        """Confirm activation of the selected Journey."""

        starter = str(journey.get("starter") or "Unknown")
        team = journey.get("team")
        team_count = len(team) if isinstance(team, list) else 0

        self.page.show_dialog(
            ft.AlertDialog(
                modal=True,
                title=ft.Text(
                    "Load this Journey?",
                    weight=ft.FontWeight.BOLD,
                    color=TEXT_PRIMARY,
                ),
                content=ft.Container(
                    content=ft.Column(
                        controls=cast(
                            list[ft.Control],
                            [
                                ft.Text(
                                    (
                                        "This Journey will become the active "
                                        "Journey on this device."
                                    ),
                                    size=TEXT_SIZE_BODY_LARGE,
                                    color=TEXT_SECONDARY,
                                ),
                                ft.Container(
                                    content=ft.Column(
                                        controls=cast(
                                            list[ft.Control],
                                            [
                                                ft.Text(
                                                    f"Starter: {starter}",
                                                    weight=ft.FontWeight.BOLD,
                                                    color=TEXT_PRIMARY,
                                                ),
                                                ft.Text(
                                                    (
                                                        "Active team: "
                                                        f"{team_count} Pokémon"
                                                    ),
                                                    color=TEXT_SECONDARY,
                                                ),
                                            ],
                                        ),
                                        spacing=6,
                                        tight=True,
                                    ),
                                    padding=12,
                                    bgcolor=SURFACE_RAISED,
                                    border_radius=10,
                                ),
                            ],
                        ),
                        spacing=14,
                        tight=True,
                    ),
                    width=520,
                ),
                actions=cast(
                    list[ft.Control],
                    [
                        ft.Button(
                            content="Cancel",
                            on_click=self._cancel_journey_load,
                        ),
                        ft.Button(
                            content="Load Journey",
                            icon=ft.Icons.UPLOAD_FILE_OUTLINED,
                            bgcolor=PRIMARY_BLUE,
                            color=TEXT_PRIMARY,
                            icon_color=TEXT_PRIMARY,
                            on_click=self._confirm_journey_load,
                        ),
                    ],
                ),
                actions_alignment=ft.MainAxisAlignment.END,
            )
        )

    def _cancel_journey_load(
        self,
        event: ft.Event[ft.Button],
    ) -> None:
        """Cancel a pending Journey import."""

        del event
        self.pending_import_journey = None
        self.page.pop_dialog()
        self.page.update()

    async def _confirm_journey_load(
        self,
        event: ft.Event[ft.Button],
    ) -> None:
        """Persist the imported Journey and show success confirmation."""

        del event
        imported_journey = self.pending_import_journey

        if imported_journey is None:
            self.page.pop_dialog()
            self._show_load_error(
                "No valid Journey is waiting to be loaded."
            )
            return

        self.page.pop_dialog()

        try:
            load_succeeded = await self.app_state.import_journey(
                imported_journey
            )
        except (RuntimeError, ValueError) as error:
            self.pending_import_journey = None
            self._show_load_error(
                f"The Journey could not be loaded: {error}"
            )
            return

        self.pending_import_journey = None

        if not load_succeeded:
            self._show_load_error(
                "The Journey could not be saved."
            )
            return

        self.page.show_dialog(
            ft.AlertDialog(
                modal=True,
                title=ft.Text(
                    "Journey Loaded!",
                    weight=ft.FontWeight.BOLD,
                    color=TEXT_PRIMARY,
                ),
                content=ft.Text(
                    (
                        "Your saved Journey has been restored. Select OK "
                        "to continue from its last saved page."
                    ),
                    size=TEXT_SIZE_BODY_LARGE,
                    color=TEXT_SECONDARY,
                ),
                actions=[
                    ft.Button(
                        content="OK",
                        icon=ft.Icons.CHECK_ROUNDED,
                        bgcolor=PRIMARY_BLUE,
                        color=TEXT_PRIMARY,
                        icon_color=TEXT_PRIMARY,
                        on_click=self._finish_journey_load,
                    ),
                ],
                actions_alignment=ft.MainAxisAlignment.END,
            )
        )

    def _finish_journey_load(
        self,
        event: ft.Event[ft.Button],
    ) -> None:
        """Close load confirmation and enter the restored Journey."""

        del event
        self.page.pop_dialog()
        self.on_complete()

    def _show_load_error(self, message: str) -> None:
        """Show a non-fatal Journey import error."""

        self.page.show_dialog(
            ft.AlertDialog(
                modal=True,
                title=ft.Text(
                    "Journey could not be loaded",
                    weight=ft.FontWeight.BOLD,
                    color=TEXT_PRIMARY,
                ),
                content=ft.Text(
                    message,
                    size=TEXT_SIZE_BODY_LARGE,
                    color=TEXT_SECONDARY,
                ),
                actions=[
                    ft.Button(
                        content="OK",
                        on_click=self._close_load_error,
                    ),
                ],
                actions_alignment=ft.MainAxisAlignment.END,
            )
        )

    def _close_load_error(
        self,
        event: ft.Event[ft.Button],
    ) -> None:
        """Close a Journey-import error dialog."""

        del event
        self.page.pop_dialog()
        self.page.update()

    def _build_starter_selection(self) -> ft.Control:
        """Build the starter-selection component."""

        return StarterSelection(
            starter_defaults=STARTER_DEFAULTS,
            on_selected=self._handle_starter_selected,
        )

    def _build_starter_details(
        self,
        starter_name: str | None,
    ) -> ft.Control:
        """Build the starter-details component."""

        if (
            starter_name is None
            or starter_name not in STARTER_DEFAULTS
        ):
            return self._build_starter_selection()

        self.starter_details = StarterDetails(
            starter_name=starter_name,
            starter_defaults=STARTER_DEFAULTS[
                starter_name
            ],
            moves_data=self.app_state.moves_data,
            on_completed=self._starter_ready,
        )

        return self.starter_details

    def _handle_starter_selected(
        self,
        starter_name: str,
    ) -> None:
        """Open starter details without changing persistent Journey data."""

        if starter_name not in STARTER_DEFAULTS:
            return

        self.pending_starter = starter_name
        self.content_host.content = self._build_starter_details(
            starter_name
        )
        self.page.update()

    def _starter_ready(
        self,
        starter_record: dict,
    ) -> None:
        """Begin saving the completed replacement Journey."""

        if self.pending_starter is None:
            if self.starter_details is not None:
                self.starter_details.show_save_error(
                    "No starter is selected. "
                    "Please return to starter selection."
                )
            return

        self.page.run_task(
            self._replace_journey,
            starter_record,
        )

    async def _replace_journey(
        self,
        starter_record: dict,
    ) -> None:
        """Atomically replace the active Journey after onboarding finishes."""

        if self.pending_starter is None:
            return

        save_succeeded = await self.app_state.replace_journey(
            starter=self.pending_starter,
            team_data=[starter_record],
        )

        if not save_succeeded:
            if self.starter_details is not None:
                self.starter_details.show_save_error(
                    "Your Journey could not be saved. "
                    "Your previous Journey is still safe. "
                    "Please try again."
                )
            return

        self._show_journey_ready()

    def _show_journey_ready(self) -> None:
        """Show the final onboarding screen."""

        self.content_host.content = JourneyReady(
            on_continue=self.on_complete,
        )
        self.page.update()