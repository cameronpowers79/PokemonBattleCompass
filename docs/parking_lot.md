### Layout
- [x] Recommendation card.
- [x] Battle Snapshot card.
- [x] Other Strong Options (exclude recommended Pokémon).
- [x] Expandable Full Analysis.
- [x] Matchup Strength indicator.
- [x] Center title header
- [ ] Move Best Move effectiveness banner so it stays near the move name rather than falling below the matchup strength indicator
- [x] Move Opponent selector to below the header divider so it only appears on the Battle Compass page

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
- [ ] Info link from Why? to Full Analysis.

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
- [ ] Evaluate larger sprite/icon source later; current Alpha uses lightweight PokéSprite box icons.
- [ ] Gender/form sprite support.

## Battle Selection

- [x] Order battles by BattleOrder.
- [x] Order opponent Pokémon by Slot.
- [x] Support starter-dependent trainer lineups.