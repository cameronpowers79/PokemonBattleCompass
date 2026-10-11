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
HERO_VERSION = "v0.3.0 Beta"
HERO_TAGLINE = "Built because one Excel workbook escaped containment."


# Strategy reference: each entry is a standard About card so existing About-page
# assembly automatically displays it. AboutCard supplies its artwork and color.
STRATEGY_ABOUT_SECTIONS = (
    AboutSection(
        title="Understanding Team Strategies", icon="account_tree",
        paragraphs=(
            "A Team Strategy is a general battle plan, not a required team type. Instead of asking only which Pokémon hits hardest right now, you can ask how your team should create an advantage: by boosting, spreading status, controlling weather, or surviving until the opponent runs out of options.",
            "Strategies first appear during Journey onboarding. You may accept planning help, skip it, or change strategies later. Your Pokémon choices are always yours; the Compass adapts to the Pokémon, moves, and Abilities you actually enter.",
            "The Strategy Recommender assesses the current equipped team and can suggest additions and moves through My Journey. Its readiness grades describe the available tools, not whether you are allowed to select a strategy. In battle, Strategic Fit evaluates the proposed tactical plan; Direct Matchup and Full Analysis remain available for straightforward comparisons.",
            "A conditional plan assumes a particular battle state, such as an active screen, poisoned target, or surviving weather. Battle Compass cannot see the actual fight or know whether you followed an earlier recommendation. Check those assumptions before acting. A dangerous opposing setup move or a safer immediate knockout can also justify temporarily deviating from your chosen strategy.",
            "The eight modes below can work independently or be combined by an experienced player. You do not need to know competitive terminology to use them; start with whichever description sounds fun."
        ), accent="blue",
    ),
    AboutSection(
        title="Strongest Matchup", icon="target",
        paragraphs=(
            "The simplest starting point: choose the Pokémon with the best modeled immediate matchup against the selected opponent. The Compass weighs how hard its attacks hit against the danger of the opponent's strongest available attack, including type effectiveness, defenses, Abilities, and supported held items.",
            "Example: if your Ground-type can safely defeat an opposing Electric-type with Earthquake, this mode can recommend that direct answer without asking you to set anything up first.",
            "Choose it when you want uncomplicated battle guidance, when you are unfamiliar with strategy modes, or when a special plan is too dangerous to attempt. Strongest Matchup is always available and serves as the fallback when a tactical assumption cannot be supported."
        ), accent="blue",
    ),
    AboutSection(
        title="Poison – Offensive Pressure", icon="target",
        paragraphs=(
            "Poison first, damage second. Establish poison through an equipped move such as Toxic or Toxic Spikes, then exploit the poisoned target with attacks that become stronger or more useful while poison is active—especially Venoshock, Hex, or a suitable Merciless attacker.",
            "Example: Roserade poisons an opponent, then Salazzle uses Venoshock for amplified damage. Toxic Spikes can help with later incoming foes, but it does not poison the opponent already standing on the field.",
            "A successful team needs reliable poison application and a meaningful offensive payoff. Poison and Steel types generally cannot be poisoned, except that Corrosion can allow its user to poison them; Steel still resists or is immune to the relevant attacking types normally. The Compass evaluates these matchups and may choose immediate offense instead of forcing a poison setup."
        ), accent="purple",
    ),
    AboutSection(
        title="Poison – Attrition", icon="target",
        paragraphs=(
            "Poison is the clock, and staying alive is the plan. After poisoning the target, use recovery, protection, bulky Pokémon, and defensive control to let poison damage accumulate over several turns.",
            "Example: a poison setter such as Roserade establishes Toxic, then Toxapex uses Recover and Baneful Bunker to limit damage while the opponent's health ticks down. Teammates with protection or resistance can maintain pressure even without a huge immediate attack.",
            "This works best against targets that can be poisoned and cannot quickly break through your defenses. A poison-immune foe, a dangerous setup sweeper, or an immediate knockout opportunity may call for a different answer. Toxic Spikes on the field are not proof that the current opponent is poisoned."
        ), accent="purple",
    ),
    AboutSection(
        title="Screen Control", icon="target",
        paragraphs=(
            "Reflect reduces incoming physical damage and Light Screen reduces special damage in singles. A screen setter creates a safer window for a teammate that is powerful but might otherwise struggle to take a hit.",
            "Example: a male Meowstic with Prankster uses Reflect or Light Screen, then a hard-hitting partner enters with extra protection. Light Clay can extend ordinary screen duration, providing more useful protected turns.",
            "A good screen team has a dependable setter plus at least one attacker that really benefits from the protection. Switching consumes a turn, screens expire, and some attacks or Abilities bypass or remove them. The Compass identifies the relevant opponent's attack category but cannot confirm a screen established earlier is still active."
        ), accent="blue",
    ),
    AboutSection(
        title="Setup Offense", icon="target",
        paragraphs=(
            "Spend a relatively safe turn strengthening your Pokémon, then convert the boost into stronger attacks or a Speed advantage. Swords Dance raises physical Attack, Nasty Plot raises Special Attack, and Calm Mind raises Special Attack and Special Defense.",
            "Example: Weavile uses Swords Dance and follows with Ice Punch or Throat Chop; another team might use a Calm Mind special attacker or a Pokémon whose Ability raises Speed. Screens or status control can help create the opening, even though they are separate modes in the Compass.",
            "The crucial question is whether you can afford the setup turn. Boosts do not help if the opponent knocks you out first, and some opponents can remove boosts or become lethal through their own setup. The Compass estimates the projected payoff and can recommend attacking immediately instead."
        ), accent="orange",
    ),
    AboutSection(
        title="Status Control & Punish", icon="target",
        paragraphs=(
            "Use a reliable burn, paralysis, or sleep effect to disrupt the opponent, and then benefit from the change in battle conditions. Burn weakens most physical attackers, paralysis reduces Speed, and sleep can create free turns. A move such as Hex provides extra damage against targets with major status conditions.",
            "Example: Chandelure uses Will-O-Wisp to burn a physical attacker, then hits with a stronger Hex. A Thunder Wave user may instead let a slower teammate move first. Unlike Poison strategies, the value here can come from control even without Venoshock or poison damage.",
            "A chance of status as a move's minor secondary effect is not the same as a dependable setter. Type and Ability immunities matter. Each newly encountered opponent starts without an assumed major status; conditional damage is an opportunity, not a claim that the opponent is already afflicted."
        ), accent="purple",
    ),
    AboutSection(
        title="Weather Control", icon="target",
        paragraphs=(
            "Change the battlefield's weather to create a useful advantage. Rain strengthens Water attacks and weakens Fire attacks; sun does the reverse. Sandstorm can protect Rock-types from special attacks, while hail can support Ice-oriented effects in Pokémon Sword. Weather-dependent Abilities and moves provide further benefits.",
            "Example: Pelipper's Drizzle starts rain for a Swift Swim Barraskewda; Torkoal's Drought empowers its own Fire attacks or lets an ally use Solar Blade without charging; Gigalith's Sand Stream can support an Excadrill with Sand Force. Onboarding helps build matched setter-and-beneficiary pairs by weather.",
            "Weather has a limited duration. A teammate with a different automatic weather Ability replaces the current weather upon entering; incompatible setters must not be treated as one continuous plan. Sometimes the setter's own attack is the best payoff, and sometimes the strongest decision is to avoid weather that would help the opponent. Conditional projections do not prove the weather is still active."
        ), accent="blue",
    ),
    AboutSection(
        title="Defensive Attrition", icon="target",
        paragraphs=(
            "Win through defensive staying power rather than a quick knockout. Moves such as Iron Defense can make physical hits less dangerous, and Body Press converts the user's Defense into attacking power. Protect, recovery, and contact-punishing moves can create other ways to gain ground.",
            "Example: Ferrothorn uses Iron Defense and then Body Press, or Toxapex uses Baneful Bunker to poison a contact attacker before attacking with Venoshock. Obstagoon can use Obstruct to lower a contact attacker's Defense, then punish with Throat Chop or Body Press.",
            "Protection is not universally safe: the opponent might choose a noncontact move, boost its stats, or simply overwhelm the defender. Consecutive protection attempts can fail. The Compass evaluates the actual incoming attacks and can abandon setup when an immediate knockout is safer."
        ), accent="blue",
    ),
)

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
            "Recommends the strongest current team matchup or an opponent-aware strategy action.",
            "Offers eight optional Team Strategies, guided team-building, and tactical plans.",
            "Identifies each teammate’s best attacking move.",
            "Compares projected offense and incoming danger.",
            "Shows Matchup Strength and a full-team analysis.",
            "Shows Nature effects and next-evolution requirements in Pokémon Details.",
            "Highlights important mechanics through Battle Notes.",
            "Suggests modeled held items that fit the current build.",
            "Provides move, type, Ability, and held-item reference popups.",
            "Explains why one option edged out another.",
            "Plans future moves and their TM/TR acquisition needs in My Journey.",
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
                "recommendation. Select a Team Strategy if you want battle plans "
                "that use setup, protection, status, or weather rather than "
                "ranking direct damage alone."
            ),
            (
                "My Journey — Use the Badge Tracker to keep your story progress "
                "current. Current Objectives shows what matters now, while the "
                "Journey Checklist, Galar map, Team Planner, and Move Planner "
                "help you track items, future team additions, planned moves, "
                "and when and where their requirements become available. "
                "Objectives move from unavailable to available to obtained as "
                "your Journey progresses."
            ),
            (
                "Team Planner — Review acquisition details before hunting a "
                "planned Pokémon. When you catch one, mark it acquired and add "
                "the Pokémon you actually caught to My Team so the planning "
                "objective becomes part of your usable roster."
            ),
            (
                "Move Planner — Plan up to four moves for each Pokémon in Team "
                "Planner. Choose a plain move when you only want to record the "
                "moveset, or choose its TM/TR source when Battle Compass should "
                "also add that acquisition requirement to the Journey Checklist. "
                "Consumable TR quantities are counted across the active plan."
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
            "STAB, modeled Ability effects, and deterministic Ability-set weather",
            "Move power, accuracy, priority, and multi-hit behavior",
            "Relevant offensive and defensive stats",
            "Modeled held-item bonuses and defensive effects",
            "Special damage rules such as Body Press, Psyshock, and Foul Play",
            "Incoming danger, likely OHKOs, and tactical warnings",
        ),
        accent="purple",
    ),
    *STRATEGY_ABOUT_SECTIONS,
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
            "Deterministic Drought, Drizzle, Sand Stream, and Snow Warning weather handling",
        ),
    ),
    (
        "Still intentionally outside the model",
        (
            "Doubles-specific targeting and partner interactions",
            "Full turn-by-turn simulation of weather duration, terrain, and changing battle state",
            "Nature effects in battle calculations, IVs, EV spreads, and competitive optimization",
            "Long-form turn-by-turn battle simulation",
            "Every wonderfully strange edge case Game Freak has invented",
        ),
    ),
)


VERSION_HISTORY = (
    VersionEntry(
        name="v0.3.0",
        status="Current Beta",
        summary="Team Strategies: guided planning and opponent-aware tactical battle recommendations.",
        bullets=(
            "Added eight selectable strategies, from Strongest Matchup to weather, screens, setup, status, poison, and defensive attrition",
            "Added a Strategy Recommender and onboarding support for team members, Abilities, and planned moves",
            "Introduced strategic roles, projected conditional Move Scores, Strategic Fit, and strategy-specific action explanations",
            "Added safer tactical fallbacks for dangerous setup opponents, contact punishment, switching, and weather changes",
            "Expanded the Tutorial and About reference to explain strategies with practical examples",
        ),
    ),
    VersionEntry(
        name="v0.2.2",
        status="Previous Beta",
        summary=(
            "Move planning, deterministic Ability-set weather, and a focused "
            "stability and Journey-refinement pass for the next validation run."
        ),
        bullets=(
            "Added Move Planner with four move slots per planned Pokémon",
            "Linked TM/TR move sources to Journey Checklist requirements and consumable quantities",
            "Modeled deterministic Drought, Drizzle, Sand Stream, and Snow Warning weather effects",
            "Refined Badge Tracker behavior and mobile interaction",
            "Improved storage and session robustness around SharedPreferences startup/reconnect timing",
            "Added Aegislash mixed-form stat-entry guidance and Stance Change battle warnings",
        ),
    ),
    VersionEntry(
        name="v0.2.1",
        status="Previous Beta",
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
        name="v0.2.0",
        status="Initial Beta",
        summary=(
            "The first Beta release, introducing My Journey, broader battle "
            "mechanics, web deployment, and the expanded playthrough-planning "
            "toolset."
        ),
        bullets=(
            "Introduced My Journey with Badge Tracker, Current Objectives, map, and Team Planner",
            "Added broader Journey persistence, import/export, and backup support",
            "Expanded battle-engine handling for special moves, Abilities, held items, and OHKO notes",
            "Added held-item recommendations and richer Pokémon Details",
            "Completed the move from desktop-only Alpha to hosted Flet web Beta",
            "Added normalized texture artwork and expanded runtime asset support",
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