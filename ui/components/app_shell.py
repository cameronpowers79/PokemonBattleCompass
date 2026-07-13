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


class AppShell:
    """Shared Battle Compass layout and primary navigation."""

    MOBILE_BREAKPOINT = 700

    def __init__(
        self,
        page: ft.Page,
        battle_compass_view: ViewBuilder,
        my_team_view: ViewBuilder,
    ) -> None:
        self.page = page
        self.view_builders = {
            "battle_compass": battle_compass_view,
            "my_team": my_team_view,
        }
        self.active_view = "battle_compass"

        self.content_host = ft.Container(
            content=self.view_builders[self.active_view](),
            width=CONTENT_MAX_WIDTH,
            alignment=ft.Alignment.TOP_CENTER,
        )

        self.battle_compass_button = ft.Button(
            content="Battle Compass",
            icon=ft.Icons.EXPLORE_OUTLINED,
            on_click=lambda event: self.show_view("battle_compass"),
        )

        self.my_team_button = ft.Button(
            content="My Team",
            icon=ft.Icons.GROUP_OUTLINED,
            on_click=lambda event: self.show_view("my_team"),
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
                    horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                )
            ),
            width=CONTENT_MAX_WIDTH,
            padding=PAGE_PADDING_DESKTOP,
            alignment=ft.Alignment.TOP_CENTER,
        )

        self.update_navigation_style()
        self.apply_responsive_layout(self.page.width or 1000)

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

    def show_view(self, view_name: str) -> None:
        """Switch the displayed primary application view."""
        if view_name == self.active_view:
            return

        self.active_view = view_name
        self.content_host.content = self.view_builders[view_name]()
        self.update_navigation_style()
        self.page.update()

    def update_navigation_style(self) -> None:
        """Apply selected and unselected navigation styling."""
        buttons = {
            "battle_compass": self.battle_compass_button,
            "my_team": self.my_team_button,
        }

        for view_name, button in buttons.items():
            is_active = view_name == self.active_view

            button.bgcolor = PRIMARY_BLUE if is_active else SURFACE
            button.color = TEXT_PRIMARY if is_active else TEXT_SECONDARY
            button.icon_color = TEXT_PRIMARY if is_active else TEXT_MUTED

    def apply_responsive_layout(self, width: float) -> None:
        """Adjust shared spacing for narrow windows and mobile screens."""
        is_mobile = width < self.MOBILE_BREAKPOINT

        self.page_container.padding = (
            PAGE_PADDING_MOBILE
            if is_mobile
            else PAGE_PADDING_DESKTOP
        )

        self.navigation.spacing = 8 if is_mobile else 12