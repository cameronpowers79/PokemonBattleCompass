"""Convert Journey catalog records and player move plans to team-coverage inputs.

Planned evolution targets use the target's type, not their acquire-as stage.
Unknown types are omitted rather than silently treated as neutral.
"""
from __future__ import annotations
from collections.abc import Mapping, Sequence
from typing import Any
from engine.team_coverage import team_coverage


def catalog_team_member(record: Mapping[str, Any], *, moves: Sequence[str] = (),
                        ability: str = "", form: str = "", gender: str = "") -> dict[str, Any]:
    name = str(record.get("Pokemon") or record.get("pokemon") or "").strip()
    forms = record.get("types")
    selected_types: list[str] = []
    if isinstance(forms, dict):
        wanted = [form, f"{name} ({gender})" if gender else "", name]
        for label in wanted:
            if label and isinstance(forms.get(label), list):
                selected_types = forms[label]
                break
        if not selected_types and len(forms) == 1:
            selected_types = next(iter(forms.values()))
        if not selected_types:
            alternatives = [types for key, types in forms.items()
                            if key.casefold().endswith(" " + name.casefold()) and isinstance(types, list)]
            if len(alternatives) == 1:
                selected_types = alternatives[0]
    else:
        selected_types = [record.get("Type1", ""), record.get("Type2", "")]
    member = {"Pokemon": name, "Ability": ability or record.get("Ability", ""),
              "Type1": selected_types[0] if selected_types else "",
              "Type2": selected_types[1] if len(selected_types) > 1 else ""}
    for i, move in enumerate(list(moves)[:4], 1):
        member[f"Move{i}"] = move
    return member


def planned_moves_from_slots(slots: Sequence[Any]) -> list[str]:
    return [str(slot.get("move_name") or "").strip() for slot in slots[:4]
            if isinstance(slot, Mapping) and str(slot.get("move_name") or "").strip()]


def planned_coverage(records: Sequence[Mapping[str, Any]],
                     slots_by_id: Mapping[str, Sequence[Any]],
                     type_chart: Mapping[str, Mapping[str, float]], moves_data: Sequence[Mapping[str, Any]],
                     forms_by_id: Mapping[str, Mapping[str, str]] | None = None) -> dict[str, Any]:
    members = []
    for record in records[:6]:
        identity = str(record.get("id") or "")
        prefs = (forms_by_id or {}).get(identity, {})
        members.append(catalog_team_member(record, moves=planned_moves_from_slots(slots_by_id.get(identity, [])),
            form=str(prefs.get("form") or ""), gender=str(prefs.get("gender") or "")))
    return team_coverage(members, type_chart, moves_data)
