# Pokémon Battle Compass — Parking Lot

# Migration / Platform

## Current Status

- [x] Freeze Streamlit Alpha as the reference implementation.
- [x] Tag Streamlit Alpha.
- [x] Create migration branch.
- [x] Restore `main` to the stable Streamlit Alpha.

## Desktop + PWA Migration

- [x] Select the replacement framework (Flet).
- [x] Build proof-of-concept.
- [x] Implement durable local storage.
- [x] Add first-use Journey onboarding.
- [ ] Implement autosave.
- [ ] Implement optional backup/export.
- [ ] Implement restore/import.
- [ ] Verify desktop packaging.
- [ ] Verify installable PWA.
- [ ] Verify offline behavior.
- [ ] Verify iPhone PWA behavior.
- [ ] Migrate Battle Compass.
- [ ] Migrate Trainer's Guide.
- [ ] Retire the Streamlit implementation.


---

## Layout

- [x] Recommendation card.
- [x] Battle Snapshot card.
- [x] Other Strong Options, excluding the recommended Pokémon.
- [ ] Permanently visible Full Analysis.
- [x] Matchup Strength indicator.
- [x] Center title header.
- [x] Keep Best Move effectiveness near the move name.
- [x] Keep the Opponent selector within the Battle Compass page.
- [x] Prevent “Recommended Pokémon” from stacking on mobile.
- [x] Add currently selected battle information near the Opponent selector.
- [x] Keep Other Strong Options notes inside their cards.
- [x] Add box sprites to Other Strong Options.
- [x] Preserve Battle Compass selections while switching views.
- [ ] Add jump link from Why? to Full Analysis.
- [ ] Recreate responsive desktop and PWA layouts in the new UI.
- [ ] Review Full Analysis behavior on narrow mobile screens.
- [ ] Look into sizing down the team editing table in My Team for Mobile (browser may do this for us?)
- [ ] Freeze "Pokemon" column in My Team editor?
- [ ] Add move effectiveness to Other Strong Options cards

---

## Battle Notes

- [x] Structured Battle Notes.
- [x] Render note categories with icons and colors.
- [x] Display Battle Notes as styled UI rather than plain text.
- [ ] Preserve structured notes as framework-independent engine output.
- [ ] Recreate note presentation in the new desktop/PWA UI.

---

## Polish and Interaction

- [x] Pokémon sprites.
- [x] Type badges.
- [x] Type colors.
- [x] Worst Incoming Move displays category.
- [x] Typography:
  - Exo 2 for headers.
  - Aptos for body text.
  - Bahnschrift for metrics.
- [x] Blue active-page selector.
- [x] Application branding: logo and wordmark.
- [x] Extend branding colors to the Recommendation card.
- [x] Brighten Recommendation card accent/glow for mobile.
- [x] Custom application favicon.
- [x] Held-item boost indicator and score breakdown popover.
- [x] Add ♂/♀ immediately after Pokémon names.
- [x] Reduce the size of the ♂/♀ gender symbols slightly.
- [x] Reuse My Team’s move-card visual language during onboarding.
- [ ] Tap or click move cards for full move details.
- [ ] Tap or click Ability and Held Item for descriptions.
- [ ] Optional: tap type badges to show weaknesses and resistances.
- [ ] Add held-item sprites to the boosted-attack popover.
- [ ] Recreate branding, typography, cards, and interactions in the new UI.
- [ ] Add desktop-specific window and scaling polish.
- [ ] Add PWA-specific mobile polish.
- [ ] Ensure Matchup Strength text matches the highlighted color in the graphic
- [ ] Show an empty-state message in Other Strong Options when fewer than two team members are available. "Catch a few more Pokémon! As your team grows, your other strongest matchup recommendations will appear here."

---

## Architecture

- [x] Split `app.py` before it became a crime scene.
- [x] Centralize move metadata lookups.
- [x] Structured Battle Notes.
- [x] Implement sprite lookup layer.
- [x] Player-editable Team Data.
- [x] Add UI theme/constants module.
- [x] Continue separating UI from engine.
- [ ] Keep `engine/` framework-independent.
- [x] Separate persistent user data from bundled reference data.
- [ ] Create a shared storage interface for desktop and PWA.
- [x] Add save-data schema versioning.
- [ ] Add save-data validation and migration support.
- [ ] Add automatic recovery from interrupted writes.
- [ ] Add lightweight automated tests for core calculations.
- [ ] Keep the battle engine UI-framework agnostic.

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
- [ ] Add automatic saving after confirmed edits.
- [ ] Add optional manual backup/export.
- [ ] Add restore/import.
- [ ] Add ability validation.
- [ ] Add held-item validation after the modeled item list expands.
- [ ] Add Pokémon name dropdown and validation.
- [ ] Add clear “new team” and “reset team” actions.
- [ ] Add confirmation before destructive actions.
- [ ] Add multiple teams or save slots.
- [ ] Add page or section jump navigation where useful.
- [ ] Build Pokémon option list from available sprite assets.

---

## Sprite Support

- [x] Use lightweight PokéSprite box icons for the Alpha.
- [x] Gender and form sprite support.
- [x] Texture artwork fallback hierarchy.
- [ ] Handle display-name cleanup for sprite slugs.
- [ ] Expand the texture hierarchy for regional forms and other variants.
- [ ] Preserve sprite lookup as framework-independent logic.
- [ ] Verify sprite packaging in the desktop build.
- [ ] Verify sprite caching and offline use in the PWA.

---

## Battle Selection

- [x] Order battles by `BattleOrder`.
- [x] Order opponent Pokémon by `Slot`.
- [x] Support starter-dependent trainer lineups.
- [ ] Preserve battle selections locally between launches.
- [ ] Add optional recent-battle history.

---

## Texture and Trainer Artwork

- [x] Automatic texture-to-sprite fallback.
- [x] Galar starter-line textures.
- [x] Textures for Hop’s Pokémon.
- [ ] Add textures for unique Pokémon in `opponents.json`.
- [ ] Add trainer artwork for the 21 represented trainers.
- [ ] Gradually expand texture coverage for player-selected Pokémon.
- [ ] Package artwork efficiently for desktop.
- [ ] Cache artwork for offline PWA use.

---

## Modeled Items and Guidance

- [ ] Expand the modeled held-item list.
- [ ] Add held-item data validation.
- [ ] Recommend a modeled held item for the selected matchup.
- [ ] Compare the current item with the recommended item.
- [ ] Show estimated Move Score change from switching.
- [ ] Distinguish offensive, defensive, and sustain recommendations.
- [ ] Explain why the item is recommended.
- [ ] Add held-item sprites and descriptions.

---

## Bugfixes and Stability

- [x] Fix null `Slot` values for Bede’s Ballonlea/Wyndon postgame battle.
- [ ] Add validation for incomplete Pokémon records.
- [ ] Add graceful handling for empty teams.
- [ ] Add graceful handling for missing assets.
- [ ] Add user-facing error recovery instead of raw exceptions.
- [ ] Add logging suitable for standalone and PWA builds.
- [ ] Test multiple simultaneous PWA users.
- [ ] Test suspend/resume behavior on iOS.
- [ ] Test offline startup and reconnection.
- [ ] Test corrupted or outdated save files.

---

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

---

# Trainer's Guide

## Team Planning

- [ ] Pokémon acquisition planner.
- [ ] Earliest obtainable route or area.
- [ ] Earliest obtainable level.
- [ ] Version-exclusive indicators.
- [ ] Planned team builder.
- [ ] Save multiple planned runs.

## Shopping and Preparation

- [ ] TM/TR shopping checklist.
- [ ] Held-item shopping checklist.
- [ ] Evolution-item checklist.
- [ ] Berry checklist.
- [ ] Optional completion tracking.

## Progress Tracking

- [ ] Gym progress tracker.
- [ ] Badge progress.
- [ ] Story milestone tracker.
- [ ] Optional route-completion tracker.

## Reference

- [ ] Location lookup.
- [ ] Evolution requirements.
- [ ] Held-item locations.
- [ ] TM/TR locations.
- [ ] NPC gift Pokémon.
- [ ] Optional Max Raid availability.

## Future Ideas

- [ ] Wild Area weather planner.
- [ ] Watt vendor rotation helper.
- [ ] Daily event tracker.
- [ ] Optional battle history / battle journal.