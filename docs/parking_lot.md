### Layout
- [x] Recommendation card.
- [x] Battle Snapshot card.
- [x] Other Strong Options (exclude recommended Pokémon).
- [x] Expandable Full Analysis.
- [x] Matchup Strength indicator.

### Battle Notes
- [x] Structured Battle Notes.
- [x] Render note categories with icons/colors.
- [x] Display Battle Notes as styled UI rather than plain text.

### Polish
- [x] Pokémon sprites.
- [ ] Evaluate larger sprite/icon source later; current Alpha uses lightweight PokéSprite box icons.
- [x] Type badges.
- [x] Type colors.
- [x] Worst Incoming Move displays category (Physical/Special).
- [x] Typography:
  - Exo 2 (headers)
  - Aptos (body)
  - Bahnschrift (metrics)
- [ ] Info link from Why? to Full Analysis.
- [ ] Gender/form sprite support.

### Architecture
- [x] Split app.py before it became a crime scene.
- [x] Centralize move metadata lookups.
- [x] Structured Battle Notes.
- [x] Implement sprite lookup layer.
- [x] Player-editable Team Data.
- [ ] Add UI theme/constants module.
- [ ] Continue separating UI from engine.

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
- [ ] Build Pokémon option list from available sprite assets.
- [ ] Handle display-name cleanup for sprite slugs.