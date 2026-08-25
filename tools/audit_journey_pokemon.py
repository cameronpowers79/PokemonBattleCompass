"""Audit deterministic acquisition gates in journey_pokemon.json.

The script is report-only. It never edits Journey data.

Usage:
    python tools/audit_journey_pokemon.py
    python tools/audit_journey_pokemon.py --input data/journey_pokemon.json
    python tools/audit_journey_pokemon.py --output-dir audit_reports

Outputs:
    journey_pokemon_acquisition_audit.csv
    journey_pokemon_summary_audit.csv
"""

from __future__ import annotations

import argparse
import csv
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from journey_acquisition_rules import (
    LOCATION_REQUIRED_BADGES,
    RAID_STAR_REQUIRED_BADGES,
    WEATHER_REQUIRED_BADGES,
    WILD_CATCH_METHODS,
    METHODS_WITH_POSSIBLE_UNMODELED_GATES,
    VERIFIED_ACQUISITION_BADGES,
    badges_needed_for_wild_level,
)


ROOT_DIR = Path(__file__).resolve().parents[1]
DEFAULT_INPUT = ROOT_DIR / "data" / "journey_pokemon.json"
DEFAULT_OUTPUT_DIR = ROOT_DIR / "audit_reports"


@dataclass
class GateResult:
    computed_badge: int
    reasons: list[str]
    review_flags: list[str]


def _as_int(value: Any) -> int | None:
    if value is None or isinstance(value, bool):
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def _location_gate(location: str) -> tuple[int, str | None]:
    location = location.strip()
    if not location:
        return 0, "Missing location"

    if location not in LOCATION_REQUIRED_BADGES:
        return 0, f"Unknown location access rule: {location}"

    return LOCATION_REQUIRED_BADGES[location], None


def _effective_location(
    acquisition: dict[str, Any],
    encounter: dict[str, Any] | None,
) -> str:
    if encounter:
        encounter_location = str(encounter.get("location") or "").strip()
        if encounter_location:
            return encounter_location

    return str(acquisition.get("location") or "").strip()


def _verified_acquisition_gate(
    pokemon_name: str,
    acquisition: dict[str, Any],
) -> tuple[int, str | None, bool]:
    method = str(acquisition.get("method") or "").strip()
    location = str(acquisition.get("location") or "").strip()
    key = (pokemon_name, method, location)

    if key not in VERIFIED_ACQUISITION_BADGES:
        return 0, None, False

    required = VERIFIED_ACQUISITION_BADGES[key]
    reason = (
        f"Verified special acquisition requires {required} badge(s)"
        if required
        else "Verified special acquisition is available before the first badge"
    )
    return required, reason, True


def _weather_gate(
    encounter: dict[str, Any] | None,
) -> tuple[int, str | None]:
    if not encounter:
        return 0, None

    weather = str(encounter.get("weather") or "").strip()
    if not weather:
        return 0, None

    required = WEATHER_REQUIRED_BADGES.get(weather, 0)
    if required:
        return required, f"{weather} unlocks after {required} badge(s)"

    return 0, None


def _catch_level_gate(
    acquisition: dict[str, Any],
    encounter: dict[str, Any] | None,
) -> tuple[int, str | None, str | None]:
    if acquisition.get("method") not in WILD_CATCH_METHODS:
        return 0, None, None

    if not encounter:
        return 0, None, "Wild acquisition has no encounter level data"

    level_min = _as_int(encounter.get("level_min"))
    level_max = _as_int(encounter.get("level_max"))

    # Earliest legality is determined by the lowest level that can actually
    # appear. If that level is catchable, at least part of the encounter range
    # is obtainable.
    level_for_gate = level_min if level_min is not None else level_max
    required = badges_needed_for_wild_level(level_for_gate)

    if required is None:
        return 0, None, "Wild encounter has no usable level range"

    reason = (
        f"Lv. {level_for_gate} minimum requires {required} badge(s) "
        "under the wild catch cap"
        if required
        else None
    )
    return required, reason, None


def _raid_gate(
    acquisition: dict[str, Any],
    verified_special: bool,
) -> tuple[int, str | None, str | None]:
    if acquisition.get("method") != "max_raid_battle":
        return 0, None, None

    # Some den encounters are verified rare spawns without a meaningful
    # minimum-star floor (currently Galarian Yamask for Runerigus). An exact
    # verified acquisition override handles those cases.
    if verified_special:
        return 0, None, None

    star_level = _as_int(acquisition.get("minimum_star_level"))
    if star_level is None:
        return 0, None, "Max Raid acquisition has no minimum_star_level"

    if star_level not in RAID_STAR_REQUIRED_BADGES:
        return 0, None, f"Unknown Max Raid star tier: {star_level}★"

    required = RAID_STAR_REQUIRED_BADGES[star_level]
    reason = (
        f"{star_level}★ Max Raids require {required} badge(s)"
        if required
        else f"{star_level}★ Max Raids are available before the first badge"
    )
    return required, reason, None


def compute_gate(
    pokemon_name: str,
    acquisition: dict[str, Any],
    encounter: dict[str, Any] | None,
) -> GateResult:
    gate_values: list[int] = [0]
    reasons: list[str] = []
    review_flags: list[str] = []

    verified_badge, verified_reason, verified_special = (
        _verified_acquisition_gate(pokemon_name, acquisition)
    )
    gate_values.append(verified_badge)
    if verified_reason:
        reasons.append(verified_reason)

    location = _effective_location(acquisition, encounter)
    location_badge, location_review = _location_gate(location)
    gate_values.append(location_badge)
    if location_badge:
        reasons.append(
            f"{location} is accessible after {location_badge} badge(s)"
        )
    if location_review:
        review_flags.append(location_review)

    weather_badge, weather_reason = _weather_gate(encounter)
    gate_values.append(weather_badge)
    if weather_reason:
        reasons.append(weather_reason)

    level_badge, level_reason, level_review = _catch_level_gate(
        acquisition,
        encounter,
    )
    gate_values.append(level_badge)
    if level_reason:
        reasons.append(level_reason)
    if level_review:
        review_flags.append(level_review)

    raid_badge, raid_reason, raid_review = _raid_gate(
        acquisition,
        verified_special,
    )
    gate_values.append(raid_badge)
    if raid_reason:
        reasons.append(raid_reason)
    if raid_review:
        review_flags.append(raid_review)

    # acquisition["required_badge"] is a declaration to validate, not an
    # authoritative input to the computed gate. Feeding it back into the
    # calculation would allow an incorrect declaration to validate itself.
    if (
        not verified_special
        and acquisition.get("method") in METHODS_WITH_POSSIBLE_UNMODELED_GATES
        and _as_int(acquisition.get("required_badge")) is None
    ):
        review_flags.append(
            f"{acquisition.get('method')} may have an unmodeled story, "
            "trade-partner, or parent-access gate"
        )

    return GateResult(
        computed_badge=max(gate_values),
        reasons=reasons,
        review_flags=review_flags,
    )


def _iter_acquisitions(
    pokemon: dict[str, Any],
) -> list[tuple[str, int, dict[str, Any]]]:
    rows: list[tuple[str, int, dict[str, Any]]] = []

    primary = pokemon.get("primary_acquisition")
    if isinstance(primary, dict):
        rows.append(("primary", 0, primary))

    alternates = pokemon.get("alternate_acquisitions", [])
    if isinstance(alternates, list):
        for index, acquisition in enumerate(alternates, start=1):
            if isinstance(acquisition, dict):
                rows.append(("alternate", index, acquisition))

    return rows


def _encounter_rows(
    acquisition: dict[str, Any],
) -> list[dict[str, Any] | None]:
    encounters = acquisition.get("encounters", [])
    if not isinstance(encounters, list):
        return [None]

    cleaned: list[dict[str, Any] | None] = [
        encounter
        for encounter in encounters
        if isinstance(encounter, dict)
    ]

    return cleaned or [None]


def _compare_badges(
    declared: int | None,
    computed: int,
    review_flags: list[str],
) -> str:
    if review_flags:
        return "REVIEW"
    if declared is None:
        return "MISSING_DECLARATION"
    if declared < computed:
        return "TOO_PERMISSIVE"
    if declared > computed:
        return "TOO_RESTRICTIVE"
    return "OK"


def build_audit_rows(
    pokemon_data: list[dict[str, Any]],
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    detail_rows: list[dict[str, Any]] = []
    summary_rows: list[dict[str, Any]] = []

    for pokemon in pokemon_data:
        pokemon_name = str(pokemon.get("pokemon") or "Unknown")
        acquire_as = str(pokemon.get("acquire_as") or pokemon_name)
        pokemon_declared_badge = _as_int(pokemon.get("required_badge"))

        acquisition_minima: list[tuple[str, int, int]] = []
        all_candidate_badges: list[int] = []
        primary_candidate_badges: list[int] = []
        record_review_flags: list[str] = []

        for kind, acquisition_index, acquisition in _iter_acquisitions(pokemon):
            candidate_badges: list[int] = []

            for encounter_index, encounter in enumerate(
                _encounter_rows(acquisition),
                start=1,
            ):
                gate = compute_gate(pokemon_name, acquisition, encounter)
                candidate_badges.append(gate.computed_badge)
                all_candidate_badges.append(gate.computed_badge)
                if kind == "primary":
                    primary_candidate_badges.append(gate.computed_badge)

                record_review_flags.extend(gate.review_flags)

                acquisition_declared_badge = _as_int(
                    acquisition.get("required_badge")
                )
                declared_for_candidate = (
                    acquisition_declared_badge
                    if acquisition_declared_badge is not None
                    else pokemon_declared_badge
                )

                encounter_location = (
                    str(encounter.get("location") or "").strip()
                    if encounter
                    else ""
                )
                encounter_method = (
                    str(encounter.get("method") or "").strip()
                    if encounter
                    else ""
                )
                weather = (
                    str(encounter.get("weather") or "").strip()
                    if encounter
                    else ""
                )

                detail_rows.append(
                    {
                        "pokemon": pokemon_name,
                        "acquire_as": acquire_as,
                        "acquisition_kind": kind,
                        "acquisition_index": acquisition_index,
                        "acquisition_method": acquisition.get("method", ""),
                        "acquisition_location": acquisition.get("location", ""),
                        "encounter_index": encounter_index,
                        "encounter_location": encounter_location,
                        "encounter_method": encounter_method,
                        "weather": weather,
                        "rarity_percent": (
                            encounter.get("rarity_percent", "")
                            if encounter
                            else ""
                        ),
                        "level_min": (
                            encounter.get("level_min", "")
                            if encounter
                            else ""
                        ),
                        "level_max": (
                            encounter.get("level_max", "")
                            if encounter
                            else ""
                        ),
                        "pokemon_declared_badge": pokemon_declared_badge,
                        "acquisition_declared_badge": acquisition_declared_badge,
                        "declared_badge_used": declared_for_candidate,
                        "computed_minimum_badge": gate.computed_badge,
                        "gate_reasons": " | ".join(gate.reasons),
                        "review_flags": " | ".join(gate.review_flags),
                        "validation_result": _compare_badges(
                            declared_for_candidate,
                            gate.computed_badge,
                            gate.review_flags,
                        ),
                    }
                )

            if candidate_badges:
                acquisition_minima.append(
                    (kind, acquisition_index, min(candidate_badges))
                )

        computed_record_badge = (
            min(all_candidate_badges)
            if all_candidate_badges
            else None
        )
        computed_primary_badge = (
            min(primary_candidate_badges)
            if primary_candidate_badges
            else None
        )

        unique_review_flags = sorted(set(record_review_flags))
        if computed_record_badge is None:
            record_result = "REVIEW"
            unique_review_flags.append("No acquisition candidates found")
        elif unique_review_flags:
            record_result = "REVIEW"
        elif pokemon_declared_badge is None:
            record_result = "MISSING_DECLARATION"
        elif pokemon_declared_badge < computed_record_badge:
            record_result = "TOO_PERMISSIVE"
        elif pokemon_declared_badge > computed_record_badge:
            record_result = "TOO_RESTRICTIVE"
        else:
            record_result = "OK"

        summary_rows.append(
            {
                "pokemon": pokemon_name,
                "acquire_as": acquire_as,
                "declared_required_badge": pokemon_declared_badge,
                "computed_record_minimum_badge": computed_record_badge,
                "computed_primary_minimum_badge": computed_primary_badge,
                "validation_result": record_result,
                "review_flags": " | ".join(unique_review_flags),
                "acquisition_count": len(acquisition_minima),
                "candidate_count": len(all_candidate_badges),
            }
        )

    return detail_rows, summary_rows


def write_csv(
    path: Path,
    rows: list[dict[str, Any]],
) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)

    if not rows:
        path.write_text("", encoding="utf-8")
        return

    with path.open("w", encoding="utf-8", newline="") as file:
        writer = csv.DictWriter(
            file,
            fieldnames=list(rows[0].keys()),
        )
        writer.writeheader()
        writer.writerows(rows)


def print_summary(summary_rows: list[dict[str, Any]]) -> None:
    counts: dict[str, int] = {}
    for row in summary_rows:
        result = str(row["validation_result"])
        counts[result] = counts.get(result, 0) + 1

    print(f"Pokémon audited: {len(summary_rows)}")
    for label in (
        "OK",
        "TOO_PERMISSIVE",
        "TOO_RESTRICTIVE",
        "MISSING_DECLARATION",
        "REVIEW",
    ):
        print(f"{label:20} {counts.get(label, 0)}")

    flagged = [
        row
        for row in summary_rows
        if row["validation_result"] != "OK"
    ]
    if flagged:
        print("\nFlagged Pokémon:")
        for row in flagged:
            print(
                f"  {row['pokemon']}: "
                f"declared={row['declared_required_badge']} "
                f"computed={row['computed_record_minimum_badge']} "
                f"[{row['validation_result']}]"
            )


def main() -> None:
    parser = argparse.ArgumentParser(
        description=(
            "Audit deterministic badge gates in journey_pokemon.json "
            "without modifying source data."
        )
    )
    parser.add_argument(
        "--input",
        type=Path,
        default=DEFAULT_INPUT,
        help=f"Journey Pokémon JSON (default: {DEFAULT_INPUT})",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=DEFAULT_OUTPUT_DIR,
        help=f"CSV report directory (default: {DEFAULT_OUTPUT_DIR})",
    )
    args = parser.parse_args()

    raw = json.loads(args.input.read_text(encoding="utf-8"))
    if not isinstance(raw, list):
        raise ValueError("journey_pokemon.json must contain a top-level list.")

    pokemon_data = [
        row
        for row in raw
        if isinstance(row, dict)
    ]

    detail_rows, summary_rows = build_audit_rows(pokemon_data)

    detail_path = (
        args.output_dir
        / "journey_pokemon_acquisition_audit.csv"
    )
    summary_path = (
        args.output_dir
        / "journey_pokemon_summary_audit.csv"
    )

    write_csv(detail_path, detail_rows)
    write_csv(summary_path, summary_rows)

    print_summary(summary_rows)
    print(f"\nDetailed report: {detail_path}")
    print(f"Summary report:  {summary_path}")


if __name__ == "__main__":
    main()