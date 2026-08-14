from __future__ import annotations

import shutil
import subprocess
import sys
from pathlib import Path


APP_NAME = "PokemonBattleCompass"


def project_root() -> Path:
    return Path(__file__).resolve().parent.parent


def run(command: list[str], *, cwd: Path) -> None:
    printable = " ".join(
        f'"{part}"' if " " in part else part
        for part in command
    )
    print(f"\n> {printable}")
    subprocess.run(
        command,
        cwd=cwd,
        check=True,
    )


def copy_assets(
    assets: Path,
    packaged_internal: Path,
) -> None:
    """Copy the complete runtime asset tree beside the packaged app."""

    target = packaged_internal / "assets"

    print(
        "\nCopying runtime assets...\n"
        f"  {assets}\n"
        f"  -> {target}"
    )

    shutil.copytree(
        assets,
        target,
        dirs_exist_ok=True,
    )


def main() -> int:
    root = project_root()

    app_entry = root / "flet_app.py"
    assets = root / "assets"
    data = root / "data"
    icon = assets / "icon_windows.ico"

    normalizer = (
        root
        / "tools"
        / "normalize_pokemon_sprites.py"
    )

    dist_root = root / "dist"
    packaged_app = dist_root / APP_NAME
    packaged_internal = packaged_app / "_internal"
    packaged_exe = packaged_app / f"{APP_NAME}.exe"

    print("Pokémon Battle Compass — desktop package")
    print(f"Project: {root}")

    required_paths = (
        app_entry,
        assets,
        data,
        icon,
        normalizer,
    )

    missing = [
        path
        for path in required_paths
        if not path.exists()
    ]

    if missing:
        print(
            "\nERROR: required packaging files are missing:",
            file=sys.stderr,
        )
        for path in missing:
            print(
                f"  - {path}",
                file=sys.stderr,
            )
        return 1

    try:
        # Generate normalized Journey sprites before the asset tree is copied.
        run(
            [
                sys.executable,
                r"tools\normalize_pokemon_sprites.py",
            ],
            cwd=root,
        )

        # IMPORTANT:
        # Keep these PyInstaller arguments relative to the project root.
        # This intentionally mirrors the known-good manual PowerShell command.
        run(
            [
                sys.executable,
                "-m",
                "PyInstaller",
                "flet_app.py",
                "--noconfirm",
                "--clean",
                "--onedir",
                "--windowed",
                "--name",
                APP_NAME,
                "--icon",
                r"assets\icon_windows.ico",
                "--add-data",
                r"data;data",
            ],
            cwd=root,
        )

        if not packaged_internal.is_dir():
            raise FileNotFoundError(
                "PyInstaller completed, but the expected "
                f"_internal directory is missing: {packaged_internal}"
            )

        copy_assets(
            assets,
            packaged_internal,
        )

        if not packaged_exe.is_file():
            raise FileNotFoundError(
                f"Packaged executable not found: {packaged_exe}"
            )

        normalized_assets = (
            packaged_internal
            / "assets"
            / "runtime"
            / "pokemon-gen8"
            / "regular"
        )

        if not normalized_assets.is_dir():
            raise FileNotFoundError(
                "Normalized Pokémon sprites were not copied into "
                f"the packaged app: {normalized_assets}"
            )

        print(
            "\nSUCCESS: desktop package created at:\n"
            f"  {packaged_app}\n"
            "\nExecutable:\n"
            f"  {packaged_exe}"
        )
        return 0

    except subprocess.CalledProcessError as exc:
        print(
            f"\nERROR: packaging command failed with exit code "
            f"{exc.returncode}.",
            file=sys.stderr,
        )
        return exc.returncode or 1

    except Exception as exc:
        print(
            f"\nERROR: {exc}",
            file=sys.stderr,
        )
        return 1


if __name__ == "__main__":
    raise SystemExit(main())