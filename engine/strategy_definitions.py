from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class StrategyDefinition:
    key: str
    label: str
    color: str
    compact_description: str
    full_description: str
    required_roles: tuple[str, ...]
    supporting_roles: tuple[str, ...] = ()
    battle_compass_selectable: bool = False
    recommender_available: bool = False
    proactive_near_ready_eligible: bool = True


STRATEGY_COLORS = {
    "strongest_matchup": "#FFFFFF",
    "poison_offensive_pressure": "#C084FC",
    "poison_attrition": "#C084FC",
    "screen_control": "#F95587",
    "setup_offense": "#C22E28",
    "status_control_punish": "#735797",
    "weather_control": "#96D9D6",
    "defensive_attrition": "#B7B7CE",
}


STRATEGY_DEFINITIONS = {
    "strongest_matchup": StrategyDefinition(
        key="strongest_matchup",
        label="Strongest Matchup",
        color=STRATEGY_COLORS["strongest_matchup"],
        compact_description=(
            "Use the standard Battle Compass recommendation priority based on "
            "the strongest modeled matchup. See My Team for a complete explanation."
        ),
        full_description=(
            "Use the standard Battle Compass recommendation priority based on "
            "the strongest modeled matchup."
        ),
        required_roles=(),
        battle_compass_selectable=True,
        recommender_available=True,
        proactive_near_ready_eligible=False,
    ),

    "poison_offensive_pressure": StrategyDefinition(
        key="poison_offensive_pressure",
        label="Poison – Offensive Pressure",
        color=STRATEGY_COLORS["poison_offensive_pressure"],
        compact_description=(
            "Establish poison when it is safe and worthwhile. Follow with "
            "offensive pressure with moves like Venoshock or Hex. See My Team "
            "for a complete explanation."
        ),
        full_description=(
            "Establish poison when it is safe and worthwhile, then convert it "
            "into offensive pressure with tools such as Venoshock, Hex, or "
            "Merciless. Non-lead opponents inherit the recommended lead setup "
            "when that assumption remains valid."
        ),
        required_roles=(
            "poison_setter",
            "poison_offensive_punisher",
        ),
        supporting_roles=(
            "team_poison_setup",
            "corrosion",
            "setup_support",
            "speed_control",
            "recovery",
        ),
        battle_compass_selectable=True,
        recommender_available=True,
    ),

    "poison_attrition": StrategyDefinition(
        key="poison_attrition",
        label="Poison – Attrition",
        color=STRATEGY_COLORS["poison_attrition"],
        compact_description=(
            "Establish poison when it is safe and worthwhile. Follow with "
            "recovery, protection, and defensive control while poison progresses. "
            "See My Team for a complete explanation."
        ),
        full_description=(
            "Establish poison when it is safe and worthwhile, then favor "
            "walling, recovery, protection, screens, defensive setup, and other "
            "ways to let poison progress. Non-lead opponents inherit the "
            "recommended lead setup when that assumption remains valid."
        ),
        required_roles=(
            "poison_setter",
            "attrition_anchor",
        ),
        supporting_roles=(
            "team_poison_setup",
            "corrosion",
            "recovery",
            "protection",
            "defensive_setup",
            "screen_support",
            "setup_denial",
        ),
        battle_compass_selectable=True,
        recommender_available=True,
    ),

    "screen_control": StrategyDefinition(
        key="screen_control",
        label="Screen Control",
        color=STRATEGY_COLORS["screen_control"],
        compact_description=(
            "Use Reflect and Light Screen to create safer turns for powerful "
            "teammates that normally trade bulk for offense."
        ),
        full_description=(
            "Favor an easy, organic screen setter that can establish Reflect "
            "and/or Light Screen without sacrificing its entire role, then use "
            "those protected turns to support powerful but comparatively frail "
            "attackers. Favor a balanced physical and special offensive core "
            "when the available team permits it."
        ),
        required_roles=(
            "screen_setter",
            "screen_offensive_beneficiary",
        ),
        supporting_roles=(
            "dual_screen_setter",
            "priority_screen_setter",
            "fast_screen_setter",
            "light_clay_user",
            "physical_offense",
            "special_offense",
            "setup_sweeper",
        ),
        battle_compass_selectable=True,
        recommender_available=True,
    ),

    "setup_offense": StrategyDefinition(
        key="setup_offense",
        label="Setup Offense",
        color=STRATEGY_COLORS["setup_offense"],
        compact_description=(
            "Create a safe opening to boost, then turn moves like Swords Dance "
            "or Calm Mind into overwhelming offensive pressure."
        ),
        full_description=(
            "Build around Pokémon that can turn stat boosts into a major offensive "
            "advantage. Favor sweepers that can establish boosts reliably through "
            "Speed, priority, natural staying power, or a teammate-created opening. "
            "Debuffs and control moves can qualify as setup facilitation when they "
            "make the switch-and-boost sequence meaningfully safer."
        ),
        required_roles=("setup_sweeper",),
        supporting_roles=(
            "setup_facilitator",
            "opponent_debuffer",
            "speed_control",
            "priority_user",
            "fast_setup",
            "defensive_setup",
            "physical_setup",
            "special_setup",
        ),
        battle_compass_selectable=True,
        recommender_available=True,
    ),

    "status_control_punish": StrategyDefinition(
        key="status_control_punish",
        label="Status Control & Punish",
        color=STRATEGY_COLORS["status_control_punish"],
        compact_description=(
            "Reliably inflict a major status condition, then exploit the battle "
            "state directly with tools such as Hex or indirectly through control."
        ),
        full_description=(
            "Pair reliable major-status application with a meaningful payoff. "
            "Burn, paralysis, sleep, and Yawn can create the opening; Hex is the "
            "gold-standard direct punishment, while speed control, physical "
            "suppression, and setup opportunities can also turn status into "
            "strategic value. Incidental low-chance secondary effects do not "
            "count as reliable status establishment."
        ),
        required_roles=(
            "reliable_status_setter",
            "status_punisher",
        ),
        supporting_roles=(
            "burn_setter",
            "paralysis_setter",
            "sleep_setter",
            "yawn_setter",
            "hex_user",
            "speed_control",
            "setup_facilitator",
            "defensive_control",
        ),
        battle_compass_selectable=True,
        recommender_available=True,
    ),

    "weather_control": StrategyDefinition(
        key="weather_control",
        label="Weather Control",
        color=STRATEGY_COLORS["weather_control"],
        compact_description=(
            "Establish weather deliberately, then use teammates whose moves or "
            "abilities gain meaningful value from it."
        ),
        full_description=(
            "Build around reliable weather establishment plus enough beneficiaries "
            "to justify spending turns creating that weather. Reward Pokémon whose "
            "moves, abilities, accuracy, Speed, recovery, defense, or setup economy "
            "materially improve in sun, rain, sandstorm, or hail. A lone weather "
            "move without meaningful beneficiaries is not a weather strategy."
        ),
        required_roles=(
            "weather_setter",
            "weather_beneficiary",
        ),
        supporting_roles=(
            "automatic_weather_setter",
            "weather_speed_beneficiary",
            "weather_power_beneficiary",
            "weather_accuracy_beneficiary",
            "weather_defense_beneficiary",
            "weather_recovery_beneficiary",
            "weather_charge_skip_beneficiary",
        ),
        battle_compass_selectable=True,
        recommender_available=True,
    ),

    "defensive_attrition": StrategyDefinition(
        key="defensive_attrition",
        label="Defensive Attrition",
        color=STRATEGY_COLORS["defensive_attrition"],
        compact_description=(
            "Turn defense into pressure through chip, contact punishment, denial, "
            "or defensive stats that become offense."
        ),
        full_description=(
            "Favor Pokémon that become difficult to remove while making continued "
            "interaction costly for the opponent. This includes defense-to-damage "
            "engines such as Iron Defense plus Body Press, passive contact punishment "
            "such as Iron Barbs, and defensive denial or retaliation through moves "
            "such as Obstruct and Baneful Bunker. Recovery, protection, and persistent "
            "chip strengthen the plan but poison is not required."
        ),
        required_roles=(
            "defensive_pressure",
            "staying_power",
        ),
        supporting_roles=(
            "defense_to_damage",
            "contact_punishment",
            "protection",
            "recovery",
            "defensive_setup",
            "persistent_chip",
            "opponent_debuffer",
            "setup_denial",
        ),
        battle_compass_selectable=True,
        recommender_available=True,
    ),
}


BATTLE_COMPASS_SELECTABLE_STRATEGY_IDS = tuple(
    key
    for key, definition in STRATEGY_DEFINITIONS.items()
    if definition.battle_compass_selectable
)

RECOMMENDER_STRATEGY_IDS = tuple(
    key
    for key, definition in STRATEGY_DEFINITIONS.items()
    if definition.recommender_available
)


def get_strategy_definition(strategy: str) -> StrategyDefinition:
    return STRATEGY_DEFINITIONS.get(
        strategy,
        STRATEGY_DEFINITIONS["strongest_matchup"],
    )