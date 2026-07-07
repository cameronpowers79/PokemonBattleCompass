import json
from pathlib import Path
from openpyxl import load_workbook

PROJECT_ROOT = Path(__file__).resolve().parents[1]
WORKBOOK = PROJECT_ROOT / "workbook" / "Pokemon Battle Compass v1.2.xlsx"
OUTPUT_FILE = PROJECT_ROOT / "data" / "team_data.json"

SHEET_TO_EXPORT = "Team Data"

wb = load_workbook(WORKBOOK, data_only=True)
sheet = wb[SHEET_TO_EXPORT]

headers = [
    sheet.cell(row=1, column=col).value
    for col in range(1, sheet.max_column + 1)
]

rows = []

for row in range(2, sheet.max_row + 1):
    record = {}

    for col, header in enumerate(headers, start=1):
        record[header] = sheet.cell(row=row, column=col).value

    if record.get("Pokemon"):
        rows.append(record)

with open(OUTPUT_FILE, "w", encoding="utf-8") as file:
    json.dump(rows, file, indent=2)

print(f"Exported {len(rows)} records from {SHEET_TO_EXPORT} to:")
print(OUTPUT_FILE)