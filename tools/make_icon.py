from pathlib import Path
from PIL import Image

PROJECT_ROOT = Path(__file__).resolve().parents[1]

png = PROJECT_ROOT / "assets" / "icon_windows.png"
ico = PROJECT_ROOT / "assets" / "icon_windows.ico"

img = Image.open(png)

img.save(
    ico,
    format="ICO",
    sizes=[
        (16, 16),
        (32, 32),
        (48, 48),
        (64, 64),
        (128, 128),
        (256, 256),
    ],
)

print(f"Created {ico}")