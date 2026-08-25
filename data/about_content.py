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
HERO_SUBTITLE = "Tactical battle guidance for Pokémon Sword"
HERO_VERSION = "v0.2.1 Beta"
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
        title="How to Use Battle Compass",
        icon="help",
        paragraphs=(
            (
                "Battle Compass works best as a simple loop: keep your team "
                "updated, check the matchup before an important battle, plan "
                "what comes next, and repeat."
            ),
            (
                "The app can only work with the information you give it. A "
                "beautifully calculated recommendation based on last Tuesday’s "
                "moveset is still a beautifully calculated wrong answer."
            ),
        ),
        bullets=(
            (
                "My Team — Start with the Team Editor. Enter your active and "
                "boxed Pokémon and keep their level, stats, moves, Ability, "
                "held item, Nature, and other available details current. The "
                "Battle Compass uses this information directly in its "
                "calculations, so update it after evolutions, move changes, "
                "held-item changes, or other meaningful changes to a build."
            ),
            (
                "Pokémon Details — To review any Pokémon already in your "
                "Journey, open Pokémon Details on the My Team page and select "
                "the Pokémon you want to inspect from the dropdown. This gives "
                "you a quick view of its current build, stats, Nature effects, "
                "and evolution information."
            ),
            (
                "Battle Compass — Select the battle and opponent you are "
                "preparing for. The Recommendation card shows the suggested "
                "team member, Best Move, Matchup Strength, explanation, and "
                "relevant Battle Notes. Check Full Analysis when you want to "
                "compare the rest of the team instead of stopping at the top "
                "recommendation."
            ),
            (
                "My Journey — Use the Badge Tracker to keep your story progress "
                "current. Current Objectives shows what matters now, while the "
                "Journey Checklist, Galar map, and Team Planner help you track "
                "items and future team additions and see when and where they "
                "become available. Objectives move from unavailable to "
                "available to obtained as your Journey progresses."
            ),
            (
                "Team Planner — Review acquisition details before hunting a "
                "planned Pokémon. When you catch one, mark it acquired and add "
                "the Pokémon you actually caught to My Team so the planning "
                "objective becomes part of your usable roster."
            ),
            (
                "About — You are here. This page contains the recommendation "
                "philosophy, save and backup guidance, current project scope, "
                "roadmap, version history, credits, and the optional Nerd Stuff "
                "for anyone who would like considerably more Pokémon math than "
                "was strictly necessary."
            ),
        ),
        accent="blue",
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
                "You can export a portable Journey backup and load it again "
                "later. Browser storage still belongs to that browser and "
                "device, so backups are strongly recommended if you would be "
                "annoyed by your carefully assembled team vanishing into the void."
            ),
            (
                "On iPhone and iPad, use Battle Compass as a normal browser site. "
                "Installed Home Screen Web App mode is not currently supported "
                "because Journey file import does not work reliably there."
            ),
        ),
        accent="green",
    ),
    AboutSection(
        title="Current Scope",
        icon="target",
        paragraphs=(
            (
                "Battle Compass currently focuses on Pokémon Sword story play "
                "and singles battles."
            ),
            (
                "It intentionally does not attempt to recreate the entire "
                "competitive battle simulator ecosystem. That road ends with "
                "weather matrices, EV optimization, and me forgetting what "
                "sunlight looks like."
            ),
        ),
        bullets=(
            "Pokémon Sword",
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
                "Alpha, and now runs in Flet as both a packaged Windows desktop "
                "application and a static browser application."
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
                "With the core Flet migration and Beta feature set complete, "
                "the next phase is release hardening, broader testing, and the "
                "remaining quality-of-life work that survives contact with actual players."
            ),
        ),
        bullets=(
            "Save-data validation and migration support",
            "Additional recovery and error handling",
            "Broader automated engine regression tests",
            "More complete move-effect data and mechanics",
            "Shield support",
            "Additional Journey and team-planning refinements",
            "Revisit offline/PWA support when the Flet toolchain is less dramatic",
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
        name="v0.2.1",
        status="Current Beta",
        summary=(
            "Journey acquisition validation, planning refinements, and "
            "player-facing guidance for the next round of Beta testing."
        ),
        bullets=(
            "Corrected and validated Pokémon Journey acquisition data",
            "Added deterministic acquisition validation with 193/193 records passing",
            "Improved special trade, gift, story, and Max Raid acquisition handling",
            "Refined Journey encounter and badge-gating data",
            "Added How to Use Battle Compass guidance to the About page",
            "Included additional Journey and mobile-interface polish",
        ),
    ),
    VersionEntry(
        name="v0.2.1",
        status="Current Beta",
        summary=(
            "Journey acquisition validation, planning refinements, and "
            "player-facing guidance for the next round of Beta testing."
        ),
        bullets=(
            "Corrected and validated Pokémon Journey acquisition data",
            "Added deterministic acquisition validation with 193/193 records passing",
            "Improved special trade, gift, story, and Max Raid acquisition handling",
            "Refined Journey encounter and badge-gating data",
            "Added How to Use Battle Compass guidance to the About page",
            "Included additional Journey and mobile-interface polish",
        ),
    ),
    VersionEntry(
    name="v0.1.1",
        status="Previous Alpha",
        summary=(
            "The final pre-Beta desktop Alpha, built around the validated "
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