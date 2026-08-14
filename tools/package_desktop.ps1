$ErrorActionPreference = "Stop"

$projectRoot = Split-Path -Parent $PSScriptRoot
$appName = "PokemonBattleCompass"

Set-Location $projectRoot

Write-Host "Pokemon Battle Compass - desktop package"
Write-Host "Project: $projectRoot"

$requiredPaths = @(
    ".\\flet_app.py",
    ".\\assets",
    ".\\assets\\icon_windows.ico",
    ".\\data",
    ".\\tools\\normalize_pokemon_sprites.py"
)

foreach ($path in $requiredPaths) {
    if (-not (Test-Path -Path $path)) {
        throw "Required packaging path not found: $path"
    }
}

Write-Host ""
Write-Host "Running PyInstaller..."

python -m PyInstaller flet_app.py --noconfirm --clean --onedir --windowed --name PokemonBattleCompass --icon "assets\\icon_windows.ico" --add-data "data;data"

if ($LASTEXITCODE -ne 0) {
    throw "PyInstaller failed with exit code $LASTEXITCODE."
}

Write-Host ""
Write-Host "Normalizing Pokemon sprites..."

python tools\\normalize_pokemon_sprites.py

if ($LASTEXITCODE -ne 0) {
    throw "Sprite normalization failed with exit code $LASTEXITCODE."
}

$packagedApp = Join-Path $projectRoot "dist\\PokemonBattleCompass"
$packagedInternal = Join-Path $packagedApp "_internal"
$packagedExe = Join-Path $packagedApp "PokemonBattleCompass.exe"
$packagedAssets = Join-Path $packagedInternal "assets"
$normalizedSprites = Join-Path $packagedAssets "runtime\\pokemon-gen8\\regular"

if (-not (Test-Path -Path $packagedInternal -PathType Container)) {
    throw "Expected packaged _internal directory not found: $packagedInternal"
}

Write-Host ""
Write-Host "Copying runtime assets..."
Write-Host "  $projectRoot\\assets"
Write-Host "  -> $packagedAssets"

Copy-Item -Path ".\\assets" -Destination $packagedInternal -Recurse -Force

if (-not (Test-Path -Path $packagedExe -PathType Leaf)) {
    throw "Packaged executable not found: $packagedExe"
}

if (-not (Test-Path -Path $normalizedSprites -PathType Container)) {
    throw "Normalized Pokemon sprites were not copied into the packaged app: $normalizedSprites"
}

Write-Host ""
Write-Host "SUCCESS: desktop package created at:"
Write-Host "  $packagedApp"
Write-Host ""
Write-Host "Executable:"
Write-Host "  $packagedExe"