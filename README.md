# Pokémon Battle Compass

Pokémon Battle Compass is a fan-made decision-support tool for **Pokémon Sword**.

It analyzes your current team against story opponents, recommends strong matchups, explains why they are strong, and helps track team progression throughout a playthrough.

The goal is not to solve Pokémon for you. It is a **compass, not a GPS**: useful guidance while still leaving room for challenge runs, theme teams, favorites, questionable strategic choices, and all the other things that make an actual playthrough fun.

## Current Version

**0.2.0 Beta**

The original Excel prototype and Streamlit migration have been retired. The active application is now built with **Flet** and runs as:

- a packaged Windows desktop application
- a browser-based web application

## Features

### Battle Compass

Select your starter, trainer battle, opponent, and current team to see:

- Recommended Pokémon
- Best move
- Matchup strength
- Defensive risk
- Other strong options
- Full team analysis
- Context-sensitive battle notes
- Support for many special move and ability interactions

The recommendation engine considers more than simple type effectiveness. It also evaluates stats, STAB, held items, abilities, move behavior, defensive matchups, likely OHKOs, and a growing collection of battle-specific mechanics.

### My Team

Build and maintain your current team with:

- Pokémon
- Gender
- Level
- Nature
- Ability
- Held item
- Stats
- Moves

Pokémon details include sprites, type information, stat visualization, move details, evolution guidance, and related reference information.

### My Journey

Track your Sword playthrough with:

- Badge progression
- Current objectives
- Pokémon acquisition targets
- Items, TMs, and TRs
- Galar map markers
- Team planning
- Save / backup / restore support

Objective availability follows story progression, so the app can distinguish between something that exists in the game and something you can actually obtain yet.

## Saving Your Progress

Pokémon Battle Compass stores Journey data locally on your device.

You can also export a backup and restore it later.

Because browser storage belongs to the browser/device you are using, data does not automatically synchronize between computers, phones, browsers, or browser profiles.

Backups are strongly recommended if you care about preserving a Journey.

## Windows Version

The Windows release is distributed as a packaged application.

Download the Windows release ZIP, extract the entire folder, and run:

`PokemonBattleCompass.exe`

Do not remove the `_internal` folder beside the executable. The application needs those files to run.

No installation is currently required.

## Web Version

The web version runs directly in a modern browser.

### Mobile note

On iPhone and iPad, use Pokémon Battle Compass **in Safari or Chrome as a normal browser site**.

Installing it to the Home Screen as a standalone Web App is not currently considered a supported configuration because Journey file import / Load does not work reliably in that mode.

## Current Scope

Pokémon Battle Compass currently targets:

**Pokémon Sword — Generation VIII**

Opponent data, acquisition guidance, progression logic, and recommendations are built around the Sword story.

Shield support may come later, but is not part of the current Beta.

## What the App Does Not Try to Do

Pokémon Battle Compass is intentionally not a full battle simulator.

It does not attempt to model every possible live battle state, including arbitrary:

- HP percentages
- stat stages
- field conditions
- turn-by-turn decision trees
- opponent AI behavior
- random damage rolls

The app focuses on practical pre-battle matchup guidance using the information a player can reasonably maintain without turning every fight into spreadsheet homework.

That would rather defeat the purpose.

## Development

The active application is built with:

- Python
- Flet
- Flet DataTable2
- PyInstaller
- Pillow

The battle engine is intentionally kept separate from the UI so recommendation logic can remain framework-independent.

### Run locally

From the project root:

```powershell
python flet_app.py