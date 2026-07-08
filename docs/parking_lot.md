# Battle Compass Parking Lot

## Engine Parity

### Notes / Why
- [ ] Replace placeholder OHKO Notes thresholds with workbook HP-aware logic.
- [ ] Port remaining Notes ordering, conditions, and verbiage from Compass.
- [x] Port workbook-derived Why? explanation logic.
- [x] Refine Why? wording for the app (compose explanations from multiple factors using story-player tone).
- [ ] Compose richer Why? explanations from multiple factors.

### Mechanics
- [x] Flash Fire immunity (Excel bug fixed; Python already correct).
- [x] Body Press uses DEF.
- [x] Psyshock / Psystrike / Secret Sword use target DEF.
- [x] Technician / low-power move boost.
- [x] Body Press + Iron Defense opportunity note.
- [x] Status-boosted Hex / Venoshock notes.
- [x] Priority move mechanics note framework.
- [x] Contact-triggered tactical notes.
- [ ] Add remaining special move mechanics (Shell Trap, etc.).
- [ ] Verify all DamageMethod values from `moves.json` are implemented.

---

## Battle Notes

- [ ] Replace plain-text notes with structured Battle Notes.
- [ ] Introduce note categories:
  - 💡 Worth Considering
  - ℹ️ Information
  - ⚠️ Caution
  - 🚨 Warning
- [x] Refine priority warnings to be move-specific.
- [x] Refine contact warnings with move-specific wording.
- [x] Replace "Defense-boosted Body Press possible" with coaching-style wording.

---

## Player Experience

### Alpha UI
- [x] Build Alpha prototype.
- [ ] Promote Alpha into main application.

### Layout
- [ ] Recommendation card.
- [ ] Battle Snapshot card.
- [ ] Top 3 recommendations.
- [ ] Expandable Full Analysis.
- [ ] Matchup Strength indicator.

### Polish
- [ ] Pokémon sprites.
- [ ] Type badges.
- [ ] Stat data bars with numeric values.
- [ ] Worst Incoming Move displays move category (Physical/Special).
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
- [ ] Continue separating UI from engine.
- [ ] Improve importer output.
- [ ] Centralize move metadata lookups.
- [ ] Implement sprite lookup layer.

---

## Design Principles

- Advice first. Analysis second. Calculations third.
- Explain the recommendation, not the game.
- Battle Compass is a compass, not a GPS.
- Write for experienced story-mode players.
- Be transparent without being overwhelming.
- Every calculation should answer a player question.