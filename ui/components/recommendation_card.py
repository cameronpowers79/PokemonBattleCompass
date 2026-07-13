from __future__ import annotations

import flet as ft


CARD_BACKGROUND = "#121722"
CARD_BORDER = "#4F9CFF"
TEXT_PRIMARY = "#F4F7FB"
TEXT_SECONDARY = "#AEB8C7"
BLUE_PANEL = "#182A43"
GREEN_PANEL = "#173828"
AMBER_PANEL = "#3B3017"


def _type_badge(
    badge_src: str,
    pokemon_type: str,
) -> ft.Image:
    return ft.Image(
        src=badge_src,
        height=24,
        fit=ft.BoxFit.CONTAIN,
        semantics_label=f"{pokemon_type} type",
    )


def _matchup_segment(
    color: str,
    active: bool = False,
) -> ft.Container:
    return ft.Container(
        height=14,
        expand=True,
        bgcolor=color,
        opacity=1.0 if active else 0.35,
        border=ft.Border.all(
            1,
            "#55FFFFFF" if active else "#22FFFFFF",
        ),
        border_radius=4,
    )


def build_matchup_meter() -> ft.Control:
    return ft.Column(
        controls=[
            ft.Text(
                "Matchup Strength",
                size=14,
                color=TEXT_SECONDARY,
            ),
            ft.Row(
                controls=[
                    _matchup_segment("#C13D3D"),
                    _matchup_segment("#D87931"),
                    _matchup_segment("#B9C936"),
                    _matchup_segment("#37B866", active=True),
                    _matchup_segment("#3D83D9"),
                ],
                spacing=4,
            ),
            ft.Text(
                "Comfortable",
                size=20,
                weight=ft.FontWeight.BOLD,
                color="#4ADE80",
            ),
            ft.Text(
                "Ratio 3.42",
                size=13,
                color=TEXT_SECONDARY,
            ),
        ],
        spacing=7,
    )


def build_recommendation_card(
    *,
    pokemon_name: str,
    sprite_src: str,
    type_badges: list[tuple[str, str]],
) -> ft.Container:
    badge_row = ft.Row(
        controls=[
            _type_badge(badge_src, pokemon_type)
            for pokemon_type, badge_src in type_badges
        ],
        spacing=8,
        wrap=True,
    )

    pokemon_header = ft.ResponsiveRow(
        controls=[
            ft.Container(
                content=ft.Image(
                    src=sprite_src,
                    width=150,
                    height=150,
                    fit=ft.BoxFit.CONTAIN,
                    semantics_label=pokemon_name,
                ),
                alignment=ft.Alignment.CENTER,
                col={
                    ft.ResponsiveRowBreakpoint.XS: 12,
                    ft.ResponsiveRowBreakpoint.SM: 4,
                },
            ),
            ft.Container(
                content=ft.Column(
                    controls=[
                        ft.Text(
                            pokemon_name,
                            size=42,
                            weight=ft.FontWeight.BOLD,
                            color=TEXT_PRIMARY,
                        ),
                        badge_row,
                    ],
                    spacing=12,
                    horizontal_alignment=(
                        ft.CrossAxisAlignment.START
                    ),
                ),
                alignment=ft.Alignment.CENTER_LEFT,
                col={
                    ft.ResponsiveRowBreakpoint.XS: 12,
                    ft.ResponsiveRowBreakpoint.SM: 8,
                },
            ),
        ],
        spacing=16,
        run_spacing=12,
        vertical_alignment=ft.CrossAxisAlignment.CENTER,
    )

    move_panel = ft.Container(
        content=ft.Column(
            controls=[
                ft.Text(
                    "Best Move",
                    size=14,
                    color=TEXT_SECONDARY,
                ),
                ft.Text(
                    "Brave Bird",
                    size=34,
                    weight=ft.FontWeight.BOLD,
                    color=TEXT_PRIMARY,
                ),
                ft.Container(
                    content=ft.Text(
                        "🟢 Super Effective (2×)",
                        size=15,
                        weight=ft.FontWeight.BOLD,
                        color="#7EE2A1",
                    ),
                    padding=ft.Padding.symmetric(
                        horizontal=14,
                        vertical=10,
                    ),
                    bgcolor=GREEN_PANEL,
                    border_radius=10,
                ),
            ],
            spacing=10,
        ),
        col={
            ft.ResponsiveRowBreakpoint.XS: 12,
            ft.ResponsiveRowBreakpoint.MD: 7,
        },
    )

    matchup_panel = ft.Container(
        content=build_matchup_meter(),
        col={
            ft.ResponsiveRowBreakpoint.XS: 12,
            ft.ResponsiveRowBreakpoint.MD: 5,
        },
    )

    why_panel = ft.Container(
        content=ft.Column(
            controls=[
                ft.Text(
                    "Why this Pokémon?",
                    size=20,
                    weight=ft.FontWeight.BOLD,
                    color=TEXT_PRIMARY,
                ),
                ft.Text(
                    "Corviknight combines strong defensive typing "
                    "with a favorable offensive matchup. Brave Bird "
                    "provides the best projected result while keeping "
                    "incoming damage manageable.",
                    size=15,
                    color="#D7E8FF",
                ),
                ft.Text(
                    "ℹ Compare the entire team in Full Analysis.",
                    size=14,
                    weight=ft.FontWeight.BOLD,
                    color="#69A8FF",
                ),
            ],
            spacing=9,
        ),
        padding=16,
        bgcolor=BLUE_PANEL,
        border=ft.Border.all(1, "#445F8BC4"),
        border_radius=12,
    )

    battle_notes = ft.Column(
        controls=[
            ft.Text(
                "Battle Notes",
                size=20,
                weight=ft.FontWeight.BOLD,
                color=TEXT_PRIMARY,
            ),
            ft.Container(
                content=ft.Text(
                    "✅ Corviknight is expected to survive the "
                    "opponent’s strongest projected attack.",
                    size=15,
                    color="#C9F7D7",
                ),
                padding=12,
                bgcolor=GREEN_PANEL,
                border_radius=10,
            ),
            ft.Container(
                content=ft.Text(
                    "⚠ Brave Bird causes recoil damage.",
                    size=15,
                    color="#FFE5A3",
                ),
                padding=12,
                bgcolor=AMBER_PANEL,
                border_radius=10,
            ),
        ],
        spacing=9,
    )

    return ft.Container(
        content=ft.Column(
            controls=[
                ft.Text(
                    "⭐ Recommended Pokémon",
                    size=24,
                    weight=ft.FontWeight.BOLD,
                    color=TEXT_PRIMARY,
                ),
                pokemon_header,
                ft.Divider(color="#28FFFFFF"),
                ft.ResponsiveRow(
                    controls=[
                        move_panel,
                        matchup_panel,
                    ],
                    spacing=28,
                    run_spacing=20,
                ),
                why_panel,
                battle_notes,
            ],
            spacing=22,
        ),
        width=900,
        padding=28,
        bgcolor=CARD_BACKGROUND,
        border=ft.Border.all(1, CARD_BORDER),
        border_radius=18,
    )