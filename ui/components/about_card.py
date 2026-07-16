"""
Reusable documentation cards for the About page.
"""

from __future__ import annotations

from typing import cast

import flet as ft

from ui.theme import (
    BORDER_DEFAULT,
    CARD_PADDING,
    CARD_RADIUS,
    PRIMARY_BLUE,
    PRIMARY_BLUE_SOFT,
    SUCCESS,
    SURFACE,
    SURFACE_RAISED,
    TEXT_MUTED,
    TEXT_PRIMARY,
    TEXT_SECONDARY,
)


ACCENT_STYLES = {
    "blue": (PRIMARY_BLUE, PRIMARY_BLUE_SOFT),
    "green": (SUCCESS, "#173828"),
    "purple": ("#A78BFA", "#2A2140"),
    "orange": ("#F59E0B", "#3B3017"),
}


ICON_LOOKUP = {
    "waving_hand": ft.Icons.WAVING_HAND_ROUNDED,
    "explore": ft.Icons.EXPLORE_OUTLINED,
    "analytics": ft.Icons.ANALYTICS_OUTLINED,
    "save": ft.Icons.SAVE_OUTLINED,
    "target": ft.Icons.GPS_FIXED_ROUNDED,
    "account_tree": ft.Icons.ACCOUNT_TREE_OUTLINED,
    "route": ft.Icons.ROUTE_OUTLINED,
    "favorite": ft.Icons.FAVORITE_OUTLINE_ROUNDED,
    "gavel": ft.Icons.GAVEL_ROUNDED,
}


class AboutCard(ft.Container):
    """One reusable card for player-facing About-page documentation."""

    def __init__(
        self,
        *,
        title: str,
        icon: str,
        paragraphs: tuple[str, ...] = (),
        bullets: tuple[str, ...] = (),
        accent: str = "blue",
    ) -> None:
        accent_color, accent_background = ACCENT_STYLES.get(
            accent,
            ACCENT_STYLES["blue"],
        )

        super().__init__(
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
                                            ICON_LOOKUP.get(
                                                icon,
                                                ft.Icons.INFO_OUTLINE_ROUNDED,
                                            ),
                                            size=22,
                                            color=accent_color,
                                        ),
                                        width=40,
                                        height=40,
                                        alignment=ft.Alignment.CENTER,
                                        bgcolor=accent_background,
                                        border_radius=10,
                                    ),
                                    ft.Text(
                                        title,
                                        size=22,
                                        weight=ft.FontWeight.BOLD,
                                        color=TEXT_PRIMARY,
                                        expand=True,
                                    ),
                                ],
                            ),
                            spacing=12,
                            vertical_alignment=ft.CrossAxisAlignment.CENTER,
                        ),
                        *[
                            ft.Text(
                                paragraph,
                                size=15,
                                color=TEXT_SECONDARY,
                            )
                            for paragraph in paragraphs
                        ],
                        *(
                            [self._build_bullet_list(bullets)]
                            if bullets
                            else []
                        ),
                    ],
                ),
                spacing=13,
            ),
            padding=CARD_PADDING,
            bgcolor=SURFACE,
            border=ft.Border.all(1, BORDER_DEFAULT),
            border_radius=CARD_RADIUS,
        )

    @staticmethod
    def _build_bullet_list(
        bullets: tuple[str, ...],
    ) -> ft.Control:
        return ft.Column(
            controls=cast(
                list[ft.Control],
                [
                    ft.Row(
                        controls=cast(
                            list[ft.Control],
                            [
                                ft.Icon(
                                    ft.Icons.CHEVRON_RIGHT_ROUNDED,
                                    size=18,
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
                        spacing=7,
                        vertical_alignment=ft.CrossAxisAlignment.START,
                    )
                    for bullet in bullets
                ],
            ),
            spacing=8,
        )


class HeroCard(ft.Container):
    """Branded hero area for the About page."""

    def __init__(
        self,
        *,
        title: str,
        subtitle: str,
        version: str,
        tagline: str,
    ) -> None:
        super().__init__(
            content=ft.Column(
                controls=cast(
                    list[ft.Control],
                    [
                        ft.Icon(
                            ft.Icons.EXPLORE_ROUNDED,
                            size=46,
                            color=PRIMARY_BLUE,
                        ),
                        ft.Text(
                            title,
                            size=34,
                            weight=ft.FontWeight.BOLD,
                            color=TEXT_PRIMARY,
                            text_align=ft.TextAlign.CENTER,
                        ),
                        ft.Text(
                            subtitle,
                            size=18,
                            color="#D7E8FF",
                            text_align=ft.TextAlign.CENTER,
                        ),
                        ft.Container(
                            content=ft.Text(
                                version,
                                size=13,
                                weight=ft.FontWeight.BOLD,
                                color=PRIMARY_BLUE,
                            ),
                            padding=ft.Padding.symmetric(
                                horizontal=12,
                                vertical=7,
                            ),
                            bgcolor=PRIMARY_BLUE_SOFT,
                            border=ft.Border.all(1, "#445F8BC4"),
                            border_radius=999,
                        ),
                        ft.Text(
                            tagline,
                            size=15,
                            color=TEXT_MUTED,
                            italic=True,
                            text_align=ft.TextAlign.CENTER,
                        ),
                    ],
                ),
                spacing=10,
                horizontal_alignment=ft.CrossAxisAlignment.CENTER,
            ),
            padding=32,
            bgcolor=SURFACE,
            border=ft.Border.all(1, PRIMARY_BLUE),
            border_radius=CARD_RADIUS,
            shadow=ft.BoxShadow(
                blur_radius=24,
                spread_radius=1,
                color="#244F9CFF",
            ),
        )


class FooterCard(ft.Container):
    """Lightly irreverent closing card for the About page."""

    def __init__(
        self,
        *,
        title: str,
        paragraphs: tuple[str, ...],
    ) -> None:
        super().__init__(
            content=ft.Column(
                controls=cast(
                    list[ft.Control],
                    [
                        ft.Row(
                            controls=cast(
                                list[ft.Control],
                                [
                                    ft.Icon(
                                        ft.Icons.COFFEE_ROUNDED,
                                        size=23,
                                        color="#F59E0B",
                                    ),
                                    ft.Text(
                                        title,
                                        size=21,
                                        weight=ft.FontWeight.BOLD,
                                        color=TEXT_PRIMARY,
                                    ),
                                ],
                            ),
                            spacing=10,
                        ),
                        *[
                            ft.Text(
                                paragraph,
                                size=15,
                                color=TEXT_SECONDARY,
                                text_align=ft.TextAlign.CENTER,
                            )
                            for paragraph in paragraphs
                        ],
                    ],
                ),
                spacing=12,
                horizontal_alignment=ft.CrossAxisAlignment.CENTER,
            ),
            padding=26,
            bgcolor=SURFACE_RAISED,
            border=ft.Border.all(1, "#66512A"),
            border_radius=CARD_RADIUS,
        )
