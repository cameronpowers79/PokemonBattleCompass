from __future__ import annotations

import shutil
import subprocess
import sys
import tarfile
from collections import Counter
from pathlib import Path

MAX_APP_TAR_BYTES = 10 * 1024 * 1024  # 10 MiB

STAGE_NAME = ".web-stage"
OUTPUT_NAME = "dist-web"
BACKUP_NAME = ".dist-web-backup"

ROOT_FILES = (
    "flet_app.py",
    "__init__.py",
    "requirements.txt",
    "pyproject.toml",
)

SOURCE_DIRS = (
    "engine",
    "ui",
    "data",
)

WEB_ROOT_FILES = (
    "import.html",
)

FORBIDDEN_ARCHIVE_ROOTS = {
    ".git",
    ".venv",
    "build",
    "dist",
    "dist-web",
    "dist-web-offline",
}


def project_root() -> Path:
    return Path(__file__).resolve().parent.parent


def run(command: list[str], *, cwd: Path) -> None:
    printable = " ".join(f'"{part}"' if " " in part else part for part in command)
    print(f"\n> {printable}")
    subprocess.run(command, cwd=cwd, check=True)


def remove_path(path: Path) -> None:
    if not path.exists():
        return
    if path.is_dir():
        shutil.rmtree(path)
    else:
        path.unlink()


def copy_runtime_files(root: Path, stage: Path) -> None:
    print("\nStaging runtime files...")

    for name in ROOT_FILES:
        source = root / name
        if not source.exists():
            raise FileNotFoundError(f"Required file not found: {source}")
        shutil.copy2(source, stage / name)
        print(f"  + {name}")

    for name in SOURCE_DIRS:
        source = root / name
        if not source.is_dir():
            raise FileNotFoundError(f"Required directory not found: {source}")
        shutil.copytree(source, stage / name)
        print(f"  + {name}/")


def copy_web_root_files(
    root: Path,
    staged_output: Path,
) -> None:
    """Copy static helper files beside the generated Flet web shell."""

    for name in WEB_ROOT_FILES:
        source = root / name
        if not source.is_file():
            raise FileNotFoundError(
                f"Required web root file not found: {source}"
            )

        shutil.copy2(
            source,
            staged_output / name,
        )
        print(f"  + web root: {name}")


def copy_web_branding(
    root: Path,
    staged_output: Path,
) -> None:
    """Overwrite Flet's generated PWA/mobile branding with app branding."""

    branding_root = (
        root
        / "assets"
        / "web_branding"
    )
    branding_icons = (
        branding_root
        / "icons"
    )
    generated_icons_dir = (
        staged_output
        / "icons"
    )

    if not branding_icons.is_dir():
        raise FileNotFoundError(
            f"Web branding icon directory not found: {branding_icons}"
        )

    generated_icons_dir.mkdir(
        parents=True,
        exist_ok=True,
    )

    required_icons = (
        "apple-touch-icon-192.png",
        "icon-192.png",
        "icon-512.png",
        "icon-maskable-192.png",
        "icon-maskable-512.png",
        "loading-animation.png",
    )

    for name in required_icons:
        source = branding_icons / name

        if not source.is_file():
            raise FileNotFoundError(
                f"Required web branding icon not found: {source}"
            )

        target = generated_icons_dir / name
        shutil.copy2(source, target)
        print(f"  + branded web icon: icons/{name}")

    favicon_source = branding_root / "favicon.png"
    favicon_target = staged_output / "favicon.png"

    if not favicon_source.is_file():
        raise FileNotFoundError(
            f"Required branded favicon not found: {favicon_source}"
        )

    shutil.copy2(
        favicon_source,
        favicon_target,
    )
    print("  + branded web favicon: favicon.png")


def validate_archive(app_tar: Path) -> tuple[int, int, Counter[str]]:
    if not app_tar.is_file():
        raise FileNotFoundError(
            f"Publish completed but app archive is missing: {app_tar}"
        )

    size = app_tar.stat().st_size
    if size > MAX_APP_TAR_BYTES:
        raise RuntimeError(
            f"app.tar.gz is unexpectedly large: {size:,} bytes "
            f"({size / 1024 / 1024:.2f} MiB). "
            "Refusing to replace the existing dist-web."
        )

    roots: Counter[str] = Counter()
    member_count = 0

    with tarfile.open(app_tar, "r:gz") as archive:
        for member in archive.getmembers():
            name = member.name.lstrip("./")
            if not name:
                continue
            member_count += 1
            root_name = name.split("/", 1)[0]
            roots[root_name] += 1

    bad_roots = sorted(FORBIDDEN_ARCHIVE_ROOTS.intersection(roots))
    if bad_roots:
        raise RuntimeError(
            "Unexpected generated/development directories were packaged into "
            f"app.tar.gz: {', '.join(bad_roots)}. "
            "Refusing to replace the existing dist-web."
        )

    return size, member_count, roots


def replace_output(root: Path, staged_output: Path) -> None:
    output = root / OUTPUT_NAME
    backup = root / BACKUP_NAME

    remove_path(backup)

    if output.exists():
        print(f"\nTemporarily preserving existing {OUTPUT_NAME}/...")
        output.rename(backup)

    try:
        staged_output.rename(output)
    except Exception:
        if backup.exists() and not output.exists():
            backup.rename(output)
        raise
    else:
        remove_path(backup)


def main() -> int:
    root = project_root()
    stage = root / STAGE_NAME
    staged_output = stage / OUTPUT_NAME
    assets = root / "assets"
    manifest_generator = root / "tools" / "generate_asset_manifest.py"
    sprite_normalizer = root / "tools" / "normalize_pokemon_sprites.py"
    texture_normalizer = root / "tools" / "normalize_texture_artwork.py"
    branding_generator = root / "tools" / "generate_web_branding.py"

    print("Pokémon Battle Compass — clean static web publish")
    print(f"Project: {root}")

    if not assets.is_dir():
        print(f"\nERROR: assets directory not found: {assets}", file=sys.stderr)
        return 1

    for required_tool in (
        sprite_normalizer,
        texture_normalizer,
        manifest_generator,
        branding_generator,
    ):
        if not required_tool.is_file():
            print(
                f"\nERROR: required publish tool not found: {required_tool}",
                file=sys.stderr,
            )
            return 1

    remove_path(stage)

    try:
        run([sys.executable, str(sprite_normalizer)], cwd=root)
        run([sys.executable, str(texture_normalizer), "--apply"], cwd=root)
        run([sys.executable, str(branding_generator)], cwd=root)
        run([sys.executable, str(manifest_generator)], cwd=root)

        stage.mkdir(parents=True)
        copy_runtime_files(root, stage)

        run(
            [
                sys.executable,
                "-m",
                "flet.cli",
                "publish",
                str(stage / "flet_app.py"),
                "--assets",
                str(assets),
                "--distpath",
                OUTPUT_NAME,
            ],
            cwd=root,
        )

        runtime_asset_dirs = [
            "type_badges",
            "badges",
            "raw/pokesprite/pokemon-gen8/regular",
            "fonts",
            "runtime/pokemon-gen8/regular",
        ]

        for relative_dir in runtime_asset_dirs:
            source_dir = assets / relative_dir
            target_dir = staged_output / relative_dir

            if source_dir.is_dir():
                shutil.copytree(
                    source_dir,
                    target_dir,
                    dirs_exist_ok=True,
                )

        runtime_asset_files = [
            "raw/BattleCompassLogo.png",
            "raw/WordMarkLogoBlock.png",
            "Galar_Map_Base.png",
        ]

        for relative_file in runtime_asset_files:
            source_file = assets / relative_file
            target_file = staged_output / relative_file

            if not source_file.is_file():
                raise FileNotFoundError(
                    f"Runtime asset not found: {source_file}"
                )

            target_file.parent.mkdir(
                parents=True,
                exist_ok=True,
            )

            shutil.copy2(
                source_file,
                target_file,
            )

            print(
                "  + runtime asset: "
                f"{source_file.relative_to(assets)} "
                f"-> {target_file.relative_to(staged_output)}"
            )

        item_assets_source = assets / "raw" / "pokesprite" / "items"
        item_assets_target = staged_output / "raw" / "pokesprite" / "items"

        if not item_assets_source.is_dir():
            raise FileNotFoundError(
                f"PokéSprite item assets not found: {item_assets_source}"
            )

        shutil.copytree(
            item_assets_source,
            item_assets_target,
            dirs_exist_ok=True,
        )
        print(
            "  + item assets: "
            f"{item_assets_source.relative_to(assets)} "
            f"-> {item_assets_target.relative_to(staged_output)}"
        )

        dawn_stone = (
            item_assets_target
            / "evo-item"
            / "dawn-stone.png"
        )
        if not dawn_stone.is_file():
            raise FileNotFoundError(
                "Runtime item asset verification failed: "
                f"{dawn_stone}"
            )

        copy_web_root_files(
            root,
            staged_output,
        )

        # Flet generates defaults every publish; overwrite them last.
        copy_web_branding(
            root,
            staged_output,
        )

        app_tar = staged_output / "app.tar.gz"
        size, member_count, roots = validate_archive(app_tar)

        print("\nArchive sanity check passed:")
        print(f"  app.tar.gz: {size:,} bytes ({size / 1024:.1f} KiB)")
        print(f"  members:    {member_count}")
        print("  top-level:")
        for name, count in roots.most_common():
            print(f"    {count:>4}  {name}")

        replace_output(root, staged_output)

        print(f"\nSUCCESS: clean web build published to {root / OUTPUT_NAME}")
        print(
            "\nDesktop test:\n"
            "  python -m http.server 8002 --directory dist-web\n"
            "\nPhone/LAN test:\n"
            "  python -m http.server 8005 --bind 0.0.0.0 --directory dist-web"
        )
        return 0

    except subprocess.CalledProcessError as exc:
        print(
            f"\nERROR: command failed with exit code {exc.returncode}. "
            f"Existing {OUTPUT_NAME}/ was left unchanged.",
            file=sys.stderr,
        )
        return exc.returncode or 1
    except Exception as exc:
        print(
            f"\nERROR: {exc}\nExisting {OUTPUT_NAME}/ was left unchanged.",
            file=sys.stderr,
        )
        return 1
    finally:
        remove_path(stage)


if __name__ == "__main__":
    raise SystemExit(main())