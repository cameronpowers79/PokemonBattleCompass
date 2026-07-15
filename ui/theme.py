from __future__ import annotations

import flet as ft


# ---------------------------------------------------------------------------
# Core palette
# ---------------------------------------------------------------------------

APP_BACKGROUND = "#0B0F16"
SURFACE = "#121722"
SURFACE_RAISED = "#151B27"
SURFACE_MUTED = "#10141C"

PRIMARY_BLUE = "#4F9CFF"
PRIMARY_BLUE_LIGHT = "#69A8FF"
PRIMARY_BLUE_SOFT = "#182A43"

TEXT_PRIMARY = "#F4F7FB"
TEXT_SECONDARY = "#AEB8C7"
TEXT_MUTED = "#7F8998"

BORDER_DEFAULT = "#24FFFFFF"
BORDER_ACCENT = "#734F9CFF"

SUCCESS = "#4ADE80"
SUCCESS_SOFT = "#459764"
WARNING = "#FBBF24"
DANGER = "#F87171"
INFO = "#60A5FA"


# ---------------------------------------------------------------------------
# Shared dimensions
# ---------------------------------------------------------------------------

PAGE_PADDING_DESKTOP = 28
PAGE_PADDING_MOBILE = 16

CONTENT_MAX_WIDTH = 1280

CARD_RADIUS = 18
PANEL_RADIUS = 12

CARD_PADDING = 28
PANEL_PADDING = 16


def build_dark_theme() -> ft.Theme:
    """
    Return the application-wide dark theme.

    Individual Battle Compass components may still override colors where
    the branded design requires more precision.
    """
    return ft.Theme(
        color_scheme_seed=PRIMARY_BLUE,
    )


def configure_page(page: ft.Page) -> None:
    """
    Apply shared application settings to a Flet page.
    """
    page.title = "Pokémon Battle Compass"
    page.theme_mode = ft.ThemeMode.DARK
    page.dark_theme = build_dark_theme()

    page.bgcolor = APP_BACKGROUND
    page.padding = 0
    page.spacing = 0
    page.scroll = ft.ScrollMode.AUTO

    page.horizontal_alignment = ft.CrossAxisAlignment.CENTER