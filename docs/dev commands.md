## Terminal Commands and code for dev testing


# Restore Team Cameron (default .json team_data)
    In flet_app.py, Immediately after:

    await app_state.initialize()

    temporarily add:

    # TEMPORARY: Restore Team Cameron into Journey storage.
    await app_state.start_new_journey("Scorbunny")
    await app_state.save_team(
        reference_data["team_data"]
    )

# Normalize Textures
    python tools/normalize_texture_artwork.py --apply 


# Set up virtual environment
    Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
    .\.venv\Scripts\Activate.ps1

# Remove packaging files for repackaging
    Remove-Item ".\build" -Recurse -Force -ErrorAction SilentlyContinue
    Remove-Item ".\dist" -Recurse -Force -ErrorAction SilentlyContinue

# Package
   python tools\package_desktop.py
   
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
flet run --web --host 127.0.0.1 --port 51427 flet_app.py

python tools\publish_web.py
python -m http.server 8002 --directory dist-web (Desktop web)
http://localhost:8002

python -m http.server 8005 --bind 0.0.0.0 --directory dist-web (iPhone/mobile)

