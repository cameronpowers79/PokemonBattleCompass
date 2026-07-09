from pathlib import Path
from PIL import Image

SOURCE = Path("assets/raw/pokemon_icons_sheet.png")
OUT_DIR = Path("assets/sprites")

CELL_W = 26
CELL_H = 26
COLUMNS = 12

OUT_DIR.mkdir(parents=True, exist_ok=True)

sheet = Image.open(SOURCE).convert("RGBA")

sprite_number = 1

for y in range(0, sheet.height, CELL_H):
    for x in range(0, sheet.width, CELL_W):
        if x + CELL_W > sheet.width or y + CELL_H > sheet.height:
            continue

        sprite = sheet.crop((x, y, x + CELL_W, y + CELL_H))

        # Skip mostly empty cells.
        if sprite.getbbox() is None:
            continue

        sprite.save(OUT_DIR / f"{sprite_number:04d}.png")
        sprite_number += 1

print(f"Extracted {sprite_number - 1} sprites to {OUT_DIR}")