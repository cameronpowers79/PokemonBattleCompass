## Terminal Commands and code for dev testing

# Normalize Textures
    python tools/normalize_texture_artwork.py --apply 


# Set up virtual environment
    Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
    .\.venv\Scripts\Activate.ps1

# Remove packaging files for repackaging
    Remove-Item ".\build" -Recurse -Force -ErrorAction SilentlyContinue
    Remove-Item ".\dist" -Recurse -Force -ErrorAction SilentlyContinue

# Package
   .\tools\package_desktop.ps1
   
    python -m PyInstaller flet_app.py `
    --noconfirm `
    --clean `
    --onedir `
    --windowed `
    --name PokemonBattleCompass `
    --icon "assets\icon_windows.ico" `
    --add-data "data;data"

    Copy-Item `
    ".\assets" `
    ".\dist\PokemonBattleCompass\_internal\" `
    -Recurse -Force

.\dist\PokemonBattleCompass\PokemonBattleCompass.exe

# Web App Dev Commands

python tools\publish_web.py
hf upload cameronpowers/pokemon-battle-compass "C:\PokemonBattleCompass\dist-web" . --repo-type=space --commit-message="Update Pokemon Battle Compass Beta"

python -m http.server 8002 --directory dist-web (Desktop web)
http://localhost:8002

python -m http.server 8005 --bind 0.0.0.0 --directory dist-web (iPhone/mobile)



Web address: https://cameronpowers-pokemon-battle-compass.static.hf.space/index.html
