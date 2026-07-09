from pathlib import Path
from PIL import Image

SOURCE = Path("assets/raw/type_icons_sheet.png")
OUT_DIR = Path("assets/type_badges")
OUT_DIR.mkdir(parents=True, exist_ok=True)

types = [
    ["Normal", "Fighting", "Flying", "Poison", "Ground", "Rock"],
    ["Bug", "Ghost", "Steel", "Fire", "Water", "Grass"],
    ["Electric", "Psychic", "Ice", "Dragon", "Dark", "Fairy"],
]

img = Image.open(SOURCE)

badge_w = 201
badge_h = 45

x_positions = [0, 201, 402, 604, 805, 1006]
y_positions = [14, 59, 104]

for row_index, row in enumerate(types):
    for col_index, type_name in enumerate(row):
        x = x_positions[col_index]
        y = y_positions[row_index]

        badge = img.crop((x, y, x + badge_w, y + badge_h))
        badge.save(OUT_DIR / f"{type_name}.png")

print("Type badges extracted.")