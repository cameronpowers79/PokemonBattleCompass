# Pokémon Battle Compass — Parking Lot

# Migration / Platform

## Current Status

- [x] Freeze Streamlit Alpha as the reference implementation.
- [x] Tag Streamlit Alpha.
- [x] Create migration branch.
- [x] Restore `main` to the stable Streamlit Alpha.
- [x] Remove retired Streamlit UI and obsolete migration/reference artifacts from the active Flet branch.

## Data Quality

- [x] Audit move metadata for missing or incorrect mechanics.

Audit zero/conditional-power opponent moves and eliminate false immunity results.

Model Foul Play using the target's Attack.

Model Gyro Ball and Electro Ball dynamic power from Speed.

Model deterministic fixed-damage moves (Night Shade, Seismic Toss, Dragon Rage, Sonic Boom).

Model Freeze-Dry and Flying Press special effectiveness.

Model Shell Side Arm and Photon Geyser category/ability behavior.

## Desktop + PWA Migration

- [x] Select the replacement framework (Flet).
- [x] Build proof-of-concept.
- [x] Implement durable local storage.
- [x] Add first-use Journey onboarding.
- [x] Retain explicit team saving as a proofreading checkpoint.
- [x] Implement optional backup/export.
- [x] Implement restore/import.
- [x] Verify desktop packaging.
- [ ] Verify installable PWA.
- [ ] Verify offline behavior.
- [ ] Verify iPhone PWA behavior.
- [x] Migrate Battle Compass.
- [x] Migrate Trainer's Guide.
- [x] Retire the Streamlit implementation.

---

## Layout

- [x] Recommendation card.
- [x] Battle Snapshot card.
- [x] Other Strong Options, excluding the recommended Pokémon.
- [x] Matchup Strength indicator.
- [x] Center title header.
- [x] Keep Best Move effectiveness near the move name.
- [x] Keep the Opponent selector within the Battle Compass page.
- [x] Prevent “Recommended Pokémon” from stacking on mobile.
- [x] Add currently selected battle information near the Opponent selector.
- [x] Keep Other Strong Options notes inside their cards.
- [x] Add box sprites to Other Strong Options.
- [x] Preserve Battle Compass selections while switching views.
- [x] Permanently visible Full Analysis.
- [x] Add jump link from Why? to Full Analysis.
- [x] Recreate responsive desktop and PWA layouts in the new UI.
- [x] Review Full Analysis behavior on narrow mobile screens.
- [x] Improve My Team table usability on narrow/mobile layouts.
- [x] Freeze the Pokémon column in the My Team editor.
- [x] Add move effectiveness to Other Strong Options cards.
- [x] Freeze the Pokémon/item identifier columns in My Journey tables.
- [x] Preserve Checklist horizontal scroll position when progress changes.

---

## Battle Notes

- [x] Structured Battle Notes.
- [x] Render note categories with icons and colors.
- [x] Display Battle Notes as styled UI rather than plain text.
- [x] Preserve structured notes as framework-independent engine output.
- [x] Recreate note presentation in the new desktop/PWA UI.

---

## Polish and Interaction

- [x] Pokémon sprites.
- [x] Type badges.
- [x] Type colors.
- [x] Worst Incoming Move displays category.
- [x] Typography:

Exo 2 SemiBold for structural headers and main navigation.

Exo 2 ExtraBold for Pokémon identity names.

Yu Gothic UI for body/interface text.

Centralized semantic text-size hierarchy in ui/theme.py.
- [x] Blue active-page selector.
- [x] Application branding: logo and wordmark.
- [x] Extend branding colors to the Recommendation card.
- [x] Brighten Recommendation card accent/glow for mobile.
- [x] Custom application favicon.
- [x] Held-item boost indicator and score breakdown popover.
- [x] Add ♂/♀ immediately after Pokémon names.
- [x] Reduce the size of the ♂/♀ gender symbols slightly.
- [x] Reuse My Team’s move-card visual language during onboarding.
- [x] Tap or click move cards for full move details.
- [x] Tap or click Ability and Held Item for descriptions.
- [x] Add compact opponent moveset to the Opponent card.
- [x] Improve move details popup with plain-language effect descriptions.
- [x] Add Additional Navigation Aids section to move details.
- [x] Ensure Matchup Strength text matches the highlighted color in the graphic.
- [x] Show an empty-state message in Other Strong Options when fewer than two team members are available. "Catch a few more Pokémon! As your team grows, your other strongest matchup recommendations will appear here."
- [x] Reuse My Team's move-card visual language for opponent movesets.
- [x] Optional: tap type badges to show weaknesses and resistances.
- [x] Add held-item sprites to the boosted-attack popover.
- [x] Recreate branding, typography, cards, and interactions in the new UI.
- [x] Add Exo 2 branding hierarchy across page headers, navigation, and Pokémon names.
- [x] Add Incense held-item sprite resolution.
- [x] Clean up offensive/defensive 4× effectiveness wording.
- [ ] Add desktop-specific window and scaling polish.
- [ ] Add PWA-specific mobile polish.
- [ ] Complete plain-language move effect translations.
    - Healing (Giga Drain, Drain Punch, etc.)
    - Alternate damage calculations (Psyshock, Body Press, Foul Play, etc.)
    - Stat stage changes
    - Remaining activation conditions

---

## Architecture

- [x] Split `app.py` before it became a crime scene.
- [x] Centralize move metadata lookups.
- [x] Structured Battle Notes.
- [x] Implement sprite lookup layer.
- [x] Player-editable Team Data.
- [x] Add UI theme/constants module.
- [x] Continue separating UI from engine.
- [x] Keep `engine/` framework-independent.
- [x] Separate persistent user data from bundled reference data.
- [ ] Create a shared storage interface for desktop and PWA.
- [x] Add save-data schema versioning.
- [ ] Add save-data validation and migration support.
- [x] Add automatic recovery from interrupted writes.
- [ ] Add lightweight automated tests for core calculations.
- [x] Keep the battle engine UI-framework agnostic.

---

## Team Management

- [x] Editable Team Data screen.
- [x] Load current team data.
- [x] Allow editing levels, stats, moves, Ability, and Held Item.
- [x] Move dropdown validation.
- [x] Selected Pokémon detail panel.
- [x] Stat bars with numeric values.
- [x] Moveset display.
- [x] Type-colored move cards.
- [x] Type badges in My Team.
- [x] Improved Pokémon Details layout.
- [x] Replace shared `team_data.json` writes with durable per-user local storage.
- [x] Create a starter Journey with game-accurate Level 5 defaults, Ability, and starting moves.
- [x] Preserve the current Journey while previewing or abandoning new-Journey onboarding.
- [x] Replace the current Journey only after onboarding is completed and confirmed.
- [x] Resume the last-used team automatically.
- [x] Add starter-change confirmation dialog with Explore and Start New Journey options.
- [x] Add unsaved-change awareness and confirmation before leaving My Team.
- [x] Allow adding Pokémon during an active Journey.
- [x] Add Box / Release Pokémon workflow.
- [x] Add guidance beside starter selector explaining how to begin a new Journey.
- [x] Add optional manual backup/export.
- [x] Add restore/import.
- [x] Add ability validation.
- [x] Add held-item validation after the modeled item list expands.
- [x] Add Pokémon name dropdown and validation.
- [x] Add clear “new team” and “reset team” actions. (Not sure this is needed since the explanation helper for choosing a new starter has been implemented)
- [x] Add confirmation before destructive actions.
- [x] Add multiple teams or save slots. (Not needed; user can just export/load)
- [x] Add page or section jump navigation where useful.
- [x] Build Pokémon option list from available sprite assets.
- [x] Make Type 1 / Type 2 read-only and populate them from Journey Pokémon data.
- [x] Add Enter/Next navigation across numeric stat fields.
- [x] Migrate My Team editor to DataTable2 with a frozen Pokémon column.
- [x] Keep My Team helper text visible while horizontally scrolling.

---

## Sprite Support

- [x] Use lightweight PokéSprite box icons for the Alpha.
- [x] Gender and form sprite support.
- [x] Texture artwork fallback hierarchy.
- [ ] Handle display-name cleanup for sprite slugs.
- [ ] Expand the texture hierarchy for regional forms and other variants.
- [ ] Preserve sprite lookup as framework-independent logic.
- [x] Verify sprite packaging in the desktop build.
- [ ] Verify sprite caching and offline use in the PWA.

---

## Battle Selection

- [x] Order battles by `BattleOrder`.
- [x] Order opponent Pokémon by `Slot`.
- [x] Support starter-dependent trainer lineups.
- [x] Preserve battle selections locally between launches.
- [x] Add optional recent-battle history. (removed because we are not saving results or anything else worth going back to)

---

## Texture and Trainer Artwork

- [x] Automatic texture-to-sprite fallback.
- [x] Galar starter-line textures.
- [x] Textures for Hop’s Pokémon.
- [x] Add textures for unique Pokémon in `opponents.json`.
- [x] Add trainer artwork for the 21 represented trainers.
- [ ] Gradually expand texture coverage for player-selected Pokémon.
- [ ] Package artwork efficiently for desktop.
- [ ] Cache artwork for offline PWA use.

---

## Modeled Items and Guidance

- [x] Expand the modeled held-item list.
- [x] Add held-item data validation.
- [x] Recommend a modeled held item for the selected matchup.
- [x] Compare the current item with the recommended item.
- [x] Show estimated Move Score change from switching. (Unnecessary, user can model by simply "giving" the item in the Compass and checking the Compass)
- [x] Distinguish offensive, defensive, and sustain recommendations. (Unnecessary; the nature is in the description)
- [x] Explain why the item is recommended.
- [x] Add held-item sprites and descriptions.

---

## Bugfixes and Stability

- [x] Fix null `Slot` values for Bede’s Ballonlea/Wyndon postgame battle.
- [x] Prevent incomplete or status-only Pokémon from bricking the Battle Compass.
- [ ] Add validation for incomplete Pokémon records.
- [x] Add graceful handling for empty teams.
- [ ] Add graceful handling for missing assets.
- [ ] Add user-facing error recovery instead of raw exceptions.
- [ ] Add logging suitable for standalone and PWA builds.
- [ ] Test multiple simultaneous PWA users.
- [ ] Test suspend/resume behavior on iOS.
- [ ] Test offline startup and reconnection.
- [x] Test corrupted Journey save recovery.
- [ ] Test outdated save migration.

## Documentation

- [ ] Rewrite README for the desktop/PWA architecture.
- [ ] Add current desktop screenshots.
- [ ] Add mobile/PWA screenshots.
- [ ] Add feature overview.
- [ ] Add installation instructions for the standalone build.
- [ ] Add PWA installation instructions.
- [ ] Explain autosave, local storage, backup, and restore behavior.
- [ ] Add known limitations.
- [ ] Add roadmap section.
- [ ] Create release-notes template.
- [ ] Add animated demonstrations of major features.
- [ ] Document the Streamlit Alpha as the original reference implementation.
- [ ] Document the known iOS/Safari favicon limitation in the Alpha.
- [ ] Add fan-project and intellectual-property disclaimer.
- [ ] Architecture overview.

# My Journey

## Team Planning

- [x] Pokémon acquisition planner.
- [x] Earliest obtainable route or area.
- [x] Earliest obtainable level.
- [ ] Version-exclusive indicators.
- [x] Planned team builder.
- [x] Save multiple planned runs. (Export/Load does this)
- [x] Gate Pokémon availability with the shared required_badge progression rule.
- [x] Add Hide Obtained Pokémon filter.

## Shopping and Preparation

- [x] TM/TR shopping checklist.
- [x] Held-item shopping checklist.
- [x] Evolution-item checklist.
- [x] Berry checklist. (Removed; unnecessary)
- [x] Optional completion tracking.
- [x] Add Hide Obtained Items filter.
- [x] Preserve checklist scroll position while marking objectives complete.

## Progress Tracking

- [x] Gym progress tracker.
- [x] Badge progress.
- [x] Use Badge Tracker as the single progression source of truth for objective availability.
- [x] Add persistent map markers with select-once / move-to-marker-on-second-tap behavior.
- [x] Story milestone tracker. (not needed)
- [x] Optional route-completion tracker. (not needed)

## Reference

- [x] Location lookup.
- [x] Evolution requirements.
- [x] Held-item locations.
- [x] TM/TR locations.
- [x] NPC gift Pokémon.
- [x] Optional Max Raid availability.

## Future Ideas

- [ ] Pokemon Movepool Validation
- [ ] Add Shield support