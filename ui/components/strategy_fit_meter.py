"""Compact five-section strategy fit indicator with continuous partial fill."""
import flet as ft

COLORS = {"Poor":"#D85B65", "Limited":"#DC944C", "Moderate":"#D9BE4A", "Good":"#68B995", "Excellent":"#31B984", "Flexible":"#A9B2C0"}

def strategy_fit_meter(fit, *, width: int = 225) -> ft.Control:
    color = COLORS.get(fit.label, "#A9B2C0")
    progress = max(0.0, min(1.0, float(fit.fraction))) * 5
    segments: list[ft.Control] = []
    for i in range(5):
        fill = max(0.0, min(1.0, progress-i))
        # Overlay independent proportional fill and neutral background.
        segments.append(ft.Container(width=(width-16)/5, height=12,
            bgcolor="#354052", border_radius=3,
            content=ft.Row(controls=[ft.Container(width=((width-16)/5)*fill, height=12,
                bgcolor=color, border_radius=3)], spacing=0)))
    return ft.Column(controls=[
        ft.Text(f"Strategy Fit: {fit.label}", size=12, weight=ft.FontWeight.BOLD, color=color),
        ft.Row(controls=segments, spacing=4, tight=True),
    ], spacing=4, tight=True)
