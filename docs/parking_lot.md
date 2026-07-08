# Pokémon Battle Compass Parking Lot

---

## Design Principles

- Advice first. Analysis second. Calculations third.
- Explain the recommendation, not the game.
- Battle Compass is a compass, not a GPS.
- Write for experienced story-mode players.
- Be transparent without being overwhelming.
- Every calculation should answer a player question.

## Engine Parity

### Notes / Why
- [x] Replace placeholder OHKO Notes thresholds with workbook HP-aware logic.
- [x] Port workbook-derived Why? explanation logic.
- [x] Refine Why? durability wording for immunity/resistance matchups.
- [x] Body Press opportunity notes.
- [x] Status-boosted Hex / Venoshock notes.
- [x] Structured Battle Notes framework.
- [ ] Compose richer Why? explanations from multiple contributing factors.

### Mechanics
- [x] Flash Fire immunity.
- [x] Body Press uses DEF.
- [x] Psyshock / Psystrike / Secret Sword use target DEF.
- [x] Technician / low-power move boost.
- [x] Contact-triggered tactical notes.
- [x] Priority move framework.
- [x] Tactical ability framework.
- [ ] Validate remaining ActivationCondition mechanics.
- [ ] Validate remaining DamageMethod mechanics.

---

## Alpha UI

- [x] Build Alpha prototype.
- [x] Promote Alpha to main app.

### Layout

- [ ] Recommendation card.
- [ ] Battle Snapshot card.
- [ ] Other Strong Options (exclude recommended Pokémon).
- [ ] Expandable Full Analysis.
- [ ] Matchup Strength indicator.

### Battle Notes

- [x] Structured Battle Notes.
- [ ] Render note categories with icons/colors.
- [ ] Display Battle Notes as styled UI rather than plain text.

### Polish

- [ ] Pokémon sprites.
- [ ] Type badges.
- [ ] Type colors.
- [ ] Stat data bars with numeric values.
- [ ] Worst Incoming Move displays category (Physical/Special).
- [ ] Info link from Why? to Full Analysis.
- [ ] Typography:
  - Exo 2 (headers)
  - Aptos (body)
  - Bahnschrift (metrics)

---

## Documentation

- [ ] About Battle Compass.
- [ ] Explain recommendation methodology.
- [ ] Explain Matchup Strength.
- [ ] Explain Ratio.
- [ ] Explain Battle Notes.
- [ ] Update README.

---

## Architecture

- [x] Split app.py before it became a crime scene.
- [x] Centralize move metadata lookups.
- [x] Structured Battle Notes.
- [ ] Continue separating UI from engine.
- [ ] Improve importer output.
- [ ] Implement sprite lookup layer.
- [ ] Add UI theme/constants module.

---

## Beta Readiness

- [ ] Recommendation card complete.
- [ ] Battle Snapshot complete.
- [ ] Sprites integrated.
- [ ] Type badges integrated.
- [ ] Matchup Strength implemented.
- [ ] About page complete.
- [ ] Package executable build.

