# Pokémon Battle Compass

Pokémon Battle Compass is a fan-made decision-support tool for **Pokémon Sword**.

It analyzes your current team against story opponents, recommends strong matchups, explains why they are strong, and helps track team progression throughout a playthrough.

The goal is not to solve Pokémon for you. It is a **compass, not a GPS**: useful guidance while still leaving room for challenge runs, theme teams, favorites, questionable strategic choices, and all the other things that make an actual playthrough fun.

## Current Version

**0.2.1 Beta**

The original Excel prototype and Streamlit migration have been retired. The active application is now built with **Flet** and runs as:

- a packaged Windows desktop application
- a browser-based web application
- an installable mobile/web app on supported devices

## Features

### Battle Compass

Select your starter, trainer battle, opponent, and current team to see:

- Recommended Pokémon
- Best move
- Matchup Strength
- Defensive risk
- Other strong options
- Full team analysis
- Context-sensitive Battle Notes
- Likely OHKO and survival guidance
- Support for many special move, held-item, and Ability interactions

The recommendation engine considers more than simple type effectiveness. It also evaluates stats, STAB, held items, Abilities, move behavior, defensive matchups, likely OHKOs, turn order, priority, and a growing collection of battle-specific mechanics.

Recommendations are intended as decision support, not commands. Sometimes the mathematically strongest matchup is exactly what you want. Sometimes you brought a haunted balloon because you felt like it. Both are valid approaches to Pokémon.

### My Team

Build and maintain your current and boxed Pokémon with the Team Editor:

- Pokémon
- Gender
- Level
- Nature
- Ability
- Held item
- Stats
- Moves

Battle Compass uses the information entered here for its calculations, so keeping your team data current matters. Update Pokémon after evolutions, move changes, held-item changes, major stat changes, or other meaningful build changes.

Pokémon Details provides a closer look at any current or boxed Pokémon, including artwork, types, stats, Nature effects, moves, held-item guidance, and evolution information.

### My Journey

Track and plan your Sword playthrough with:

- Badge progression
- Current Objectives
- Pokémon acquisition targets
- Item, TM, and TR objectives
- Acquisition availability
- Galar map markers
- Team Planner
- Encounter details
- Save / backup / restore support

Objective availability follows story progression, catch-level restrictions, important traversal requirements, weather restrictions, and other modeled acquisition gates.

The goal is to distinguish between **“this exists somewhere in Pokémon Sword”** and **“you can reasonably go get this now.”**

Pokémon acquisition data has been validated against the app’s progression rules, including special handling for trades, gifts, story encounters, Raid exceptions, and other acquisition methods that do not fit neatly into ordinary wild-encounter logic.

## How to Use It

A typical Battle Compass workflow looks like this:

1. Enter and maintain your Pokémon on **My Team**.
2. Use **Battle Compass** before important battles to review the recommended matchup and Full Analysis.
3. Keep your earned badges current on **My Journey**.
4. Use Current Objectives, the map, and Team Planner to see what becomes available next.
5. Update My Team when your Pokémon evolve, learn new moves, change items, or otherwise change meaningfully.
6. Export a Journey backup occasionally, because relying entirely on browser storage is an exciting lifestyle choice.

More detailed guidance is available on the in-app **About** page under **How to Use Battle Compass**.

## Saving Your Progress

Pokémon Battle Compass stores Journey data locally on your device.

You can also export a portable Journey backup and restore it later.

Because browser storage belongs to the browser/device you are using, Journey data does not automatically synchronize between computers, phones, browsers, or browser profiles.

Backups are strongly recommended if you care about preserving a Journey.

## Windows Version

The Windows release is distributed as a packaged application.

Download the Windows release ZIP, extract the entire folder, and run:

`PokemonBattleCompass.exe`

Do not remove the `_internal` folder beside the executable. The application needs those files to run.

No installation is currently required.

## Web Version

The web version runs directly in a modern browser.

It can also be installed as a standalone web app on supported devices.

### Mobile / PWA note

Pokémon Battle Compass has been tested as an installed Home Screen Web App on iPhone as well as in a normal mobile browser.

Journey storage, artwork, map features, and Journey import / load are supported in the current Beta build.

As with any locally stored web application, keeping an exported Journey backup is still strongly recommended.

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
- doubles-specific partner interactions
- full weather and terrain simulation
- turn-by-turn decision trees
- opponent AI behavior
- every random damage outcome
- every wonderfully strange edge case Game Freak has invented

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
flet run flet_app.py