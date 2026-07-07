import json
from pathlib import Path
from openpyxl import load_workbook

PROJECT_ROOT = Path(__file__).resolve().parents[1]
WORKBOOK = PROJECT_ROOT / "workbook" / "Pokemon Battle Compass v1.2.xlsx"
DATA_DIR = PROJECT_ROOT / "data"


def sheet_to_records(workbook, sheet_name):
    sheet = workbook[sheet_name]

    headers = [
        sheet.cell(row=1, column=col).value
        for col in range(1, sheet.max_column + 1)
    ]

    records = []

    for row in range(2, sheet.max_row + 1):
        record = {}

        for col, header in enumerate(headers, start=1):
            record[header] = sheet.cell(row=row, column=col).value

        # Skip fully blank rows
        if any(value is not None for value in record.values()):
            records.append(record)

    return records


def export_json(records, output_file):
    output_path = DATA_DIR / output_file

    with open(output_path, "w", encoding="utf-8") as file:
        json.dump(records, file, indent=2)

    print(f"✓ Exported {len(records)} records to data/{output_file}")


wb = load_workbook(WORKBOOK, data_only=True)

team_data = sheet_to_records(wb, "Team Data")
movelist = sheet_to_records(wb, "Movelist")
ability_rules = sheet_to_records(wb, "Ability Rules")
items = sheet_to_records(wb, "Items")
opponents = sheet_to_records(wb, "Opponent")

# Keep workbook sheet naming for now where it represents actual app data.
export_json(team_data, "team_data.json")
export_json(movelist, "moves.json")
export_json(ability_rules, "ability_rules.json")
export_json(items, "items.json")
export_json(opponents, "opponents.json")

print("\nImport complete.")