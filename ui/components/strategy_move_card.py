"""Compact, branded move card for Strategy recommendations and planning."""
from __future__ import annotations
import flet as ft
from ui.constants import TYPE_COLORS


def strategy_move_card(move_name: str, move_type: str, badge_src: str | None,
                       *, width: int = 174) -> ft.Control:
    """Same colored move + right-aligned type badge vocabulary as opponent cards."""
    background = TYPE_COLORS.get(move_type, "#4B5563")
    controls: list[ft.Control] = [
        ft.Text(move_name, size=13, weight=ft.FontWeight.BOLD, color="#FFFFFFFF",
                max_lines=2, overflow=ft.TextOverflow.ELLIPSIS),
    ]
    if badge_src:
        controls.append(ft.Row(
            controls=[ft.Image(src=badge_src, height=15, fit=ft.BoxFit.CONTAIN,
                               semantics_label=f"{move_type} move type")],
            alignment=ft.MainAxisAlignment.END))
    return ft.Container(
        content=ft.Column(controls=controls, spacing=3, tight=True),
        width=width, height=66, padding=ft.Padding.symmetric(horizontal=10, vertical=8),
        bgcolor=background, border=ft.Border.all(1, "#40FFFFFF"), border_radius=10,
        alignment=ft.Alignment.CENTER_LEFT,
    )
