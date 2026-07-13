"""
Pokémon Battle Compass Flet application entry point.

Configures the shared application shell and supplies the initial
Battle Compass and My Team views.
"""

from __future__ import annotations

from pathlib import Path
from typing import cast

import flet as ft

from ui.components.app_shell import AppShell
from ui.components.opponent_card import OpponentCard
from ui.components.recommendation_card import RecommendationCard
from ui.rendering import get_sprite_path
from ui.theme import (
    BORDER_DEFAULT,
    PRIMARY_BLUE,
    SURFACE,
    TEXT_MUTED,
    TEXT_PRIMARY,
    TEXT_SECONDARY,
    configure_page,
)


PROJECT_ROOT = Path(__file__).resolve().parent
ASSETS_DIR = PROJECT_ROOT / "assets"


def resolve_project_path(
    file_path: str | Path,
) -> Path:
    path = Path(file_path)

    if not path.is_absolute():
        path = PROJECT_ROOT / path

    return path.resolve()


def require_asset_path(
    file_path: str | Path | None,
    asset_name: str,
) -> Path:
    if file_path is None:
        raise FileNotFoundError(
            f"Could not locate the {asset_name} asset."
        )

    return resolve_project_path(file_path)


def asset_src(
    file_path: str | Path,
) -> str:
    resolved_path = resolve_project_path(file_path)

    return resolved_path.relative_to(
        ASSETS_DIR.resolve()
    ).as_posix()


def build_battle_compass_view() -> ft.Control:
    corviknight_artwork = require_asset_path(
        get_sprite_path(
            "Corviknight",
            gender="Male",
            use_gmax=False,
            use_texture=True,
        ),
        "Corviknight artwork",
    )

    gardevoir_artwork = require_asset_path(
        get_sprite_path(
            "Gardevoir",
            gender=None,
            use_gmax=False,
            use_texture=True,
        ),
        "Gardevoir artwork",
    )

    flying_badge = (
        ASSETS_DIR
        / "type_badges"
        / "Flying.png"
    )

    steel_badge = (
        ASSETS_DIR
        / "type_badges"
        / "Steel.png"
    )

    psychic_badge = (
        ASSETS_DIR
        / "type_badges"
        / "Psychic.png"
    )

    fairy_badge = (
        ASSETS_DIR
        / "type_badges"
        / "Fairy.png"
    )

    recommendation_card = RecommendationCard(
        pokemon_name="Corviknight",
        gender_symbol="♂",
        artwork_src=asset_src(corviknight_artwork),
        type_badges=[
            (
                "Flying",
                asset_src(flying_badge),
            ),
            (
                "Steel",
                asset_src(steel_badge),
            ),
        ],
        best_move="Brave Bird",
        best_move_type_badge_src=asset_src(
            flying_badge
        ),
        effectiveness_label="Super Effective · 2×",
        effectiveness_color="#7EE2A1",
        move_score=412.98,
        item_boosted=True,
        held_item="Sharp Beak",
        item_multiplier=1.2,
        base_move_score=344.15,
        item_bonus_amount=68.83,
        matchup_label="Comfortable",
        matchup_ratio=3.42,
        matchup_level=3,
        why_text=(
            "Corviknight combines strong defensive typing with a "
            "favorable offensive matchup. Brave Bird provides the "
            "best projected result while keeping incoming damage "
            "manageable."
        ),
        battle_notes=[
            (
                "✓",
                "Corviknight is expected to survive the opponent’s "
                "strongest projected attack.",
                "success",
            ),
            (
                "⚠",
                "Brave Bird causes recoil damage.",
                "warning",
            ),
        ],
    )

    opponent_card = OpponentCard(
        pokemon_name="Gardevoir",
        artwork_src=asset_src(gardevoir_artwork),
        level=61,
        type_badges=[
            (
                "Psychic",
                asset_src(psychic_badge),
            ),
            (
                "Fairy",
                asset_src(fairy_badge),
            ),
        ],
        incoming_worst_score=110.26,
        worst_incoming_move="Future Sight",
        incoming_category="Special",
        incoming_type_badge_src=asset_src(
            psychic_badge
        ),
        defensive_effectiveness_label=(
            "🟢 Not Very Effective (0.5×)"
        ),
        defensive_effectiveness_color="#4ADE80",
        defensive_effectiveness_background="#174B35",
    )

    return ft.Column(
        controls=cast(
            list[ft.Control],
            [
                recommendation_card,
                opponent_card,
            ],
        ),
        spacing=20,
        horizontal_alignment=ft.CrossAxisAlignment.CENTER,
    )


def build_placeholder_view(
    *,
    title: str,
    description: str,
    icon: ft.IconData,
) -> ft.Control:
    controls = cast(
        list[ft.Control],
        [
            ft.Icon(
                icon,
                size=44,
                color=PRIMARY_BLUE,
            ),
            ft.Text(
                title,
                size=28,
                weight=ft.FontWeight.BOLD,
                color=TEXT_PRIMARY,
                text_align=ft.TextAlign.CENTER,
            ),
            ft.Text(
                description,
                size=16,
                color=TEXT_SECONDARY,
                text_align=ft.TextAlign.CENTER,
            ),
            ft.Text(
                "Production components will be added here next.",
                size=13,
                color=TEXT_MUTED,
                text_align=ft.TextAlign.CENTER,
            ),
        ],
    )

    return ft.Container(
        content=ft.Column(
            controls=controls,
            spacing=12,
            horizontal_alignment=ft.CrossAxisAlignment.CENTER,
        ),
        width=760,
        padding=32,
        bgcolor=SURFACE,
        border=ft.Border.all(
            1,
            BORDER_DEFAULT,
        ),
        border_radius=18,
        alignment=ft.Alignment.CENTER,
    )


def build_my_team_view() -> ft.Control:
    return build_placeholder_view(
        title="My Team",
        description=(
            "Manage Pokémon, stats, moves, abilities, "
            "and held items."
        ),
        icon=ft.Icons.GROUP_OUTLINED,
    )


def main(page: ft.Page) -> None:
    configure_page(page)

    app_shell = AppShell(
        page=page,
        battle_compass_view=build_battle_compass_view,
        my_team_view=build_my_team_view,
    )

    page.on_resize = (
        lambda event: app_shell.apply_responsive_layout(
            event.width,
        )
    )

    page.add(app_shell.build())


if __name__ == "__main__":
    ft.run(
        main,
        assets_dir=str(ASSETS_DIR),
    )