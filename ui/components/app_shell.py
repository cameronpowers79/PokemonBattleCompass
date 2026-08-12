from __future__ import annotations

import asyncio

from collections.abc import Callable

import flet as ft

from ui.theme import (
    APP_BACKGROUND,
    BORDER_DEFAULT,
    CONTENT_MAX_WIDTH,
    PAGE_PADDING_DESKTOP,
    PAGE_PADDING_MOBILE,
    PRIMARY_BLUE,
    SURFACE,
    TEXT_MUTED,
    TEXT_PRIMARY,
    TEXT_SECONDARY,
)


ViewBuilder = Callable[[], ft.Control]
DirtyStateCheck = Callable[[], bool]
DiscardChanges = Callable[[], None]
ViewChanged = Callable[[str], None]


class AppShell:
    """Shared Battle Compass layout and primary navigation."""

    MOBILE_BREAKPOINT = 700

    def __init__(
        self,
        page: ft.Page,
        battle_compass_view: ViewBuilder,
        my_team_view: ViewBuilder,
        my_journey_view: ViewBuilder,
        about_view: ViewBuilder,
        *,
        initial_view: str = "battle_compass",
        on_view_changed: ViewChanged | None = None,
        my_team_has_unsaved_changes: (
            DirtyStateCheck | None
        ) = None,
        discard_my_team_changes: (
            DiscardChanges | None
        ) = None,
    ) -> None:
        self.page = page

        self.view_builders = {
            "battle_compass": battle_compass_view,
            "my_team": my_team_view,
            "my_journey": my_journey_view,
            "about": about_view,
        }

        self.on_view_changed = on_view_changed

        self.my_team_has_unsaved_changes = (
            my_team_has_unsaved_changes
        )
        self.discard_my_team_changes = (
            discard_my_team_changes
        )

        self.active_view = (
            initial_view
            if initial_view in self.view_builders
            else "battle_compass"
        )
        self.pending_view: str | None = None
        self._my_journey_overlay_controls: list[ft.Control] = []
        self._return_to_top_threshold = 600.0
        self._return_to_top_overlay = self._build_return_to_top_overlay()
        self._return_to_top_is_attached = False

        # Live metrics from the shell-owned scrollable Column. These let
        # programmatic navigation center a real scroll target without making
        # assumptions about screen width or the responsive layout above it.
        self._scroll_pixels = 0.0
        self._scroll_viewport_dimension = 0.0
        self._scroll_min_extent = 0.0
        self._scroll_max_extent = 0.0

        self.content_host = ft.Container(
            content=self.view_builders[
                self.active_view
            ](),
            width=CONTENT_MAX_WIDTH,
            alignment=ft.Alignment.TOP_CENTER,
        )

        self.battle_compass_button = ft.Button(
            content="Battle Compass",
            icon=ft.Icons.EXPLORE_OUTLINED,
            on_click=(
                lambda event:
                self._request_view_change(
                    event,
                    "battle_compass",
                )
            ),
        )

        self.my_team_button = ft.Button(
            content="My Team",
            icon=ft.Icons.GROUP_OUTLINED,
            on_click=(
                lambda event:
                self._request_view_change(
                    event,
                    "my_team",
                )
            ),
        )

        self.my_journey_button = ft.Button(
            content="My Journey",
            icon=ft.Icons.ROUTE_OUTLINED,
            on_click=(
                lambda event:
                self._request_view_change(
                    event,
                    "my_journey",
                )
            ),
        )

        self.about_button = ft.Button(
            content="About",
            icon=ft.Icons.INFO_OUTLINE_ROUNDED,
            on_click=(
                lambda event:
                self._request_view_change(
                    event,
                    "about",
                )
            ),
        )

        self.navigation = ft.Row(
            controls=[
                self.battle_compass_button,
                self.my_team_button,
                self.my_journey_button,
                self.about_button,
            ],
            alignment=ft.MainAxisAlignment.CENTER,
            spacing=12,
            wrap=True,
        )

        self.page_container = ft.Container(
            content=ft.SafeArea(
                content=ft.Column(
                    controls=[
                        self.build_branding_header(),
                        self.navigation,
                        ft.Divider(
                            color=BORDER_DEFAULT,
                            height=1,
                        ),
                        self.content_host,
                    ],
                    spacing=24,
                    horizontal_alignment=(
                        ft.CrossAxisAlignment.CENTER
                    ),
                )
            ),
            width=CONTENT_MAX_WIDTH,
            padding=PAGE_PADDING_DESKTOP,
            alignment=ft.Alignment.TOP_CENTER,
        )

        self.scroll_host = ft.Column(
            controls=[self.page_container],
            expand=True,
            scroll=ft.ScrollMode.AUTO,
            on_scroll=self._handle_shell_scroll,
            horizontal_alignment=ft.CrossAxisAlignment.CENTER,
        )

        self.update_navigation_style()
        self._sync_my_journey_overlay_visibility()

        self.apply_responsive_layout(
            self.page.width or 1000
        )

    def _build_return_to_top_overlay(self) -> ft.Container:
        """Build the floating Return to Top control."""

        overlay = ft.Container(
            key="app-return-to-top-overlay",
            content=ft.IconButton(
                icon=ft.Icons.ARROW_UPWARD_ROUNDED,
                icon_color=TEXT_PRIMARY,
                tooltip="Return to top",
                on_click=lambda: self.page.run_task(
                    self._scroll_to_top
                ),
            ),
            width=52,
            height=52,
            alignment=ft.Alignment.CENTER,
            bgcolor=ft.Colors.with_opacity(0.96, SURFACE),
            border=ft.Border.all(1, BORDER_DEFAULT),
            border_radius=26,
            shadow=ft.BoxShadow(
                blur_radius=18,
                spread_radius=1,
                color=ft.Colors.with_opacity(
                    0.35,
                    ft.Colors.BLACK,
                ),
                offset=ft.Offset(0, 6),
            ),
        )
        overlay.right = 24
        overlay.bottom = 92
        return overlay

    def _set_return_to_top_attached(
        self,
        should_attach: bool,
    ) -> None:
        """Attach or remove the button only when its state changes."""

        if should_attach == self._return_to_top_is_attached:
            return

        if should_attach:
            if self._return_to_top_overlay not in self.page.overlay:
                self.page.overlay.append(self._return_to_top_overlay)
        elif self._return_to_top_overlay in self.page.overlay:
            self.page.overlay.remove(self._return_to_top_overlay)

        self._return_to_top_is_attached = should_attach
        self.page.update()

    def _handle_shell_scroll(
        self,
        event: ft.OnScrollEvent,
    ) -> None:
        """Track shell scroll metrics and toggle Return to Top."""

        self._scroll_pixels = float(event.pixels)
        self._scroll_viewport_dimension = float(event.viewport_dimension)
        self._scroll_min_extent = float(event.min_scroll_extent)
        self._scroll_max_extent = float(event.max_scroll_extent)

        self._set_return_to_top_attached(
            self._scroll_pixels >= self._return_to_top_threshold
        )

    async def scroll_to(
        self,
        *,
        offset: float | None = None,
        delta: float | None = None,
        scroll_key: ft.ScrollKey | str | int | float | bool | None = None,
        center_scroll_key: bool = False,
        duration: int = 0,
        curve: ft.AnimationCurve = ft.AnimationCurve.EASE,
    ) -> None:
        """Scroll the shell's shared content area.

        When ``center_scroll_key`` is True, first scroll to the real keyed
        control, then use the actual post-scroll position and viewport extent
        reported by ``on_scroll`` to center that target in the viewport.
        """

        await self.scroll_host.scroll_to(
            offset=offset,
            delta=delta,
            scroll_key=scroll_key,
            duration=duration,
            curve=curve,
        )

        if not center_scroll_key or scroll_key is None:
            return

        # Programmatic scrolling produces normal scroll notifications. Wait for
        # the keyed animation to finish so the stored metrics describe its true
        # landing position rather than an intermediate animation frame.
        await asyncio.sleep(max(0.05, (duration / 1000) + 0.05))

        viewport = self._scroll_viewport_dimension
        if viewport <= 0:
            viewport = float(self.page.height or 0)

        if viewport <= 0:
            return

        centered_offset = self._scroll_pixels - (viewport / 2)
        centered_offset = max(
            self._scroll_min_extent,
            min(centered_offset, self._scroll_max_extent),
        )

        # The first keyed jump gives us the target's real absolute position.
        # This second scroll only converts that measured position into centered
        # viewport placement; no responsive-layout dimensions are estimated.
        await self.scroll_host.scroll_to(
            offset=centered_offset,
            duration=min(280, max(160, duration // 2)),
            curve=curve,
        )

    async def _scroll_to_top(self) -> None:
        """Smoothly return the active page to its top."""

        await self.scroll_to(
            offset=0,
            duration=450,
            curve=ft.AnimationCurve.EASE_OUT_CUBIC,
        )
        self._set_return_to_top_attached(False)

    def build(self) -> ft.Control:
        """Return the complete application shell."""

        return ft.Container(
            content=self.scroll_host,
            expand=True,
            bgcolor=APP_BACKGROUND,
            alignment=ft.Alignment.TOP_CENTER,
        )

    @staticmethod
    def build_branding_header() -> ft.Control:
        """Build the shared application branding."""

        return ft.Column(
            controls=[
                ft.Image(
                    src="raw/BattleCompassLogo.png",
                    width=122,
                    fit=ft.BoxFit.CONTAIN,
                    semantics_label="Battle Compass logo",
                ),
                ft.Image(
                    src="raw/WordMarkLogoBlock.png",
                    width=760,
                    fit=ft.BoxFit.CONTAIN,
                    semantics_label="Pokémon Battle Compass",
                ),
                ft.Text(
                    "Navigate every matchup with confidence.",
                    size=17,
                    color=TEXT_SECONDARY,
                    text_align=ft.TextAlign.CENTER,
                ),
            ],
            spacing=8,
            horizontal_alignment=ft.CrossAxisAlignment.CENTER,
        )

    def _request_view_change(
        self,
        event: ft.Event[ft.Button],
        view_name: str,
    ) -> None:
        """Request navigation to another primary view."""

        del event

        if view_name == self.active_view:
            return

        leaving_dirty_team = (
            self.active_view == "my_team"
            and view_name != "my_team"
            and self.my_team_has_unsaved_changes
            is not None
            and self.my_team_has_unsaved_changes()
        )

        if not leaving_dirty_team:
            self.show_view(
                view_name
            )
            return

        self.pending_view = view_name

        self.page.show_dialog(
            self._build_unsaved_changes_dialog()
        )

    def _build_unsaved_changes_dialog(
        self,
    ) -> ft.AlertDialog:
        """Build the unsaved-team navigation warning."""

        return ft.AlertDialog(
            modal=True,
            title=ft.Text(
                "Leave without saving?",
                weight=ft.FontWeight.BOLD,
                color=TEXT_PRIMARY,
            ),
            content=ft.Text(
                (
                    "Your team has unsaved changes. "
                    "Leaving My Team now will discard them "
                    "and keep the last saved version of your "
                    "team in the Battle Compass."
                ),
                size=15,
                color=TEXT_SECONDARY,
            ),
            actions=[
                ft.Button(
                    content="Stay on My Team",
                    on_click=(
                        self._cancel_pending_navigation
                    ),
                ),
                ft.Button(
                    content="Discard Changes",
                    icon=ft.Icons.DELETE_OUTLINE_ROUNDED,
                    bgcolor=PRIMARY_BLUE,
                    color=TEXT_PRIMARY,
                    icon_color=TEXT_PRIMARY,
                    on_click=(
                        self._discard_and_continue
                    ),
                ),
            ],
            actions_alignment=ft.MainAxisAlignment.END,
        )

    def _cancel_pending_navigation(
        self,
        event: ft.Event[ft.Button],
    ) -> None:
        """Remain on My Team and preserve unsaved edits."""

        del event

        self.pending_view = None
        self.page.pop_dialog()
        self.page.update()

    def _discard_and_continue(
        self,
        event: ft.Event[ft.Button],
    ) -> None:
        """Discard unsaved team edits and continue navigation."""

        del event

        destination = self.pending_view
        self.pending_view = None

        self.page.pop_dialog()

        if self.discard_my_team_changes is not None:
            self.discard_my_team_changes()

        if destination is not None:
            self.show_view(
                destination
            )
            return

        self.page.update()

    def _sync_my_journey_overlay_visibility(self) -> None:
        """Attach the Move to Map pill only while My Journey is active.

        Mounted Flet controls are frozen, so visibility is controlled by
        adding or removing the overlay control from ``page.overlay`` rather
        than mutating its ``visible`` property after it has been mounted.
        """

        overlay_key = "my-journey-move-to-map-overlay"
        live_controls = [
            control
            for control in self.page.overlay
            if (
                isinstance(control, ft.Container)
                and control.key == overlay_key
            )
        ]

        for control in live_controls:
            if control not in self._my_journey_overlay_controls:
                self._my_journey_overlay_controls.append(control)

        if self.active_view == "my_journey":
            for control in self._my_journey_overlay_controls:
                if control not in self.page.overlay:
                    self.page.overlay.append(control)
            return

        for control in live_controls:
            self.page.overlay.remove(control)

    def show_view(
        self,
        view_name: str,
    ) -> None:
        """Switch the displayed primary application view."""

        if view_name == self.active_view:
            return

        if view_name not in self.view_builders:
            raise ValueError(
                f"Unknown application view: {view_name}"
            )

        self.active_view = view_name

        if self.on_view_changed is not None:
            self.on_view_changed(view_name)

        self.content_host.content = (
            self.view_builders[
                view_name
            ]()
        )

        self.page.run_task(
            self.scroll_to,
            offset=0,
            duration=0,
        )
        self._set_return_to_top_attached(False)
        self.update_navigation_style()
        self._sync_my_journey_overlay_visibility()
        self.page.update()

    def update_navigation_style(self) -> None:
        """Apply selected and unselected navigation styling."""

        buttons = {
            "battle_compass": (
                self.battle_compass_button
            ),
            "my_team": self.my_team_button,
            "my_journey": self.my_journey_button,
            "about": self.about_button,
        }

        for view_name, button in buttons.items():
            is_active = (
                view_name == self.active_view
            )

            button.bgcolor = (
                PRIMARY_BLUE
                if is_active
                else SURFACE
            )

            button.color = (
                TEXT_PRIMARY
                if is_active
                else TEXT_SECONDARY
            )

            button.icon_color = (
                TEXT_PRIMARY
                if is_active
                else TEXT_MUTED
            )

    def apply_responsive_layout(
        self,
        width: float,
    ) -> None:
        """Adjust spacing for narrow windows and mobile screens."""

        is_mobile = (
            width < self.MOBILE_BREAKPOINT
        )

        self.page_container.padding = (
            PAGE_PADDING_MOBILE
            if is_mobile
            else PAGE_PADDING_DESKTOP
        )

        self.navigation.spacing = (
            8
            if is_mobile
            else 12
        )