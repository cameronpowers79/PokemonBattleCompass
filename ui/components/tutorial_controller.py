"""
Screenshot-driven tutorial for Pokémon Battle Compass.

This tutorial avoids live-page targeting and scrolling. Each step uses a
bundled screenshot with deterministic callouts inside a modal overlay.
"""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from pathlib import Path
import sys
from typing import cast

import flet as ft

from ui.theme import (
    BORDER_DEFAULT,
    PRIMARY_BLUE,
    PRIMARY_BLUE_SOFT,
    SURFACE,
    SURFACE_RAISED,
    TEXT_MUTED,
    TEXT_PRIMARY,
    TEXT_SECONDARY,
    FONT_FAMILY_HEADER,
)


PROJECT_ROOT = Path(__file__).resolve().parents[2]
ASSETS_DIR = PROJECT_ROOT / "assets"

TutorialCompletedCallback = Callable[[], Awaitable[None]]


@dataclass(frozen=True)
class TutorialHighlight:
    x: float
    y: float
    width: float
    height: float
    label: str | None = None


@dataclass(frozen=True)
class TutorialStep:
    title: str
    filename: str
    image_width: int
    image_height: int
    paragraphs: tuple[str, ...]
    highlights: tuple[TutorialHighlight, ...] = ()


TUTORIAL_STEPS = (
    TutorialStep(
        title="Choose the Battle",
        filename="01_battle_settings.png",
        image_width=2048,
        image_height=476,
        paragraphs=(
            "Battle Settings tells the Compass which matchup you want to analyze. Choose your starter path, the trainer, the battle, and the opposing Pokémon.",
            "Changing the opponent immediately recalculates the recommendation. The starter selector can also be used to explore another starter path without changing the starter saved in your Journey.",
        ),
        highlights=(
            TutorialHighlight(72, 150, 370, 125, "Starter"),
            TutorialHighlight(725, 150, 385, 125, "Trainer"),
            TutorialHighlight(1365, 150, 435, 125, "Battle"),
            TutorialHighlight(70, 300, 500, 120, "Opponent"),
        ),
    ),
    TutorialStep(
        title="Read the Recommendation",
        filename="02_recommendation_card.png",
        image_width=570,
        image_height=942,
        paragraphs=(
            "The Recommended Pokémon card is the Compass's main answer for the selected matchup. It shows the suggested team member, its best modeled move, and the overall Matchup Strength.",
            "This is decision support, not an order. The card is meant to show you the strongest modeled option and explain why it rose to the top.",
        ),
        highlights=(
            TutorialHighlight(30, 30, 510, 255, "Recommended Pokémon"),
            TutorialHighlight(30, 310, 290, 280, "Best Move"),
            TutorialHighlight(335, 310, 205, 145, "Matchup Strength"),
        ),
    ),
    TutorialStep(
        title="How the Compass Chooses",
        filename="02_recommendation_card.png",
        image_width=570,
        image_height=942,
        paragraphs=(
            "Move Score estimates the strength of your best available move using the information Battle Compass can model: move power, your relevant attacking stat, the opponent's defenses, type effectiveness, STAB, Abilities, Held Items, deterministic weather, and other supported mechanics.",
            "Incoming Worst Score (IWS) performs the same kind of analysis from the opponent's side and identifies the most dangerous modeled incoming move.",
            "The Ratio compares your outgoing pressure with that incoming danger. Higher ratios generally represent stronger matchups.",
            "If a Pokémon has a very high modeled chance to move first and OHKO the opponent, Battle Compass may promote it even when another teammate has a slightly better Ratio. Sometimes the safest incoming attack is the one the opponent never gets to use.",
            "Effects that depend on battle state the Compass cannot know are kept out of the math and surfaced as Battle Notes instead.",
        ),
        highlights=(
            TutorialHighlight(30, 310, 290, 280, "Move Score"),
            TutorialHighlight(335, 310, 205, 145, "Ratio"),
        ),
    ),
    TutorialStep(
        title="Type Badges Are Clickable",
        filename="02_recommendation_card.png",
        image_width=570,
        image_height=942,
        paragraphs=(
            "Click or tap a Pokémon's type badge to see its defensive weaknesses, resistances, and immunities. Dual types are combined automatically.",
            "Move-type badges are clickable too. Those show that move type's offensive effectiveness.",
        ),
        highlights=(
            TutorialHighlight(255, 190, 235, 48, "Pokémon type"),
            TutorialHighlight(45, 405, 190, 48, "Move type"),
        ),
    ),
    TutorialStep(
        title="Why, Notes, and Full Analysis",
        filename="02_recommendation_card.png",
        image_width=570,
        image_height=942,
        paragraphs=(
            "Why this Pokémon? gives you the plain-English reason behind the recommendation.",
            "Battle Notes flag important tactical details such as likely OHKOs, priority moves, contact risks, or mechanics that depend on battle state.",
            "Use the Full Analysis link when you want to compare the entire team instead of only the top recommendation.",
        ),
        highlights=(
            TutorialHighlight(30, 610, 510, 145, "Why + Full Analysis"),
            TutorialHighlight(30, 770, 510, 145, "Battle Notes"),
        ),
    ),
    TutorialStep(
        title="Keep My Team Accurate",
        filename="06_my_team_editor.png",
        image_width=1240,
        image_height=730,
        paragraphs=(
            "My Team is where you tell Battle Compass about level-ups, new moves, changed stats, Abilities, Held Items, and party changes. The engine can only recommend from the information you give it.",
            "Save Team is an intentional proofreading checkpoint: edit freely, then save when the row data matches the game.",
            "Export Journey creates a portable backup. Load Journey restores one later, which is especially useful before moving between devices or browsers.",
        ),
        highlights=(
            TutorialHighlight(35, 195, 1170, 400, "Team Editor"),
            TutorialHighlight(430, 608, 155, 42, "Save Team"),
            TutorialHighlight(790, 608, 160, 42, "Export"),
            TutorialHighlight(965, 608, 160, 42, "Load"),
        ),
    ),
    TutorialStep(
        title="Pokémon Details",
        filename="07_pokemon_details.png",
        image_width=955,
        image_height=917,
        paragraphs=(
            "Pokémon Details turns the saved team data into a quick reference. Review stats and Nature effects, select move cards for move details, and click Ability or Held Item for descriptions.",
            "The Pokémon type badges here are clickable too, using the same defensive matchup popup as the Battle Compass.",
        ),
        highlights=(
            TutorialHighlight(530, 180, 245, 95, "Type badges"),
            TutorialHighlight(50, 650, 850, 120, "Moves"),
            TutorialHighlight(50, 785, 850, 90, "Ability + Held Item"),
        ),
    ),
    TutorialStep(
        title="Evolving a Team Member",
        filename="11_evolution_ready.png",
        image_width=932,
        image_height=417,
        paragraphs=(
            "When a Pokémon has a known next evolution, Pokémon Details shows its evolution requirement and an Evolve! button.",
            "Level-based evolutions can also prompt automatically when you save a newly eligible level. Special evolutions remain available from this button whenever you know the evolution happened in-game.",
            "Battle Compass never guesses the evolved Pokémon's new stats, moves, or Ability. After evolving, update those details from your game and save the team again.",
        ),
        highlights=(
            TutorialHighlight(515, 285, 195, 105, "Next Evolution"),
        ),
    ),
    TutorialStep(
        title="Track the Journey",
        filename="08_my_journey_overview.png",
        image_width=1225,
        image_height=1037,
        paragraphs=(
            "My Journey keeps the strategic side of a playthrough together. Current Objectives surfaces the highest-priority things available now, while the Badge Tracker controls progression through Galar.",
            "The Journey Checklist tracks planned Pokémon, items, TMs, and TRs. The map uses that same progression state so unavailable objectives stay locked until the required badge has been earned.",
        ),
        highlights=(
            TutorialHighlight(0, 0, 605, 710, "Objectives + Checklist"),
            TutorialHighlight(620, 0, 605, 710, "Badges + Map"),
        ),
    ),
    TutorialStep(
        title="Plan the Team",
        filename="12_team_planner.png",
        image_width=1235,
        image_height=482,
        paragraphs=(
            (
                "Team Planner keeps your intended final team tied to the actual "
                "playthrough. Add the Pokémon you plan to use and Battle Compass "
                "will show acquisition guidance, encounter options, and evolution "
                "notes for each one."
            ),
            (
                "The status icon shows whether that Pokémon is currently available "
                "at your Badge count. View locations opens the known encounter "
                "options, while Mark as acquired records that you have actually "
                "caught or obtained it."
            ),
            (
                "Team Planner favors the earliest curated Sword acquisition route, "
                "including earlier Max Raid access when that makes a Pokémon "
                "available sooner than its ordinary encounter locations."
            ),
        ),
        highlights=(
            TutorialHighlight(35, 125, 745, 320, "Acquisition guidance"),
            TutorialHighlight(780, 210, 185, 185, "Mark as acquired"),
            TutorialHighlight(615, 210, 175, 185, "View locations"),
        ),
    ),
    TutorialStep(
        title="Checklist to Map",
        filename="09_map_move_to_map.png",
        image_width=1235,
        image_height=1027,
        paragraphs=(
            "Checklist rows and map markers are linked. Select an objective to focus it; selecting it again can move you directly to the corresponding place on the Galar map.",
            "Marker filters let you reduce map clutter when you only want to see a particular kind of objective.",
        ),
        highlights=(
            TutorialHighlight(30, 220, 550, 135, "Checklist objective"),
            TutorialHighlight(650, 125, 545, 875, "Map"),
        ),
    ),
    TutorialStep(
        title="Plan Moves Ahead",
        filename="10_move_planner.png",
        image_width=1225,
        image_height=677,
        paragraphs=(
            "Move Planner lets you sketch each planned team member's final four moves. Choose a level-up move directly, or choose a TM/TR version when the move needs an item.",
            "Required TMs and TRs are automatically added to the Journey Checklist, tying move planning directly into acquisition planning.",
        ),
        highlights=(
            TutorialHighlight(30, 175, 1090, 490, "Planned moves"),
        ),
    ),
    TutorialStep(
        title="You're Ready!",
        filename="08_my_journey_overview.png",
        image_width=1225,
        image_height=1037,
        paragraphs=(
            (
                "That's the tour! You now know where Battle Compass gets its "
                "recommendations, how to keep your team information accurate, "
                "and how My Journey can help you plan the road ahead."
            ),
            (
                "If you ever want a refresher, head to About and choose "
                "Show Tutorial Again. The whole walkthrough will be waiting "
                "for you."
            ),
            (
                "Good luck on your Journey. May your matchups be favorable, "
                "your crits arrive exactly when needed, and your favorite "
                "Pokémon occasionally ignore the math and win anyway. :-)"
            ),
        ),
    ),
)


class TutorialController:
    def __init__(
        self,
        *,
        page: ft.Page,
        on_completed: TutorialCompletedCallback,
    ) -> None:
        self.page = page
        self.on_completed = on_completed
        self.current_index = 0
        self._dialog: ft.AlertDialog | None = None
        self._is_active = False

    def start(self) -> None:
        if self._is_active:
            return
        self._is_active = True
        self.current_index = 0
        self._show_step()

    def _asset_src(self, filename: str) -> str:
        if sys.platform == "emscripten":
            return f"tutorial/{filename}"
        return str(ASSETS_DIR / "tutorial" / filename)

    def _show_step(self) -> None:
        if not self._is_active:
            return
        if not 0 <= self.current_index < len(TUTORIAL_STEPS):
            self.page.run_task(self._finish)
            return
        if self._dialog is not None:
            try:
                self.page.pop_dialog()
            except (RuntimeError, ValueError):
                pass
        self._dialog = self._build_dialog(TUTORIAL_STEPS[self.current_index])
        self.page.show_dialog(self._dialog)

    def _build_dialog(self, step: TutorialStep) -> ft.AlertDialog:
        viewport_width = max(float(self.page.width or 1000), 360.0)
        viewport_height = max(float(self.page.height or 800), 560.0)
        content_width = min(1080.0, viewport_width - 110.0)
        content_height = min(720.0, viewport_height - 210.0)

        return ft.AlertDialog(
            modal=True,
            title=self._build_header(step),
            content=ft.Container(
                content=ft.Column(
                    controls=cast(
                        list[ft.Control],
                        [
                            self._build_explanation(step),
                            self._build_screenshot(
                                step,
                                available_width=content_width - 20,
                            ),
                        ],
                    ),
                    spacing=16,
                    scroll=ft.ScrollMode.AUTO,
                ),
                width=content_width,
                height=content_height,
            ),
            actions=cast(
                list[ft.Control],
                [
                    ft.Button(
                        content="Skip Tour",
                        on_click=self._skip_button,
                    ),
                    ft.Button(
                        content="Back",
                        icon=ft.Icons.ARROW_BACK_ROUNDED,
                        disabled=self.current_index == 0,
                        on_click=self._back,
                    ),
                    ft.Button(
                        content=(
                            "Finish"
                            if self.current_index == len(TUTORIAL_STEPS) - 1
                            else "Next"
                        ),
                        icon=(
                            ft.Icons.CHECK_ROUNDED
                            if self.current_index == len(TUTORIAL_STEPS) - 1
                            else ft.Icons.ARROW_FORWARD_ROUNDED
                        ),
                        bgcolor=PRIMARY_BLUE,
                        color=TEXT_PRIMARY,
                        icon_color=TEXT_PRIMARY,
                        on_click=(
                            self._finish_from_button
                            if self.current_index == len(TUTORIAL_STEPS) - 1
                            else self._next
                        ),
                    ),
                ],
            ),
            actions_alignment=ft.MainAxisAlignment.END,
            bgcolor=SURFACE,
        )

    def _build_header(self, step: TutorialStep) -> ft.Control:
        return ft.Row(
            controls=cast(
                list[ft.Control],
                [
                    ft.Container(
                        content=ft.Icon(
                            ft.Icons.SCHOOL_OUTLINED,
                            size=22,
                            color=PRIMARY_BLUE,
                        ),
                        width=40,
                        height=40,
                        alignment=ft.Alignment.CENTER,
                        bgcolor=PRIMARY_BLUE_SOFT,
                        border_radius=10,
                    ),
                    ft.Column(
                        controls=cast(
                            list[ft.Control],
                            [
                                ft.Text(
                                    step.title,
                                    size=21,
                                    weight=ft.FontWeight.BOLD,
                                    font_family=FONT_FAMILY_HEADER,
                                    color=TEXT_PRIMARY,
                                ),
                                ft.Text(
                                    f"Tutorial · Step {self.current_index + 1} of {len(TUTORIAL_STEPS)}",
                                    size=12,
                                    color=TEXT_MUTED,
                                ),
                            ],
                        ),
                        spacing=2,
                        tight=True,
                        expand=True,
                    ),
                    ft.IconButton(
                        icon=ft.Icons.CLOSE_ROUNDED,
                        icon_color=TEXT_MUTED,
                        tooltip="Skip tutorial",
                        on_click=self._skip_icon,
                    ),
                ],
            ),
            spacing=12,
            vertical_alignment=ft.CrossAxisAlignment.CENTER,
        )

    def _build_screenshot(
        self,
        step: TutorialStep,
        *,
        available_width: float,
    ) -> ft.Control:
        scale = min(
            available_width / float(step.image_width),
            1.0,
        )
        display_width = step.image_width * scale
        display_height = step.image_height * scale

        controls: list[ft.Control] = [
            ft.Image(
                src=self._asset_src(step.filename),
                width=display_width,
                height=display_height,
                fit=ft.BoxFit.CONTAIN,
                semantics_label=step.title,
            )
        ]

        for index, highlight in enumerate(step.highlights, start=1):
            controls.append(
                ft.Container(
                    left=highlight.x * scale,
                    top=highlight.y * scale,
                    width=max(18.0, highlight.width * scale),
                    height=max(18.0, highlight.height * scale),
                    border=ft.Border.all(3, PRIMARY_BLUE),
                    border_radius=8,
                    shadow=ft.BoxShadow(
                        blur_radius=14,
                        spread_radius=1,
                        color=ft.Colors.with_opacity(
                            0.55,
                            PRIMARY_BLUE,
                        ),
                    ),
                )
            )
            if highlight.label:
                controls.append(
                    ft.Container(
                        left=highlight.x * scale,
                        top=max(0.0, (highlight.y * scale) - 26.0),
                        content=ft.Text(
                            f"{index}. {highlight.label}",
                            size=11,
                            weight=ft.FontWeight.BOLD,
                            color=TEXT_PRIMARY,
                            no_wrap=True,
                        ),
                        padding=ft.Padding.symmetric(
                            horizontal=7,
                            vertical=4,
                        ),
                        bgcolor=ft.Colors.with_opacity(0.96, PRIMARY_BLUE),
                        border_radius=7,
                    )
                )

        return ft.Container(
            content=ft.Stack(
                controls=controls,
                width=display_width,
                height=display_height,
            ),
            alignment=ft.Alignment.CENTER,
            padding=10,
            bgcolor=SURFACE_RAISED,
            border=ft.Border.all(1, BORDER_DEFAULT),
            border_radius=12,
        )

    @staticmethod
    def _build_explanation(step: TutorialStep) -> ft.Control:
        return ft.Column(
            controls=cast(
                list[ft.Control],
                [
                    ft.Text(
                        paragraph,
                        size=14,
                        color=TEXT_SECONDARY,
                    )
                    for paragraph in step.paragraphs
                ],
            ),
            spacing=10,
        )

    def _next(self, event: ft.Event[ft.Button]) -> None:
        del event
        self.current_index += 1
        self._show_step()

    def _back(self, event: ft.Event[ft.Button]) -> None:
        del event
        self.current_index = max(0, self.current_index - 1)
        self._show_step()

    def _skip_button(self, event: ft.Event[ft.Button]) -> None:
        del event
        self.page.run_task(self._finish)

    def _skip_icon(self, event: ft.Event[ft.IconButton]) -> None:
        del event
        self.page.run_task(self._finish)

    def _finish_from_button(self, event: ft.Event[ft.Button]) -> None:
        del event
        self.page.run_task(self._finish)

    async def _finish(self) -> None:
        self._is_active = False
        if self._dialog is not None:
            try:
                self.page.pop_dialog()
            except (RuntimeError, ValueError):
                pass
        self._dialog = None
        self.page.update()
        try:
            await self.on_completed()
        except (RuntimeError, ValueError):
            pass
