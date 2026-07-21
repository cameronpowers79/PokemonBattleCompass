"""
Shared reference popups for Pokémon types and Abilities.
"""

from __future__ import annotations

from typing import Literal, cast

import flet as ft

from ui.constants import POKEMON_TYPES, TYPE_COLORS
from ui.theme import (
    BORDER_DEFAULT,
    PRIMARY_BLUE,
    PRIMARY_BLUE_SOFT,
    SURFACE_RAISED,
    TEXT_MUTED,
    TEXT_PRIMARY,
    TEXT_SECONDARY,
)


def _type_badge_src(pokemon_type: str) -> str:
    return f"type_badges/{pokemon_type}.png"


def _close_dialog(
    page: ft.Page,
    event: ft.Event[ft.Button],
) -> None:
    del event
    page.pop_dialog()
    page.update()


def _build_type_chip(
    pokemon_type: str,
) -> ft.Control:
    return ft.Container(
        content=ft.Row(
            controls=cast(
                list[ft.Control],
                [
                    ft.Image(
                        src=_type_badge_src(
                            pokemon_type
                        ),
                        height=18,
                        fit=ft.BoxFit.CONTAIN,
                        semantics_label=(
                            f"{pokemon_type} type"
                        ),
                    ),
                ],
            ),
            spacing=6,
            tight=True,
        ),
        padding=ft.Padding.symmetric(
            horizontal=9,
            vertical=6,
        ),
        bgcolor=TYPE_COLORS.get(
            pokemon_type,
            SURFACE_RAISED,
        ),
        border=ft.Border.all(
            1,
            "#40FFFFFF",
        ),
        border_radius=9,
    )


def _build_type_group(
    *,
    title: str,
    multiplier_label: str,
    types: list[str],
    accent: str,
) -> ft.Control:
    chips = cast(
        list[ft.Control],
        [
            _build_type_chip(
                pokemon_type
            )
            for pokemon_type in types
        ],
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
                                ft.Text(
                                    title,
                                    size=16,
                                    weight=ft.FontWeight.BOLD,
                                    color=accent,
                                ),
                                ft.Text(
                                    multiplier_label,
                                    size=13,
                                    weight=ft.FontWeight.BOLD,
                                    color=TEXT_MUTED,
                                ),
                            ],
                        ),
                        spacing=8,
                        wrap=True,
                    ),
                    ft.Row(
                        controls=chips,
                        spacing=7,
                        run_spacing=7,
                        wrap=True,
                    ),
                ],
            ),
            spacing=9,
        ),
        padding=13,
        bgcolor=SURFACE_RAISED,
        border=ft.Border.all(
            1,
            BORDER_DEFAULT,
        ),
        border_radius=12,
    )


def show_type_matchup_dialog(
    *,
    page: ft.Page,
    pokemon_type: str,
    type_chart: dict,
    mode: Literal["defensive", "offensive"] = "defensive",
) -> None:
    """Show single-type defensive or offensive matchups."""

    if mode == "offensive":
        super_effective: list[str] = []
        not_very_effective: list[str] = []
        no_effect: list[str] = []
        neutral: list[str] = []

        for defending_type in POKEMON_TYPES:
            multiplier = (
                type_chart.get(
                    pokemon_type,
                    {},
                ).get(
                    defending_type,
                    1,
                )
            )

            if multiplier == 0:
                no_effect.append(defending_type)
            elif multiplier > 1:
                super_effective.append(defending_type)
            elif multiplier < 1:
                not_very_effective.append(defending_type)
            else:
                neutral.append(defending_type)

        groups = cast(list[ft.Control], [])

        if super_effective:
            groups.append(
                _build_type_group(
                    title="Super effective against",
                    multiplier_label="2× damage",
                    types=super_effective,
                    accent="#86EFAC",
                )
            )

        if not_very_effective:
            groups.append(
                _build_type_group(
                    title="Not very effective against",
                    multiplier_label="½× damage",
                    types=not_very_effective,
                    accent="#FCA5A5",
                )
            )

        if no_effect:
            groups.append(
                _build_type_group(
                    title="No effect against",
                    multiplier_label="0× damage",
                    types=no_effect,
                    accent="#93C5FD",
                )
            )

        groups.append(
            _build_type_group(
                title="Normal damage against",
                multiplier_label="1× damage",
                types=neutral,
                accent=TEXT_SECONDARY,
            )
        )

        dialog_title = f"{pokemon_type} — Offensive Matchups"
        explanation = (
            f"These results show how a {pokemon_type}-type move affects "
            "a single defending type. A second defending type can change "
            "the final matchup."
        )
    else:
        weak_to: list[str] = []
        resists: list[str] = []
        immune_to: list[str] = []
        neutral = []

        for attack_type in POKEMON_TYPES:
            multiplier = (
                type_chart.get(
                    attack_type,
                    {},
                ).get(
                    pokemon_type,
                    1,
                )
            )

            if multiplier == 0:
                immune_to.append(attack_type)
            elif multiplier > 1:
                weak_to.append(attack_type)
            elif multiplier < 1:
                resists.append(attack_type)
            else:
                neutral.append(attack_type)

        groups = cast(list[ft.Control], [])

        if weak_to:
            groups.append(
                _build_type_group(
                    title="Weak to",
                    multiplier_label="2× damage",
                    types=weak_to,
                    accent="#FCA5A5",
                )
            )

        if resists:
            groups.append(
                _build_type_group(
                    title="Resists",
                    multiplier_label="½× damage",
                    types=resists,
                    accent="#86EFAC",
                )
            )

        if immune_to:
            groups.append(
                _build_type_group(
                    title="Immune to",
                    multiplier_label="0× damage",
                    types=immune_to,
                    accent="#93C5FD",
                )
            )

        groups.append(
            _build_type_group(
                title="Normal damage",
                multiplier_label="1× damage",
                types=neutral,
                accent=TEXT_SECONDARY,
            )
        )

        dialog_title = f"{pokemon_type} — Defensive Matchups"
        explanation = (
            "These results describe a single "
            f"{pokemon_type} type. A second type "
            "can change the final matchup."
        )

    page.show_dialog(
        ft.AlertDialog(
            modal=True,
            title=ft.Row(
                controls=cast(
                    list[ft.Control],
                    [
                        ft.Image(
                            src=_type_badge_src(pokemon_type),
                            height=28,
                            fit=ft.BoxFit.CONTAIN,
                            semantics_label=f"{pokemon_type} type",
                        ),
                        ft.Text(
                            dialog_title,
                            size=21,
                            weight=ft.FontWeight.BOLD,
                            color=TEXT_PRIMARY,
                            expand=True,
                        ),
                    ],
                ),
                spacing=10,
                vertical_alignment=ft.CrossAxisAlignment.CENTER,
            ),
            content=ft.Container(
                content=ft.Column(
                    controls=cast(
                        list[ft.Control],
                        [
                            ft.Text(
                                explanation,
                                size=14,
                                color=TEXT_SECONDARY,
                            ),
                            *groups,
                        ],
                    ),
                    spacing=12,
                    scroll=ft.ScrollMode.AUTO,
                ),
                width=580,
                height=520,
            ),
            actions=cast(
                list[ft.Control],
                [
                    ft.Button(
                        content="Close",
                        on_click=(
                            lambda event: _close_dialog(
                                page,
                                event,
                            )
                        ),
                    ),
                ],
            ),
            actions_alignment=ft.MainAxisAlignment.END,
        )
    )


def show_ability_dialog(
    *,
    page: ft.Page,
    ability_name: str,
    ability_descriptions: dict[str, str],
    ability_rules: list[dict],
) -> None:
    """Show a player-facing Ability description and modeling status."""

    description = ability_descriptions.get(
        ability_name,
        (
            "A player-facing description is not yet available "
            "for this Ability."
        ),
    )

    matching_rules = [
        rule
        for rule in ability_rules
        if rule.get("Ability") == ability_name
    ]

    controls = cast(
        list[ft.Control],
        [
            ft.Text(
                description,
                size=15,
                color=TEXT_SECONDARY,
            ),
            ft.Divider(
                color=BORDER_DEFAULT,
                height=1,
            ),
            ft.Text(
                "Battle Compass Modeling",
                size=17,
                weight=ft.FontWeight.BOLD,
                color=TEXT_PRIMARY,
            ),
        ],
    )

    if matching_rules:
        unique_notes: list[str] = []

        for rule in matching_rules:
            note = rule.get("Notes")

            if (
                isinstance(note, str)
                and note.strip()
                and note.strip()
                not in unique_notes
            ):
                unique_notes.append(
                    note.strip()
                )

        controls.append(
            ft.Container(
                content=ft.Row(
                    controls=cast(
                        list[ft.Control],
                        [
                            ft.Icon(
                                ft.Icons.CHECK_CIRCLE_ROUNDED,
                                size=20,
                                color="#4ADE80",
                            ),
                            ft.Text(
                                (
                                    "This Ability has modeled behavior "
                                    "in matchup calculations."
                                ),
                                size=14,
                                weight=ft.FontWeight.BOLD,
                                color="#C9F7D7",
                                expand=True,
                            ),
                        ],
                    ),
                    spacing=9,
                ),
                padding=12,
                bgcolor="#173828",
                border_radius=10,
            )
        )

        controls.extend(
            ft.Row(
                controls=cast(
                    list[ft.Control],
                    [
                        ft.Icon(
                            ft.Icons.EXPLORE_OUTLINED,
                            size=17,
                            color=PRIMARY_BLUE,
                        ),
                        ft.Text(
                            note,
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
            for note in unique_notes
        )
    else:
        controls.append(
            ft.Container(
                content=ft.Row(
                    controls=cast(
                        list[ft.Control],
                        [
                            ft.Icon(
                                ft.Icons.INFO_OUTLINE_ROUNDED,
                                size=20,
                                color=PRIMARY_BLUE,
                            ),
                            ft.Text(
                                (
                                    "This is a valid Ability, but its "
                                    "battle effect is not currently "
                                    "included in matchup scoring."
                                ),
                                size=14,
                                color="#D7E8FF",
                                expand=True,
                            ),
                        ],
                    ),
                    spacing=9,
                ),
                padding=12,
                bgcolor=PRIMARY_BLUE_SOFT,
                border_radius=10,
            )
        )

    page.show_dialog(
        ft.AlertDialog(
            modal=True,
            title=ft.Text(
                ability_name,
                size=23,
                weight=ft.FontWeight.BOLD,
                color=TEXT_PRIMARY,
            ),
            content=ft.Container(
                content=ft.Column(
                    controls=controls,
                    spacing=13,
                    tight=True,
                ),
                width=540,
            ),
            actions=cast(
                list[ft.Control],
                [
                    ft.Button(
                        content="Close",
                        on_click=(
                            lambda event:
                            _close_dialog(
                                page,
                                event,
                            )
                        ),
                    ),
                ],
            ),
            actions_alignment=(
                ft.MainAxisAlignment.END
            ),
        )
    )



MOVE_TAG_DESCRIPTIONS = {
    "Pivot": "Switches the user out after the move succeeds.",
    "Protection": "Protects the user from most attacks for one turn.",
    "Recovery": "Restores some of the user's HP.",
    "RecoveryMove": "Restores some of the user's HP.",
    "Drain": "Restores HP based on the damage dealt.",
    "HPStealingMove": "Restores HP based on the damage dealt.",
    "Recoil": "The user takes recoil damage after attacking.",
    "RecoilMove": "The user takes recoil damage after attacking.",
    "ContactPunisher": "Can punish an opponent for making contact.",
    "Screen": "Reduces damage received by the user's side of the field.",
    "Weather": "Creates or interacts with a weather condition.",
    "Terrain": "Creates or interacts with battlefield terrain.",
    "StatReset": "Resets stat changes.",
    "ItemRemoval": "Can remove, steal, or consume the target's held item.",
    "ForcedSwitch": "Forces the target to switch out when possible.",
    "AbilitySuppression": "Can suppress or remove the target's Ability.",
    "PassiveDamage": "Can continue damaging the target after the move lands.",
    "Hazard": "Can place an entry hazard on the opposing side.",
}

ACTIVATION_CONDITION_DESCRIPTIONS = {
    "targethasstatus": "if the target has a status condition",
    "targetstatused": "if the target has a status condition",
    "targetstatuscondition": "if the target has a status condition",
    "targetanystatus": "if the target has a status condition",
    "targetpoisoned": "if the target is poisoned",
    "targetbadlypoisoned": "if the target is poisoned",
    "targetburned": "if the target is burned",
    "targetparalyzed": "if the target is paralyzed",
    "targetasleep": "if the target is asleep",
    "targetfrozen": "if the target is frozen",
    "targetathalfhporless": "if the target is at half HP or less",
    "targethalfhorless": "if the target is at half HP or less",
    "targetbelowhalfhealth": "if the target is at half HP or less",
    "userhasstatus": "while the user is burned, poisoned, or paralyzed",
    "userstatused": "while the user is burned, poisoned, or paralyzed",
    "userburnedpoisonedorparalyzed": (
        "while the user is burned, poisoned, or paralyzed"
    ),
    "userburnpoisonparalysis": (
        "while the user is burned, poisoned, or paralyzed"
    ),
    "targetalreadyacted": "if the target has already acted this turn",
    "usermovesaftertarget": "if the user moves after the target",
    "userwashit": "if the user was hit earlier in the turn",
    "userhitbeforemove": "if the user was hit before using the move",
    "requiresuserhit": "if the user was hit earlier in the turn",
    "previousmovefailed": "if the user's previous move failed",
    "previousmovefailedagainsttarget": (
        "if the user's previous move against the target failed"
    ),
}


def _clean_text(value: object) -> str | None:
    if not isinstance(value, str):
        return None

    cleaned = value.strip()
    return cleaned or None


def _numeric_value(value: object) -> float | None:
    if isinstance(value, bool):
        return float(value)

    if isinstance(value, (int, float)):
        return float(value)

    if isinstance(value, str):
        try:
            return float(value.strip())
        except ValueError:
            return None

    return None


def _format_number(value: float) -> str:
    if value.is_integer():
        return str(int(value))

    return f"{value:g}"


def _normalized_key(value: object) -> str:
    text = _clean_text(value)

    if not text:
        return ""

    return "".join(
        character
        for character in text.lower()
        if character.isalnum()
    )


def _activation_description(value: object) -> str | None:
    return ACTIVATION_CONDITION_DESCRIPTIONS.get(
        _normalized_key(value)
    )


def _status_effect_description(
    value: object,
    *,
    is_status_move: bool,
) -> str | None:
    status = _clean_text(value)

    if not status:
        return None

    normalized = status.lower()

    descriptions = {
        "burn": (
            "Burns the target."
            if is_status_move
            else "May burn the target."
        ),
        "paralysis": (
            "Paralyzes the target."
            if is_status_move
            else "May paralyze the target."
        ),
        "paralyze": (
            "Paralyzes the target."
            if is_status_move
            else "May paralyze the target."
        ),
        "poison": (
            "Poisons the target."
            if is_status_move
            else "May poison the target."
        ),
        "badly poison": (
            "Badly poisons the target."
            if is_status_move
            else "May badly poison the target."
        ),
        "sleep": (
            "Puts the target to sleep."
            if is_status_move
            else "May put the target to sleep."
        ),
        "freeze": (
            "Freezes the target."
            if is_status_move
            else "May freeze the target."
        ),
        "confusion": (
            "Confuses the target."
            if is_status_move
            else "May confuse the target."
        ),
    }

    return descriptions.get(
        normalized,
        (
            f"Inflicts {status}."
            if is_status_move
            else f"May inflict {status}."
        ),
    )


def _stage_change_descriptions(move: dict) -> list[str]:
    stat_fields = (
        ("AtkStageChange", "Attack"),
        ("DefStageChange", "Defense"),
        ("SpAStageChange", "Special Attack"),
        ("SpDStageChange", "Special Defense"),
        ("SpeStageChange", "Speed"),
    )

    descriptions: list[str] = []

    for field_name, stat_name in stat_fields:
        stage_change = _numeric_value(
            move.get(field_name)
        )

        if (
            stage_change is None
            or stage_change == 0
        ):
            continue

        stage_count = abs(
            int(stage_change)
        )

        stage_text = (
            "one stage"
            if stage_count == 1
            else f"{stage_count} stages"
        )

        if stage_change > 0:
            descriptions.append(
                (
                    f"Raises the user's {stat_name} "
                    f"by {stage_text}."
                )
            )
        else:
            descriptions.append(
                (
                    f"Lowers the target's {stat_name} "
                    f"by {stage_text}."
                )
            )

    return descriptions


def _move_effect_descriptions(
    move: dict,
) -> list[str]:
    """Return the audited player-facing move description."""

    effect_description = _clean_text(
        move.get("EffectDescription")
    )

    if effect_description:
        return [
            line.strip()
            for line in effect_description.splitlines()
            if line.strip()
        ]

    return [
        (
            "This move's full effect is not yet "
            "documented in the Battle Compass."
        )
    ]


def _move_navigation_aids(
    move: dict,
) -> list[str]:
    aids: list[str] = []

    if move.get("MakesContact") is True:
        aids.append(
            "Makes contact."
        )

    hits = _numeric_value(
        move.get("Hits")
    )

    if hits is not None and hits > 1:
        aids.append(
            f"Hits {_format_number(hits)} times."
        )

    priority = _numeric_value(
        move.get("Priority")
    )

    if priority is not None and priority != 0:
        if priority > 0:
            aids.append(
                (
                    "Has increased priority "
                    f"(+{_format_number(priority)})."
                )
            )
        else:
            aids.append(
                (
                    "Has reduced priority "
                    f"({_format_number(priority)})."
                )
            )

    mechanics_tags = move.get(
        "MechanicsTags",
        [],
    )

    if isinstance(mechanics_tags, list):
        for tag in mechanics_tags:
            if not isinstance(tag, str):
                continue

            description = MOVE_TAG_DESCRIPTIONS.get(
                tag
            )

            if (
                description
                and description not in aids
            ):
                aids.append(
                    description
                )

    return aids


def _move_stat_box(
    label: str,
    value: str,
) -> ft.Control:
    return ft.Container(
        content=ft.Column(
            controls=cast(
                list[ft.Control],
                [
                    ft.Text(
                        label,
                        size=12,
                        color=TEXT_MUTED,
                    ),
                    ft.Text(
                        value,
                        size=18,
                        weight=ft.FontWeight.BOLD,
                        color=TEXT_PRIMARY,
                    ),
                ],
            ),
            spacing=3,
        ),
        col={
            "xs": 12,
            "sm": 4,
        },
        padding=12,
        bgcolor=SURFACE_RAISED,
        border_radius=10,
    )


def show_move_dialog(
    *,
    page: ft.Page,
    move: dict,
) -> None:
    """Show the shared player-facing move information dialog."""

    move_name = str(
        move.get("Move")
        or "Unknown Move"
    )
    move_type = _clean_text(
        move.get("Type")
    ) or "Unknown"
    category = _clean_text(
        move.get("Category")
    ) or "Unknown"

    power_value = _numeric_value(
        move.get("Power")
    )
    power = (
        "—"
        if (
            category.lower() == "status"
            or power_value is None
            or power_value <= 0
        )
        else _format_number(
            power_value
        )
    )

    accuracy_value = _numeric_value(
        move.get("Accuracy")
    )
    accuracy = (
        f"{_format_number(accuracy_value)}%"
        if accuracy_value is not None
        else "—"
    )

    priority_value = _numeric_value(
        move.get("Priority")
    )
    if priority_value is None:
        priority = "—"
    elif priority_value > 0:
        priority = f"+{_format_number(priority_value)}"
    else:
        priority = _format_number(
            priority_value
        )

    effect_lines = _move_effect_descriptions(
        move
    )
    navigation_aids = _move_navigation_aids(
        move
    )

    controls = cast(
        list[ft.Control],
        [
            ft.Row(
                controls=cast(
                    list[ft.Control],
                    [
                        ft.Image(
                            src=_type_badge_src(
                                move_type
                            ),
                            height=24,
                            fit=ft.BoxFit.CONTAIN,
                            semantics_label=(
                                f"{move_type} type"
                            ),
                        ),
                        ft.Container(
                            content=ft.Text(
                                category,
                                size=13,
                                weight=ft.FontWeight.BOLD,
                                color=TEXT_PRIMARY,
                            ),
                            padding=ft.Padding.symmetric(
                                horizontal=11,
                                vertical=6,
                            ),
                            bgcolor=PRIMARY_BLUE_SOFT,
                            border_radius=8,
                        ),
                    ],
                ),
                spacing=10,
                wrap=True,
            ),
            ft.ResponsiveRow(
                controls=cast(
                    list[ft.Control],
                    [
                        _move_stat_box(
                            "Power",
                            power,
                        ),
                        _move_stat_box(
                            "Accuracy",
                            accuracy,
                        ),
                        _move_stat_box(
                            "Priority",
                            priority,
                        ),
                    ],
                ),
                columns=12,
                spacing=10,
                run_spacing=10,
            ),
            ft.Divider(
                color=BORDER_DEFAULT,
                height=1,
            ),
            ft.Text(
                "Effect",
                size=17,
                weight=ft.FontWeight.BOLD,
                color=TEXT_PRIMARY,
            ),
            *[
                ft.Text(
                    line,
                    size=15,
                    color=TEXT_SECONDARY,
                )
                for line in effect_lines
            ],
        ],
    )

    if navigation_aids:
        controls.extend(
            [
                ft.Divider(
                    color=BORDER_DEFAULT,
                    height=1,
                ),
                ft.Text(
                    "Additional Navigation Aids",
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
                                    ft.Icons.EXPLORE_OUTLINED,
                                    size=17,
                                    color=PRIMARY_BLUE,
                                ),
                                ft.Text(
                                    aid,
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
                    for aid in navigation_aids
                ],
            ]
        )

    page.show_dialog(
        ft.AlertDialog(
            modal=True,
            title=ft.Text(
                move_name,
                size=23,
                weight=ft.FontWeight.BOLD,
                color=TEXT_PRIMARY,
            ),
            content=ft.Container(
                content=ft.Column(
                    controls=controls,
                    spacing=13,
                    tight=True,
                ),
                width=540,
            ),
            actions=cast(
                list[ft.Control],
                [
                    ft.Button(
                        content="Close",
                        on_click=(
                            lambda event:
                            _close_dialog(
                                page,
                                event,
                            )
                        ),
                    ),
                ],
            ),
            actions_alignment=(
                ft.MainAxisAlignment.END
            ),
        )
    )


def show_item_dialog(
    *,
    page: ft.Page,
    item_name: str,
    items: list[dict],
    item_sprite_src: str | None = None,
) -> None:
    """Show the current held item's player-facing description."""

    item = next(
        (
            row
            for row in items
            if row.get("Item") == item_name
        ),
        None,
    )

    description = (
        item.get("Description")
        if isinstance(item, dict)
        else None
    )

    if not isinstance(description, str) or not description.strip():
        description = (
            "This is a valid held item, but a detailed "
            "description is not currently available."
        )

    identity_controls = cast(
        list[ft.Control],
        [],
    )

    if item_sprite_src:
        identity_controls.append(
            ft.Image(
                src=item_sprite_src,
                width=44,
                height=44,
                fit=ft.BoxFit.CONTAIN,
                semantics_label=item_name,
            )
        )

    identity_controls.append(
        ft.Text(
            item_name,
            size=23,
            weight=ft.FontWeight.BOLD,
            color=TEXT_PRIMARY,
            expand=True,
        )
    )

    modeled = (
        isinstance(item, dict)
        and item.get("EffectType")
        not in {
            None,
            "None",
        }
    )

    status_content = (
        ft.Row(
            controls=cast(
                list[ft.Control],
                [
                    ft.Icon(
                        ft.Icons.CHECK_CIRCLE_ROUNDED,
                        size=20,
                        color="#4ADE80",
                    ),
                    ft.Text(
                        (
                            "This item has modeled behavior "
                            "or recommendation guidance in "
                            "Battle Compass."
                        ),
                        size=14,
                        color="#C9F7D7",
                        expand=True,
                    ),
                ],
            ),
            spacing=9,
        )
        if modeled
        else ft.Row(
            controls=cast(
                list[ft.Control],
                [
                    ft.Icon(
                        ft.Icons.INFO_OUTLINE_ROUNDED,
                        size=20,
                        color=PRIMARY_BLUE,
                    ),
                    ft.Text(
                        (
                            "This is a valid held item, but it "
                            "does not currently affect matchup scoring."
                        ),
                        size=14,
                        color="#D7E8FF",
                        expand=True,
                    ),
                ],
            ),
            spacing=9,
        )
    )

    page.show_dialog(
        ft.AlertDialog(
            modal=True,
            title=ft.Row(
                controls=identity_controls,
                spacing=10,
                vertical_alignment=(
                    ft.CrossAxisAlignment.CENTER
                ),
            ),
            content=ft.Container(
                content=ft.Column(
                    controls=cast(
                        list[ft.Control],
                        [
                            ft.Text(
                                description,
                                size=15,
                                color=TEXT_SECONDARY,
                            ),
                            ft.Divider(
                                color=BORDER_DEFAULT,
                                height=1,
                            ),
                            ft.Container(
                                content=status_content,
                                padding=12,
                                bgcolor=(
                                    "#173828"
                                    if modeled
                                    else PRIMARY_BLUE_SOFT
                                ),
                                border_radius=10,
                            ),
                        ],
                    ),
                    spacing=13,
                    tight=True,
                ),
                width=520,
            ),
            actions=cast(
                list[ft.Control],
                [
                    ft.Button(
                        content="Close",
                        on_click=(
                            lambda event:
                            _close_dialog(
                                page,
                                event,
                            )
                        ),
                    ),
                ],
            ),
            actions_alignment=(
                ft.MainAxisAlignment.END
            ),
        )
    )