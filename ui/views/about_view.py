"""
About page for Pokémon Battle Compass.

Presents player-facing documentation, project history, scope, roadmap,
credits, and the legally necessary reminder that this is all extremely
unofficial.
"""

from __future__ import annotations

from typing import cast

import flet as ft

from ui.components.about_card import (
    AboutCard,
    FooterCard,
    HeroCard,
)
from data.about_content import (
    ABOUT_SECTIONS,
    FOOTER_PARAGRAPHS,
    FOOTER_TITLE,
    HERO_SUBTITLE,
    HERO_TAGLINE,
    HERO_TITLE,
    HERO_VERSION,
    NERD_STUFF_GROUPS,
    NERD_STUFF_INTRO,
    VERSION_HISTORY,
)
from ui.theme import (
    BORDER_DEFAULT,
    CONTENT_MAX_WIDTH,
    PRIMARY_BLUE,
    PRIMARY_BLUE_SOFT,
    SURFACE,
    SURFACE_RAISED,
    TEXT_MUTED,
    TEXT_PRIMARY,
    TEXT_SECONDARY,
)


class AboutView:
    """Card-based in-app documentation page."""

    def __init__(
        self,
        page: ft.Page,
    ) -> None:
        self.page = page
        self.nerd_stuff_host = ft.Container(
            visible=False,
        )
        self.nerd_stuff_expanded = False
        self.nerd_stuff_button = ft.Button(
            content="Show Nerd Stuff",
            icon=ft.Icons.EXPAND_MORE_ROUNDED,
            on_click=self._toggle_nerd_stuff,
            style=ft.ButtonStyle(
                bgcolor=PRIMARY_BLUE_SOFT,
                color=TEXT_PRIMARY,
                icon_color=PRIMARY_BLUE,
                elevation=0,
            ),
        )

        self._refresh_nerd_stuff()

    def build(self) -> ft.Control:
        """Return the complete About page."""

        section_cards = cast(
            list[ft.Control],
            [
                AboutCard(
                    title=section.title,
                    icon=section.icon,
                    paragraphs=section.paragraphs,
                    bullets=section.bullets,
                    accent=section.accent,
                )
                for section in ABOUT_SECTIONS
            ],
        )

        welcome_and_features = section_cards[:5]
        architecture_and_roadmap = section_cards[5:7]
        credits_and_disclaimer = section_cards[7:]

        return ft.Container(
            content=ft.Column(
                controls=cast(
                    list[ft.Control],
                    [
                        HeroCard(
                            title=HERO_TITLE,
                            subtitle=HERO_SUBTITLE,
                            version=HERO_VERSION,
                            tagline=HERO_TAGLINE,
                        ),
                        *welcome_and_features,
                        self._build_nerd_stuff_card(),
                        *architecture_and_roadmap,
                        self._build_version_history(),
                        *credits_and_disclaimer,
                        FooterCard(
                            title=FOOTER_TITLE,
                            paragraphs=FOOTER_PARAGRAPHS,
                        ),
                    ],
                ),
                spacing=20,
                horizontal_alignment=ft.CrossAxisAlignment.STRETCH,
            ),
            width=CONTENT_MAX_WIDTH,
            alignment=ft.Alignment.TOP_CENTER,
        )

    def _build_nerd_stuff_card(self) -> ft.Control:
        """Build the collapsible technical-details section."""

        return ft.Container(
            content=ft.Column(
                controls=cast(
                    list[ft.Control],
                    [
                        ft.ResponsiveRow(
                            controls=cast(
                                list[ft.Control],
                                [
                                    ft.Container(
                                        content=ft.Row(
                                            controls=cast(
                                                list[ft.Control],
                                                [
                                                    ft.Container(
                                                        content=ft.Icon(
                                                            ft.Icons.MEMORY_ROUNDED,
                                                            size=22,
                                                            color="#A78BFA",
                                                        ),
                                                        width=40,
                                                        height=40,
                                                        alignment=ft.Alignment.CENTER,
                                                        bgcolor="#2A2140",
                                                        border_radius=10,
                                                    ),
                                                    ft.Column(
                                                        controls=cast(
                                                            list[ft.Control],
                                                            [
                                                                ft.Text(
                                                                    "Nerd Stuff (Optional)",
                                                                    size=22,
                                                                    weight=ft.FontWeight.BOLD,
                                                                    color=TEXT_PRIMARY,
                                                                ),
                                                                ft.Text(
                                                                    (
                                                                        "The engine details, "
                                                                        "minus several thousand "
                                                                        "lines of code."
                                                                    ),
                                                                    size=13,
                                                                    color=TEXT_MUTED,
                                                                ),
                                                            ],
                                                        ),
                                                        spacing=2,
                                                    ),
                                                ],
                                            ),
                                            spacing=12,
                                            vertical_alignment=(
                                                ft.CrossAxisAlignment.CENTER
                                            ),
                                        ),
                                        col={
                                            "xs": 12,
                                            "sm": 8,
                                        },
                                    ),
                                    ft.Container(
                                        content=self.nerd_stuff_button,
                                        col={
                                            "xs": 12,
                                            "sm": 4,
                                        },
                                        alignment=ft.Alignment.CENTER_RIGHT,
                                    ),
                                ],
                            ),
                            columns=12,
                            spacing=12,
                            run_spacing=10,
                            vertical_alignment=ft.CrossAxisAlignment.CENTER,
                        ),
                        self.nerd_stuff_host,
                    ],
                ),
                spacing=14,
            ),
            padding=20,
            bgcolor=SURFACE,
            border=ft.Border.all(1, BORDER_DEFAULT),
            border_radius=16,
        )

    def _refresh_nerd_stuff(self) -> None:
        """Refresh the collapsible Nerd Stuff content."""

        self.nerd_stuff_button.content = (
            "Hide Nerd Stuff"
            if self.nerd_stuff_expanded
            else "Show Nerd Stuff"
        )
        self.nerd_stuff_button.icon = (
            ft.Icons.EXPAND_LESS_ROUNDED
            if self.nerd_stuff_expanded
            else ft.Icons.EXPAND_MORE_ROUNDED
        )

        if not self.nerd_stuff_expanded:
            self.nerd_stuff_host.content = None
            self.nerd_stuff_host.visible = False
            return

        group_cards = cast(
            list[ft.Control],
            [
                ft.Container(
                    content=ft.Column(
                        controls=cast(
                            list[ft.Control],
                            [
                                ft.Text(
                                    group_title,
                                    size=17,
                                    weight=ft.FontWeight.BOLD,
                                    color=TEXT_PRIMARY,
                                ),
                                *[
                                    ft.Row(
                                        controls=cast(
                                            list[ft.Control],
                                            [
                                                ft.Icon(
                                                    ft.Icons.SCIENCE_OUTLINED,
                                                    size=16,
                                                    color=PRIMARY_BLUE,
                                                ),
                                                ft.Text(
                                                    bullet,
                                                    size=14,
                                                    color=TEXT_SECONDARY,
                                                    expand=True,
                                                ),
                                            ],
                                        ),
                                        spacing=8,
                                        vertical_alignment=(
                                            ft.CrossAxisAlignment.START
                                        ),
                                    )
                                    for bullet in bullets
                                ],
                            ],
                        ),
                        spacing=8,
                    ),
                    col={"xs": 12, "md": 6},
                    padding=15,
                    bgcolor=SURFACE_RAISED,
                    border_radius=12,
                )
                for group_title, bullets in NERD_STUFF_GROUPS
            ],
        )

        self.nerd_stuff_host.visible = True

        self.nerd_stuff_host.content = ft.Column(
            controls=cast(
                list[ft.Control],
                [
                    ft.Text(
                        NERD_STUFF_INTRO,
                        size=14,
                        color=TEXT_SECONDARY,
                    ),
                    ft.ResponsiveRow(
                        controls=group_cards,
                        columns=12,
                        spacing=12,
                        run_spacing=12,
                    ),
                ],
            ),
            spacing=13,
        )

    def _toggle_nerd_stuff(
        self,
        event: ft.Event[ft.Button],
    ) -> None:
        """Expand or collapse the optional technical details."""

        del event

        self.nerd_stuff_expanded = not self.nerd_stuff_expanded
        self._refresh_nerd_stuff()
        self.page.update()

    @staticmethod
    def _build_version_history() -> ft.Control:
        """Build the migration and release-history card."""

        version_controls = cast(list[ft.Control], [])

        for index, version in enumerate(VERSION_HISTORY):
            if index:
                version_controls.append(
                    ft.Divider(
                        color=BORDER_DEFAULT,
                        height=1,
                    )
                )

            version_controls.append(
                ft.Column(
                    controls=cast(
                        list[ft.Control],
                        [
                            ft.Row(
                                controls=cast(
                                    list[ft.Control],
                                    [
                                        ft.Text(
                                            version.name,
                                            size=18,
                                            weight=ft.FontWeight.BOLD,
                                            color=TEXT_PRIMARY,
                                        ),
                                        ft.Container(
                                            content=ft.Text(
                                                version.status,
                                                size=12,
                                                weight=ft.FontWeight.BOLD,
                                                color=PRIMARY_BLUE,
                                            ),
                                            padding=ft.Padding.symmetric(
                                                horizontal=9,
                                                vertical=5,
                                            ),
                                            bgcolor=PRIMARY_BLUE_SOFT,
                                            border_radius=999,
                                        ),
                                    ],
                                ),
                                spacing=9,
                                wrap=True,
                            ),
                            ft.Text(
                                version.summary,
                                size=14,
                                color=TEXT_SECONDARY,
                            ),
                            *[
                                ft.Row(
                                    controls=cast(
                                        list[ft.Control],
                                        [
                                            ft.Icon(
                                                ft.Icons.HISTORY_ROUNDED,
                                                size=16,
                                                color=PRIMARY_BLUE,
                                            ),
                                            ft.Text(
                                                bullet,
                                                size=13,
                                                color=TEXT_SECONDARY,
                                                expand=True,
                                            ),
                                        ],
                                    ),
                                    spacing=8,
                                    vertical_alignment=(
                                        ft.CrossAxisAlignment.START
                                    ),
                                )
                                for bullet in version.bullets
                            ],
                        ],
                    ),
                    spacing=8,
                )
            )

        return ft.Container(
            content=ft.Column(
                controls=cast(
                    list[ft.Control],
                    [
                        ft.Row(
                            controls=cast(
                                list[ft.Control],
                                [
                                    ft.Container(
                                        content=ft.Icon(
                                            ft.Icons.HISTORY_ROUNDED,
                                            size=22,
                                            color=PRIMARY_BLUE,
                                        ),
                                        width=40,
                                        height=40,
                                        alignment=ft.Alignment.CENTER,
                                        bgcolor=PRIMARY_BLUE_SOFT,
                                        border_radius=10,
                                    ),
                                    ft.Text(
                                        "Version History",
                                        size=22,
                                        weight=ft.FontWeight.BOLD,
                                        color=TEXT_PRIMARY,
                                    ),
                                ],
                            ),
                            spacing=12,
                        ),
                        *version_controls,
                    ],
                ),
                spacing=14,
            ),
            padding=20,
            bgcolor=SURFACE,
            border=ft.Border.all(1, BORDER_DEFAULT),
            border_radius=16,
        )
