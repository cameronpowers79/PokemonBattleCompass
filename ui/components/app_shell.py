from __future__ import annotations

from collections.abc import Callable

import flet as ft

from ui.theme import (
    APP_BACKGROUND,
    BORDER_DEFAULT,
    CONTENT_MAX_WIDTH,
    PAGE_PADDING_DESKTOP,
    PAGE_PADDING_MOBILE,
    PRIMARY_BLUE,
    SURFACE,
    TEXT_MUTED,
    TEXT_PRIMARY,
    TEXT_SECONDARY,
)


ViewBuilder = Callable[[], ft.Control]
DirtyStateCheck = Callable[[], bool]
DiscardChanges = Callable[[], None]


class AppShell:
    """Shared Battle Compass layout and primary navigation."""

    MOBILE_BREAKPOINT = 700

    def __init__(
        self,
        page: ft.Page,
        battle_compass_view: ViewBuilder,
        my_team_view: ViewBuilder,
        *,
        my_team_has_unsaved_changes: (
            DirtyStateCheck | None
        ) = None,
        discard_my_team_changes: (
            DiscardChanges | None
        ) = None,
    ) -> None:
        self.page = page

        self.view_builders = {
            "battle_compass": battle_compass_view,
            "my_team": my_team_view,
        }

        self.my_team_has_unsaved_changes = (
            my_team_has_unsaved_changes
        )
        self.discard_my_team_changes = (
            discard_my_team_changes
        )

        self.active_view = "battle_compass"
        self.pending_view: str | None = None

        self.content_host = ft.Container(
            content=self.view_builders[
                self.active_view
            ](),
            width=CONTENT_MAX_WIDTH,
            alignment=ft.Alignment.TOP_CENTER,
        )

        self.battle_compass_button = ft.Button(
            content="Battle Compass",
            icon=ft.Icons.EXPLORE_OUTLINED,
            on_click=(
                lambda event:
                self._request_view_change(
                    event,
                    "battle_compass",
                )
            ),
        )

        self.my_team_button = ft.Button(
            content="My Team",
            icon=ft.Icons.GROUP_OUTLINED,
            on_click=(
                lambda event:
                self._request_view_change(
                    event,
                    "my_team",
                )
            ),
        )

        self.navigation = ft.Row(
            controls=[
                self.battle_compass_button,
                self.my_team_button,
            ],
            alignment=ft.MainAxisAlignment.CENTER,
            spacing=12,
            wrap=True,
        )

        self.page_container = ft.Container(
            content=ft.SafeArea(
                content=ft.Column(
                    controls=[
                        self.build_branding_header(),
                        self.navigation,
                        ft.Divider(
                            color=BORDER_DEFAULT,
                            height=1,
                        ),
                        self.content_host,
                    ],
                    spacing=24,
                    horizontal_alignment=(
                        ft.CrossAxisAlignment.CENTER
                    ),
                )
            ),
            width=CONTENT_MAX_WIDTH,
            padding=PAGE_PADDING_DESKTOP,
            alignment=ft.Alignment.TOP_CENTER,
        )

        self.update_navigation_style()

        self.apply_responsive_layout(
            self.page.width or 1000
        )

    def build(self) -> ft.Control:
        """Return the complete application shell."""

        return ft.Container(
            content=self.page_container,
            expand=True,
            bgcolor=APP_BACKGROUND,
            alignment=ft.Alignment.TOP_CENTER,
        )

    @staticmethod
    def build_branding_header() -> ft.Control:
        """Build the shared application branding."""

        return ft.Column(
            controls=[
                ft.Image(
                    src="raw/BattleCompassLogo.png",
                    width=122,
                    fit=ft.BoxFit.CONTAIN,
                    semantics_label="Battle Compass logo",
                ),
                ft.Image(
                    src="raw/WordMarkLogoBlock.png",
                    width=760,
                    fit=ft.BoxFit.CONTAIN,
                    semantics_label="Pokémon Battle Compass",
                ),
                ft.Text(
                    "Navigate every matchup with confidence.",
                    size=17,
                    color=TEXT_SECONDARY,
                    text_align=ft.TextAlign.CENTER,
                ),
            ],
            spacing=8,
            horizontal_alignment=ft.CrossAxisAlignment.CENTER,
        )

    def _request_view_change(
        self,
        event: ft.Event[ft.Button],
        view_name: str,
    ) -> None:
        """Request navigation to another primary view."""

        del event

        if view_name == self.active_view:
            return

        leaving_dirty_team = (
            self.active_view == "my_team"
            and view_name != "my_team"
            and self.my_team_has_unsaved_changes
            is not None
            and self.my_team_has_unsaved_changes()
        )

        if not leaving_dirty_team:
            self.show_view(
                view_name
            )
            return

        self.pending_view = view_name

        self.page.show_dialog(
            self._build_unsaved_changes_dialog()
        )

    def _build_unsaved_changes_dialog(
        self,
    ) -> ft.AlertDialog:
        """Build the unsaved-team navigation warning."""

        return ft.AlertDialog(
            modal=True,
            title=ft.Text(
                "Leave without saving?",
                weight=ft.FontWeight.BOLD,
                color=TEXT_PRIMARY,
            ),
            content=ft.Text(
                (
                    "Your team has unsaved changes. "
                    "Leaving My Team now will discard them "
                    "and keep the last saved version of your "
                    "team in the Battle Compass."
                ),
                size=15,
                color=TEXT_SECONDARY,
            ),
            actions=[
                ft.Button(
                    content="Stay on My Team",
                    on_click=(
                        self._cancel_pending_navigation
                    ),
                ),
                ft.Button(
                    content="Discard Changes",
                    icon=ft.Icons.DELETE_OUTLINE_ROUNDED,
                    bgcolor=PRIMARY_BLUE,
                    color=TEXT_PRIMARY,
                    icon_color=TEXT_PRIMARY,
                    on_click=(
                        self._discard_and_continue
                    ),
                ),
            ],
            actions_alignment=ft.MainAxisAlignment.END,
        )

    def _cancel_pending_navigation(
        self,
        event: ft.Event[ft.Button],
    ) -> None:
        """Remain on My Team and preserve unsaved edits."""

        del event

        self.pending_view = None
        self.page.pop_dialog()
        self.page.update()

    def _discard_and_continue(
        self,
        event: ft.Event[ft.Button],
    ) -> None:
        """Discard unsaved team edits and continue navigation."""

        del event

        destination = self.pending_view
        self.pending_view = None

        self.page.pop_dialog()

        if self.discard_my_team_changes is not None:
            self.discard_my_team_changes()

        if destination is not None:
            self.show_view(
                destination
            )
            return

        self.page.update()

    def show_view(
        self,
        view_name: str,
    ) -> None:
        """Switch the displayed primary application view."""

        if view_name == self.active_view:
            return

        if view_name not in self.view_builders:
            raise ValueError(
                f"Unknown application view: {view_name}"
            )

        self.active_view = view_name

        self.content_host.content = (
            self.view_builders[
                view_name
            ]()
        )

        self.update_navigation_style()
        self.page.update()

    def update_navigation_style(self) -> None:
        """Apply selected and unselected navigation styling."""

        buttons = {
            "battle_compass": (
                self.battle_compass_button
            ),
            "my_team": self.my_team_button,
        }

        for view_name, button in buttons.items():
            is_active = (
                view_name == self.active_view
            )

            button.bgcolor = (
                PRIMARY_BLUE
                if is_active
                else SURFACE
            )

            button.color = (
                TEXT_PRIMARY
                if is_active
                else TEXT_SECONDARY
            )

            button.icon_color = (
                TEXT_PRIMARY
                if is_active
                else TEXT_MUTED
            )

    def apply_responsive_layout(
        self,
        width: float,
    ) -> None:
        """Adjust spacing for narrow windows and mobile screens."""

        is_mobile = (
            width < self.MOBILE_BREAKPOINT
        )

        self.page_container.padding = (
            PAGE_PADDING_MOBILE
            if is_mobile
            else PAGE_PADDING_DESKTOP
        )

        self.navigation.spacing = (
            8
            if is_mobile
            else 12
        )