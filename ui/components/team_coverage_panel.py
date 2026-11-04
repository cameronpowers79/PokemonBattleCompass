"""Reusable 18-type planned coverage presentation (no ranking implications)."""
from __future__ import annotations
from pathlib import Path
from typing import Any
import flet as ft

_BADGE_ROOT = Path(__file__).resolve().parents[2] / 'assets' / 'type_badges'


def _fmt(value: float | None) -> str:
    if value is None:
        return '—'
    return f'×{value:.2f}'.rstrip('0').rstrip('.') if value else 'IMMUNE'


def _details(page: ft.Page, kind: str, attack_type: str, entry: dict[str, Any]) -> None:
    rows: list[ft.Control] = []
    if kind == 'defensive':
        for item in entry.get('members', []):
            source = f" · {item['ability']} immunity" if item.get('immunity_source') == 'ability' else ''
            rows.append(ft.Text(f"{item['pokemon']}: {_fmt(item['multiplier'])}{source}", size=13))
        if not rows:
            rows.append(ft.Text('Add a Pokémon to see defensive coverage.'))
    else:
        for item in entry.get('contributors', []):
            rows.append(ft.Text(f"{item['pokemon']}: {item['move']} ({item['move_type']}) · {_fmt(item['multiplier'])}", size=13))
        if not rows:
            rows.append(ft.Text('No planned move is super effective against this type.', size=13))
    page.show_dialog(ft.AlertDialog(
        title=ft.Text(f'{attack_type} · {kind.title()} coverage'),
        content=ft.Container(width=420,content=ft.Column(controls=rows,spacing=8,
                          tight=True,scroll=ft.ScrollMode.AUTO)),
        actions=[ft.Button(content='Close',on_click=lambda e: page.pop_dialog())]))


def _tile(page: ft.Page, kind: str, attack_type: str, entry: dict[str, Any]) -> ft.Control:
    if kind == 'defensive':
        value = entry.get('average')
        immune = bool(entry.get('has_immunity'))
        good = value is not None and value < 1
        bad = value is not None and value > 1
    else:
        value = entry.get('best_multiplier')
        immune = False
        good = bool(entry.get('covered'))
        bad = False
    # Dim the art only for annotated tiles; overlay compact, high-contrast
    # values on the center without competing with the built-in type label.
    # Immunity is independent of the team's arithmetic average and border risk.
    annotated = immune or good or bad
    icon = '★' if immune else ('!' if bad else ('✓' if good else ''))
    icon_color = '#F6C851' if immune else ('#FF626B' if bad else '#4BE18B')
    show_value = value is not None and (
        (kind == 'defensive' and abs(value - 1) > 0.001) or good)
    value_label = _fmt(value) if show_value else ''
    badge_path = _BADGE_ROOT / f'{attack_type}.png'
    badge = (
        ft.Image(src=f'type_badges/{attack_type}.png', width=110, height=28,
                 fit=ft.BoxFit.FILL, semantics_label=f'{attack_type} type')
        if badge_path.exists() else
        ft.Container(width=110,height=28,bgcolor='#36465E',
                     content=ft.Text(attack_type,size=11,color='#FFFFFF'))
    )
    layers: list[ft.Control] = [badge]
    if annotated:
        layers.append(ft.Container(width=110,height=28,bgcolor='#D9131924'))
        layers.append(ft.Container(width=110,height=28,
            alignment=ft.Alignment.CENTER,
            content=ft.Row(controls=[
                ft.Text(icon,size=14,weight=ft.FontWeight.BOLD,color=icon_color),
                ft.Text(value_label,size=12,weight=ft.FontWeight.BOLD,color='#FFFFFF'),
            ],alignment=ft.MainAxisAlignment.CENTER,
               vertical_alignment=ft.CrossAxisAlignment.CENTER,spacing=3)))
    return ft.GestureDetector(
        content=ft.Container(content=ft.Stack(controls=layers,width=110,height=28),
                             padding=2,border_radius=6,
                             border=ft.Border.all(2,'#C85E62' if bad else '#48A579' if good else '#405068')),
        on_tap=lambda event,k=kind,t=attack_type,e=entry:_details(page,k,t,e),
        mouse_cursor=ft.MouseCursor.CLICK)


def team_coverage_panel(page: ft.Page, coverage: dict[str, Any], *, heading: str = 'Team Coverage', offensive_description: str | None = None) -> ft.Control:
    """Render two 6×3 grids, horizontally scrollable on narrow mobile screens."""
    sections: list[ft.Control] = [ft.Text(heading,size=18,weight=ft.FontWeight.BOLD)]
    for kind, explanation in (
        ('defensive','Average incoming type multiplier across the team; lower is better. ★ means at least one immune teammate. Unspecified Abilities are not assumed.'),
        ('offensive','Best planned move effectiveness against each single defending type; higher is better. No move means no coverage credit.'),
    ):
        if kind == 'offensive' and offensive_description is not None:
            explanation = offensive_description
        data = coverage.get(kind,{})
        names = list(data)
        grids: list[ft.Control] = [
            ft.Row(
                controls=[_tile(page,kind,name,data[name]) for name in names[row:row+6]],
                spacing=4,
            )
            for row in range(0,len(names),6)
        ]
        grid_column: ft.Control = ft.Column(controls=grids, spacing=4, tight=True)
        sections.extend([
            ft.Text(f'{kind.title()} coverage',weight=ft.FontWeight.BOLD,size=14),
            ft.Text(explanation,size=12,color='#AAB3C3'),
            ft.Row(controls=[grid_column],
                   scroll=ft.ScrollMode.AUTO),
        ])
    if coverage.get('warnings'):
        sections.append(ft.Text('Some types or moves could not be assessed; see the selected Pokémon and moves.',
                                size=11,color='#AAB3C3'))
    return ft.Container(content=ft.Column(controls=sections,spacing=8),padding=12,
                        border=ft.Border.all(1,'#405068'),border_radius=12)
