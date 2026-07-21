"""
Text content for the Pokémon Battle Compass About page.

This module intentionally contains no Flet imports. Keep player-facing
documentation here so copy can be revised without digging through layout code.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class AboutSection:
    """One standard About-page documentation section."""

    title: str
    icon: str
    paragraphs: tuple[str, ...] = ()
    bullets: tuple[str, ...] = ()
    accent: str = "blue"


@dataclass(frozen=True)
class VersionEntry:
    """One release-history entry."""

    name: str
    status: str
    summary: str
    bullets: tuple[str, ...] = ()


HERO_TITLE = "Pokémon Battle Compass"
HERO_SUBTITLE = "Tactical battle guidance for Pokémon Sword & Shield"
HERO_VERSION = "v0.1.1"
HERO_TAGLINE = "Built because one Excel workbook escaped containment."


ABOUT_SECTIONS = (
    AboutSection(
        title="Welcome",
        icon="waving_hand",
        paragraphs=(
            (
                "Battle Compass started life as an Excel workbook because I "
                "wanted a faster way to answer one question: ‘Okay... which "
                "one of my Pokémon should handle this?’"
            ),
            (
                "Somewhere along the way, a few formulas turned into a few "
                "hundred formulas. Then they turned into Python. Then they "
                "turned into... whatever this has become."
            ),
            (
                "If you enjoy understanding why a matchup is good instead of "
                "simply being told which button to press, you are exactly who "
                "I built this for."
            ),
            (
                "And yes, I fully realize I have spent an unreasonable amount "
                "of time teaching a computer to do pretend Pokémon math."
            ),
        ),
        accent="blue",
    ),
    AboutSection(
        title="What Battle Compass Does",
        icon="explore",
        paragraphs=(
            (
                "Battle Compass helps you make better battle decisions without "
                "taking the decision—or the fun—away from you."
            ),
        ),
        bullets=(
            "Recommends the strongest current team matchup.",
            "Identifies each teammate’s best attacking move.",
            "Compares projected offense and incoming danger.",
            "Shows Matchup Strength and a full-team analysis.",
            "Shows Nature effects and next-evolution requirements in Pokémon Details.",
            "Highlights important mechanics through Battle Notes.",
            "Suggests modeled held items that fit the current build.",
            "Provides move, type, Ability, and held-item reference popups.",
            "Explains why one option edged out another.",
        ),
        accent="green",
    ),
    AboutSection(
        title="How Recommendations Work",
        icon="analytics",
        paragraphs=(
            (
                "Battle Compass is not looking for the strongest Pokémon. It "
                "is looking for the strongest matchup."
            ),
            (
                "Every eligible team member is evaluated against the selected "
                "opponent. The recommendation balances projected outgoing "
                "damage against the opponent’s most dangerous incoming move."
            ),
            (
                "The result is decision support—not an order from the Pokémon "
                "High Council. Sometimes your favorite Pokémon is not the "
                "mathematical favorite. You are still allowed to use them. "
                "I certainly do."
            ),
        ),
        bullets=(
            "Type effectiveness and immunities",
            "STAB and modeled Ability effects",
            "Move power, accuracy, priority, and multi-hit behavior",
            "Relevant offensive and defensive stats",
            "Modeled held-item bonuses and defensive effects",
            "Special damage rules such as Body Press, Psyshock, and Foul Play",
            "Incoming danger, likely OHKOs, and tactical warnings",
        ),
        accent="purple",
    ),
    AboutSection(
        title="Saving Your Journey",
        icon="save",
        paragraphs=(
            (
                "Your Journey is stored locally on your own device. Battle "
                "Compass does not upload your team to an account or cloud "
                "service."
            ),
            (
                "The Save Team button is intentionally retained as a "
                "proofreading checkpoint. You can edit freely, confirm the "
                "details are correct, and then commit the changes to your "
                "Journey."
            ),
            (
                "Manual backup/export and restore/import are planned but not "
                "yet available. Until then, clearing browser or application "
                "storage may remove the saved Journey. Technology: still "
                "finding new ways to make ‘locally stored’ sound threatening."
            ),
        ),
        accent="green",
    ),
    AboutSection(
        title="Current Scope",
        icon="target",
        paragraphs=(
            (
                "Battle Compass currently focuses on Pokémon Sword & Shield "
                "story play and singles battles."
            ),
            (
                "It intentionally does not attempt to recreate the entire "
                "competitive battle simulator ecosystem. That road ends with "
                "weather matrices, EV optimization, and me forgetting what "
                "sunlight looks like."
            ),
        ),
        bullets=(
            "Pokémon Sword & Shield",
            "Singles battles",
            "Story and challenge-run decision support",
            "Player-entered team stats, moves, Abilities, and held items",
            "A growing—but deliberately validated—set of modeled mechanics",
        ),
        accent="orange",
    ),
    AboutSection(
        title="Architecture",
        icon="account_tree",
        paragraphs=(
            (
                "The project began as an Excel workbook, became a Streamlit "
                "Alpha, and now runs in Flet as a desktop application, with "
                "PWA support still planned."
            ),
            (
                "The validated battle engine remains framework-independent. "
                "The interface prepares player data, calls the engine, and "
                "translates its results into cards, notes, and explanations."
            ),
            (
                "In other words: the math lives in the engine; the shiny "
                "buttons are not allowed to touch it without adult supervision."
            ),
        ),
        bullets=(
            "engine/ — matchup calculations and battle mechanics",
            "ui/viewmodels/ — adapts engine output for the interface",
            "ui/components/ — reusable visual controls",
            "ui/views/ — complete application pages",
            "ui/storage/ — local Journey persistence",
            "data/ — bundled reference and modeled-mechanic data",
        ),
        accent="blue",
    ),
    AboutSection(
        title="Roadmap",
        icon="route",
        paragraphs=(
            (
                "The current priority is strengthening the features that make "
                "Journeys safe, portable, and easier to manage over a full "
                "playthrough."
            ),
        ),
        bullets=(
            "Manual backup/export and restore/import",
            "Save-data validation, migration, and interrupted-write recovery",
            "Installable and offline-capable PWA verification",
            "Additional error handling and automated engine tests",
            "More complete move-effect data and mechanics",
            "Trainer’s Guide planning and progress tools",
            "Documentation, screenshots, and release notes",
        ),
        accent="purple",
    ),
    AboutSection(
        title="Credits",
        icon="favorite",
        paragraphs=(
            "Designed and developed by Cameron.",
            "Built with Python and Flet.",
            (
                "Pokémon and held-item sprites are provided by the PokéSprite "
                "project. Trainer and texture artwork is packaged from the "
                "project’s available assets."
            ),
            (
                "Special thanks to everyone willing to stress-test a battle "
                "engine by making questionable team-building decisions. Your "
                "sacrifice has been statistically significant."
            ),
        ),
        accent="green",
    ),
    AboutSection(
        title="Fan Project Disclaimer",
        icon="gavel",
        paragraphs=(
            (
                "Pokémon Battle Compass is an unofficial, non-commercial fan "
                "project created for educational and entertainment purposes."
            ),
            (
                "Pokémon, Pokémon Sword & Shield, and all related names, "
                "characters, artwork, items, Abilities, and trademarks are "
                "owned by Nintendo, Game Freak, Creatures Inc., and The "
                "Pokémon Company."
            ),
            "No endorsement is implied. No infringement is intended.",
        ),
        accent="orange",
    ),
)


NERD_STUFF_INTRO = (
    "This section is optional in the same way that reading every Pokédex entry "
    "is optional: technically true, but some of us were always going to click."
)

NERD_STUFF_GROUPS = (
    (
        "Core matchup model",
        (
            "Type effectiveness, dual-type multiplication, and immunities",
            "STAB, Adaptability, Huge Power, Pure Power, and Technician",
            "Relevant Attack, Special Attack, Defense, and Special Defense",
            "Accuracy, multi-hit behavior, and move priority",
            "Incoming and outgoing Move Scores",
        ),
    ),
    (
        "Special move handling",
        (
            "Body Press using the user’s Defense",
            "Psyshock-family moves targeting Defense",
            "Foul Play using the target’s Attack",
            "Fixed-damage, variable-damage, and OHKO moves",
            "Conditional power for moves such as Hex and Venoshock",
            "First-turn and turn-order eligibility rules",
        ),
    ),
    (
        "Abilities and held items",
        (
            "Type and move-property immunities",
            "Damage-reduction and vulnerability modifiers",
            "Mold Breaker-style Ability bypass",
            "Offensive type/category boosters",
            "Eviolite, Assault Vest, Air Balloon, and Choice-item effects",
            "Tactical notes for recoil, move locking, Focus Sash, and contact",
        ),
    ),
    (
        "Still intentionally outside the model",
        (
            "Doubles-specific targeting and partner interactions",
            "Full weather and terrain simulation",
            "Nature effects in battle calculations, IVs, EV spreads, and competitive optimization",
            "Long-form turn-by-turn battle simulation",
            "Every wonderfully strange edge case Game Freak has invented",
        ),
    ),
)


VERSION_HISTORY = (
    VersionEntry(
    name="v0.1.1",
        status="Current",
        summary=(
            "The current desktop Alpha release, built around the validated "
            "battle engine and durable local Journeys."
        ),
        bullets=(
            "Responsive Battle Compass and My Team views",
            "First-use Journey onboarding with Gender and Nature",
            "Local Journey persistence",
            "Nature display and affected-stat indicators",
            "Evolution-method guidance in Pokémon Details",
            "Persistent Battle Compass selections",
            "Interactive offensive and defensive type references",
            "Expanded Ability and held-item battle modeling",
        ),
    ),

        VersionEntry(
            name="v0.1.0-alpha.1",
            status="Initial desktop Alpha",
            summary=(
                "The first packaged Flet release and the foundation of the "
                "current desktop application."
            ),
            bullets=(
                "Battle Compass and My Team views",
                "First-use Journey onboarding",
                "Local Journey persistence",
                "Reference dialogs",
                "Matchup Strength meter",
                "Ability-aware recommendations",
                "Full Analysis",
            ),
),

    VersionEntry(
        name="Streamlit Alpha",
        status="Reference implementation",
        summary=(
            "The original application layer and proof that the workbook’s "
            "logic could survive outside Excel."
        ),
        bullets=(
            "Established the recommendation-card layout",
            "Validated the core engine through full playthroughs",
            "Introduced Battle Notes and Full Analysis",
            "Retained as the historical reference during migration",
            (
                "Known quirk: iOS Safari may ignore the custom favicon and "
                "display a default letter icon. Safari has chosen its truth."
            ),
        ),
    ),
    VersionEntry(
        name="Excel Workbook",
        status="Origin story",
        summary=(
            "The original calculator, team sheet, opponent database, and "
            "approximately NERDTEENTHOUSAND hours of increasingly ambitious "
            "spreadsheet decisions."
        ),
        bullets=(
            "Established the first matchup-scoring model",
            "Provided the source data for the Python migration",
            (
                "Proved that a spreadsheet can become an application if nobody "
                "stops it in time"
            ),
        ),
    ),
)


FOOTER_TITLE = "Development Philosophy"
FOOTER_PARAGRAPHS = (
    (
        "Battle Compass is developed incrementally. I would rather release one "
        "feature that has been tested in actual play than ten features held "
        "together by optimism and a comment that says TODO."
    ),
    (
        "If something in this app looks a little obsessive, that is probably "
        "because I spent an evening arguing with myself about how a fictional "
        "ghost should interact with a fictional cat."
    ),
    "I remain confident this was a responsible use of time.",
)
