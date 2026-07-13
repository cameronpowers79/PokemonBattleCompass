### Layout
- [x] Recommendation card.
- [x] Battle Snapshot card.
- [x] Other Strong Options (exclude recommended Pokémon).
- [x] Expandable Full Analysis.
- [x] Matchup Strength indicator.
- [x] Center title header
- [x] Move Best Move effectiveness banner so it stays near the move name rather than falling below the matchup strength indicator
- [x] Move Opponent selector to below the header divider so it only appears on the Battle Compass page
- [x] Adjust "Recommended Pokemon" font so it doesn't stack on Mobile
- [x] Add "Currently selected" information on the Compass screen, near "Opponent Pokemon" dropdown selector (above/beside)
- [x] Move Notes for "Other Strong Options" back inside the cards rather than floating below
- [x] Add box sprites to Other Strong Options.
- [x] Preserve Battle Compass selections when switching between pages.

### Battle Notes
- [x] Structured Battle Notes.
- [x] Render note categories with icons/colors.
- [x] Display Battle Notes as styled UI rather than plain text.

### Polish
- [x] Pokémon sprites.
- [x] Type badges.
- [x] Type colors.
- [x] Worst Incoming Move displays category (Physical/Special).
- [x] Typography:
  - Exo 2 (headers)
  - Aptos (body)
  - Bahnschrift (metrics)
- [x] Change active page selector color from red to blue
- [x] Info "link" from Why? to Full Analysis.
- [x] Application branding (logo & wordmark)
- [x] Extend branding colors to Recommended Pokemon card
- [ ] ♂/♀ icon immediately after the Pokémon name
- [ ] Tap/click move cards for full move details.
- [ ] Tap/click Ability and Held Item for descriptions.
- [ ] Optional: tap on the type badges to show weaknesses/resistances.
- [x] Add ⊕ indicator and interactive breakdown for item-boosted Move Scores.
- [x] Add custom application favicon.
- [x] Brighten Recommended Pokémon card accent/glow for mobile visibility.
- [x] Add held-item boost breakdown popup to Move Score.

### Architecture
- [x] Split app.py before it became a crime scene.
- [x] Centralize move metadata lookups.
- [x] Structured Battle Notes.
- [x] Implement sprite lookup layer.
- [x] Player-editable Team Data.
- [x] Add UI theme/constants module.
- [x] Continue separating UI from engine.

## Team Editing

- [x] Add editable Team Data screen.
- [x] Load current `team_data.json`.
- [x] Allow editing levels, stats, moves, ability, and held item.
- [x] Save updates back to `data/team_data.json`.
- [ ] Add backup/export option.
- [x] Add move dropdown validation.
- [ ] Add ability validation.
- [ ] Add held-item validation after the modeled item list is expanded.
- [x] Selected Pokémon detail panel.
- [x] Stat bars with numeric values.
- [x] Moveset display for selected Pokémon.
- [x] Add type color to moves in moveset display
- [x] Type badges in My Team view.
- [ ] Pokémon name dropdown/validation.
- [x] Improve Pokémon Details section layout.
- [ ] Create page section jumpto links and place them horizontally just below the header divider? 

## Sprite Support
- [ ] Build Pokémon option list from available sprite assets.
- [ ] Handle display-name cleanup for sprite slugs.
- [x] Evaluate larger sprite/icon source later; current Alpha uses lightweight PokéSprite box icons.
- [x] Gender/form sprite support.
- [x] Texture artwork fallback hierarchy (future expansion)
- [ ] Expand texture hierarchy for additional regional/forms as needed.

## Battle Selection

- [x] Order battles by BattleOrder.
- [x] Order opponent Pokémon by Slot.
- [x] Support starter-dependent trainer lineups.

## Texture Artwork

- [x] Implement automatic texture-to-sprite fallback.
- [x] Add Galar starter-line textures.
- [x] Add textures for Hop's Pokémon.
- [ ] Add textures for unique Pokémon in `opponents.json`.
- [ ] Add trainer artwork for the 21 trainers represented in `opponents.json`.
- [ ] Gradually expand texture coverage for player-selected Pokémon.

## Bugfixes
- [x] Fix null `Slot` values for Bede’s Ballonlea/Wyndon postgame battle.

## Documentation

- [ ] Refresh README with current screenshots.
- [ ] Add mobile screenshots.
- [ ] Document installation (local Python).
- [ ] Document Streamlit Cloud deployment.
- [ ] Add feature overview.
- [ ] Add known limitations.
- [ ] Add roadmap section.
- [ ] Create release notes template.
- [ ] Add animated GIF demonstrations of major features.

## Trainer's Guide

  ### Team Planning
  - [ ] Pokémon acquisition planner.
  - [ ] Earliest obtainable route/area.
  - [ ] Earliest obtainable level.
  - [ ] Version-exclusive indicators.
  - [ ] Planned team builder.

  ### Shopping & Preparation
  - [ ] TM/TR shopping checklist.
  - [ ] Held item shopping checklist.
  - [ ] Evolution item checklist.
  - [ ] Berry checklist.
  - [ ] Optional completion tracking.

  ### Progress Tracking
  - [ ] Gym progress tracker.
  - [ ] Badge progress.
  - [ ] Story milestone tracker.
  - [ ] Optional route completion tracker.

  ### Reference
  - [ ] Location lookup.
  - [ ] Evolution requirements.
  - [ ] Held item locations.
  - [ ] TM/TR locations.
  - [ ] NPC gift Pokémon.
  - [ ] Max Raid availability (optional).

  ### Held Item Guidance
- [ ] Recommend a modeled held item for the selected matchup.
- [ ] Compare current held item vs recommended item.
- [ ] Show estimated Move Score change from switching items.
- [ ] Distinguish offensive, defensive, and sustain recommendations.
- [ ] Explain why the item is being recommended.

  ### Future Ideas
  - [ ] Wild Area weather planner.
  - [ ] Watt vendor rotation helper.
  - [ ] Daily event tracker.
  - [ ] Save multiple planned runs.