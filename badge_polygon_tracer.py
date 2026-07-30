from __future__ import annotations

import json
import tkinter as tk
from pathlib import Path
from tkinter import filedialog, messagebox, ttk
from typing import Any

from PIL import Image, ImageDraw, ImageTk


BADGE_ORDER = [
    "Grass Badge",
    "Water Badge",
    "Fire Badge",
    "Fighting Badge",
    "Fairy Badge",
    "Rock Badge",
    "Dark Badge",
    "Dragon Badge",
]

DEFAULT_IMAGE_NAME = "SwordBadges.png"
DEFAULT_OUTPUT_NAME = "badge_polygons.json"


class BadgePolygonTracer:
    """Small desktop tool for manually tracing badge polygons."""

    def __init__(self, root: tk.Tk) -> None:
        self.root = root
        self.root.title("Pokémon Battle Compass — Badge Polygon Tracer")
        self.root.geometry("1280x980")
        self.root.minsize(980, 760)

        self.image_path: Path | None = None
        self.original_image: Image.Image | None = None
        self.display_image: ImageTk.PhotoImage | None = None

        self.scale = 1.0
        self.canvas_image_id: int | None = None
        self.points: list[tuple[int, int]] = []
        self.saved_polygons: dict[str, list[list[int]]] = {}

        self.badge_var = tk.StringVar(value=BADGE_ORDER[0])
        self.status_var = tk.StringVar(
            value="Open SwordBadges.png to begin."
        )
        self.point_count_var = tk.StringVar(value="0 points")
        self.close_preview_var = tk.BooleanVar(value=True)

        self._build_ui()
        self._bind_shortcuts()
        self._try_open_default_image()

    def _build_ui(self) -> None:
        top = ttk.Frame(self.root, padding=10)
        top.pack(fill=tk.X)

        ttk.Button(
            top,
            text="Open Badge Sheet",
            command=self.open_image,
        ).pack(side=tk.LEFT)

        ttk.Label(top, text="Badge:").pack(side=tk.LEFT, padx=(18, 6))

        badge_combo = ttk.Combobox(
            top,
            textvariable=self.badge_var,
            values=BADGE_ORDER,
            state="readonly",
            width=20,
        )
        badge_combo.pack(side=tk.LEFT)
        badge_combo.bind("<<ComboboxSelected>>", self._badge_changed)

        ttk.Checkbutton(
            top,
            text="Close polygon in preview",
            variable=self.close_preview_var,
            command=self.redraw,
        ).pack(side=tk.LEFT, padx=(18, 0))

        ttk.Label(
            top,
            textvariable=self.point_count_var,
        ).pack(side=tk.RIGHT)

        controls = ttk.Frame(self.root, padding=(10, 0, 10, 10))
        controls.pack(fill=tk.X)

        ttk.Button(
            controls,
            text="Undo Last Point",
            command=self.undo_last_point,
        ).pack(side=tk.LEFT)

        ttk.Button(
            controls,
            text="Clear Current",
            command=self.clear_current,
        ).pack(side=tk.LEFT, padx=(8, 0))

        ttk.Button(
            controls,
            text="Save Current Polygon",
            command=self.save_current_polygon,
        ).pack(side=tk.LEFT, padx=(18, 0))

        ttk.Button(
            controls,
            text="Save & Next Badge",
            command=self.save_and_next,
        ).pack(side=tk.LEFT, padx=(8, 0))

        ttk.Button(
            controls,
            text="Load Existing JSON",
            command=self.load_polygons_json,
        ).pack(side=tk.LEFT, padx=(18, 0))

        ttk.Button(
            controls,
            text="Export All JSON",
            command=self.export_polygons_json,
        ).pack(side=tk.LEFT, padx=(8, 0))

        ttk.Button(
            controls,
            text="Export Preview PNG",
            command=self.export_preview_png,
        ).pack(side=tk.LEFT, padx=(8, 0))

        canvas_frame = ttk.Frame(self.root, padding=(10, 0, 10, 0))
        canvas_frame.pack(fill=tk.BOTH, expand=True)

        self.canvas = tk.Canvas(
            canvas_frame,
            background="#1b1f28",
            highlightthickness=0,
            cursor="crosshair",
        )
        self.canvas.pack(fill=tk.BOTH, expand=True)

        self.canvas.bind("<Button-1>", self.add_point)
        self.canvas.bind("<Button-3>", lambda _event: self.undo_last_point())
        self.canvas.bind("<Configure>", lambda _event: self._fit_image())

        bottom = ttk.Frame(self.root, padding=10)
        bottom.pack(fill=tk.X)

        ttk.Label(
            bottom,
            text=(
                "Left-click: add point   •   Right-click/Ctrl+Z: undo   •   "
                "Ctrl+S: save polygon   •   Ctrl+E: export JSON"
            ),
        ).pack(anchor=tk.W)

        ttk.Label(
            bottom,
            textvariable=self.status_var,
            foreground="#365f9b",
        ).pack(anchor=tk.W, pady=(4, 0))

    def _bind_shortcuts(self) -> None:
        self.root.bind("<Control-z>", lambda _event: self.undo_last_point())
        self.root.bind("<Control-s>", lambda _event: self.save_current_polygon())
        self.root.bind("<Control-e>", lambda _event: self.export_polygons_json())
        self.root.bind("<Delete>", lambda _event: self.clear_current())

    def _try_open_default_image(self) -> None:
        candidates = [
            Path.cwd() / "assets" / DEFAULT_IMAGE_NAME,
            Path.cwd() / DEFAULT_IMAGE_NAME,
            Path(__file__).resolve().parent / "assets" / DEFAULT_IMAGE_NAME,
            Path(__file__).resolve().parent / DEFAULT_IMAGE_NAME,
        ]

        for candidate in candidates:
            if candidate.exists():
                self._load_image(candidate)
                return

    def open_image(self) -> None:
        selected = filedialog.askopenfilename(
            title="Open Sword badge sheet",
            filetypes=[
                ("PNG images", "*.png"),
                ("All files", "*.*"),
            ],
        )
        if selected:
            self._load_image(Path(selected))

    def _load_image(self, path: Path) -> None:
        try:
            image = Image.open(path).convert("RGBA")
        except Exception as error:
            messagebox.showerror(
                "Could not open image",
                str(error),
            )
            return

        self.image_path = path
        self.original_image = image
        self.points = []
        self.status_var.set(
            f"Loaded {path.name} ({image.width} × {image.height})."
        )
        self._fit_image()

    def _fit_image(self) -> None:
        if self.original_image is None:
            return

        canvas_width = max(1, self.canvas.winfo_width())
        canvas_height = max(1, self.canvas.winfo_height())

        available_width = max(1, canvas_width - 30)
        available_height = max(1, canvas_height - 30)

        self.scale = min(
            available_width / self.original_image.width,
            available_height / self.original_image.height,
        )

        display_size = (
            max(1, round(self.original_image.width * self.scale)),
            max(1, round(self.original_image.height * self.scale)),
        )

        resized = self.original_image.resize(
            display_size,
            Image.Resampling.LANCZOS,
        )
        self.display_image = ImageTk.PhotoImage(resized)
        self.redraw()

    def _image_origin(self) -> tuple[float, float]:
        if self.original_image is None:
            return 0.0, 0.0

        displayed_width = self.original_image.width * self.scale
        displayed_height = self.original_image.height * self.scale

        origin_x = (self.canvas.winfo_width() - displayed_width) / 2
        origin_y = (self.canvas.winfo_height() - displayed_height) / 2
        return origin_x, origin_y

    def _canvas_to_image(
        self,
        canvas_x: float,
        canvas_y: float,
    ) -> tuple[int, int] | None:
        if self.original_image is None:
            return None

        origin_x, origin_y = self._image_origin()
        image_x = (canvas_x - origin_x) / self.scale
        image_y = (canvas_y - origin_y) / self.scale

        if not (
            0 <= image_x < self.original_image.width
            and 0 <= image_y < self.original_image.height
        ):
            return None

        return round(image_x), round(image_y)

    def _image_to_canvas(
        self,
        image_x: int,
        image_y: int,
    ) -> tuple[float, float]:
        origin_x, origin_y = self._image_origin()
        return (
            origin_x + image_x * self.scale,
            origin_y + image_y * self.scale,
        )

    def add_point(self, event: tk.Event[Any]) -> None:
        point = self._canvas_to_image(event.x, event.y)
        if point is None:
            return

        self.points.append(point)
        self.point_count_var.set(f"{len(self.points)} points")
        self.status_var.set(
            f"Added point {len(self.points)} at {point}."
        )
        self.redraw()

    def undo_last_point(self) -> None:
        if not self.points:
            return

        removed = self.points.pop()
        self.point_count_var.set(f"{len(self.points)} points")
        self.status_var.set(f"Removed point {removed}.")
        self.redraw()

    def clear_current(self) -> None:
        if not self.points:
            return

        if not messagebox.askyesno(
            "Clear current trace?",
            "Remove all unsaved points for this badge?",
        ):
            return

        self.points = []
        self.point_count_var.set("0 points")
        self.status_var.set("Current trace cleared.")
        self.redraw()

    def redraw(self) -> None:
        self.canvas.delete("all")

        if self.display_image is None or self.original_image is None:
            self.canvas.create_text(
                self.canvas.winfo_width() / 2,
                self.canvas.winfo_height() / 2,
                text="Open SwordBadges.png to begin.",
                fill="#d4d8e2",
                font=("Segoe UI", 16),
            )
            return

        origin_x, origin_y = self._image_origin()
        self.canvas_image_id = self.canvas.create_image(
            origin_x,
            origin_y,
            anchor=tk.NW,
            image=self.display_image,
        )

        if not self.points:
            return

        canvas_points = [
            self._image_to_canvas(x, y)
            for x, y in self.points
        ]

        line_points = list(canvas_points)
        if (
            self.close_preview_var.get()
            and len(canvas_points) >= 3
        ):
            line_points.append(canvas_points[0])

        if len(line_points) >= 2:
            flattened = [
                coordinate
                for point in line_points
                for coordinate in point
            ]
            self.canvas.create_line(
                *flattened,
                fill="#00e5ff",
                width=3,
            )

        for index, (x, y) in enumerate(canvas_points, start=1):
            radius = 5
            self.canvas.create_oval(
                x - radius,
                y - radius,
                x + radius,
                y + radius,
                fill="#ffffff",
                outline="#00a7c4",
                width=2,
            )
            self.canvas.create_text(
                x + 10,
                y - 10,
                text=str(index),
                fill="#ffffff",
                font=("Segoe UI", 9, "bold"),
                anchor=tk.W,
            )

    def _badge_changed(self, _event: tk.Event[Any]) -> None:
        badge_name = self.badge_var.get()
        saved = self.saved_polygons.get(badge_name)

        if saved:
            self.points = [
                (int(point[0]), int(point[1]))
                for point in saved
            ]
            self.status_var.set(
                f"Loaded saved trace for {badge_name}."
            )
        else:
            self.points = []
            self.status_var.set(
                f"Ready to trace {badge_name}."
            )

        self.point_count_var.set(f"{len(self.points)} points")
        self.redraw()

    def save_current_polygon(self) -> bool:
        if self.original_image is None:
            messagebox.showwarning(
                "No image",
                "Open the badge sheet first.",
            )
            return False

        if len(self.points) < 3:
            messagebox.showwarning(
                "Not enough points",
                "A polygon needs at least three points.",
            )
            return False

        badge_name = self.badge_var.get()
        self.saved_polygons[badge_name] = [
            [x, y]
            for x, y in self.points
        ]
        self.status_var.set(
            f"Saved {badge_name} with {len(self.points)} points."
        )
        return True

    def save_and_next(self) -> None:
        if not self.save_current_polygon():
            return

        current_index = BADGE_ORDER.index(self.badge_var.get())
        if current_index >= len(BADGE_ORDER) - 1:
            self.status_var.set(
                "Final badge saved. Export the completed JSON."
            )
            return

        next_badge = BADGE_ORDER[current_index + 1]
        self.badge_var.set(next_badge)
        self._badge_changed(None)  # type: ignore[arg-type]

    def export_polygons_json(self) -> None:
        self.save_current_polygon()

        if not self.saved_polygons:
            messagebox.showwarning(
                "Nothing to export",
                "Trace and save at least one badge first.",
            )
            return

        default_dir = (
            self.image_path.parent
            if self.image_path is not None
            else Path.cwd()
        )

        selected = filedialog.asksaveasfilename(
            title="Export badge polygon coordinates",
            initialdir=default_dir,
            initialfile=DEFAULT_OUTPUT_NAME,
            defaultextension=".json",
            filetypes=[("JSON files", "*.json")],
        )
        if not selected:
            return

        payload = {
            "source_image": (
                self.image_path.name
                if self.image_path is not None
                else DEFAULT_IMAGE_NAME
            ),
            "image_width": (
                self.original_image.width
                if self.original_image is not None
                else None
            ),
            "image_height": (
                self.original_image.height
                if self.original_image is not None
                else None
            ),
            "badge_order": BADGE_ORDER,
            "polygons": {
                badge: self.saved_polygons.get(badge, [])
                for badge in BADGE_ORDER
            },
        }

        Path(selected).write_text(
            json.dumps(payload, indent=2),
            encoding="utf-8",
        )
        self.status_var.set(
            f"Exported polygon coordinates to {selected}."
        )
        messagebox.showinfo(
            "Export complete",
            f"Saved:\n{selected}",
        )

    def load_polygons_json(self) -> None:
        selected = filedialog.askopenfilename(
            title="Load badge polygon coordinates",
            filetypes=[("JSON files", "*.json")],
        )
        if not selected:
            return

        try:
            payload = json.loads(
                Path(selected).read_text(encoding="utf-8")
            )
            polygons = payload.get("polygons", payload)
            if not isinstance(polygons, dict):
                raise ValueError(
                    "JSON does not contain a polygon dictionary."
                )

            loaded: dict[str, list[list[int]]] = {}
            for badge_name in BADGE_ORDER:
                raw_points = polygons.get(badge_name, [])
                if not isinstance(raw_points, list):
                    continue

                valid_points: list[list[int]] = []
                for point in raw_points:
                    if (
                        isinstance(point, list)
                        and len(point) == 2
                        and all(
                            isinstance(value, (int, float))
                            for value in point
                        )
                    ):
                        valid_points.append(
                            [round(point[0]), round(point[1])]
                        )

                if valid_points:
                    loaded[badge_name] = valid_points

            self.saved_polygons = loaded
            self._badge_changed(None)  # type: ignore[arg-type]
            self.status_var.set(
                f"Loaded polygon coordinates from {selected}."
            )
        except Exception as error:
            messagebox.showerror(
                "Could not load JSON",
                str(error),
            )

    def export_preview_png(self) -> None:
        if self.original_image is None:
            messagebox.showwarning(
                "No image",
                "Open the badge sheet first.",
            )
            return

        if len(self.points) < 3:
            messagebox.showwarning(
                "Not enough points",
                "Trace at least three points first.",
            )
            return

        preview = self.original_image.copy()
        overlay = Image.new(
            "RGBA",
            preview.size,
            (0, 0, 0, 0),
        )
        draw = ImageDraw.Draw(overlay)
        draw.polygon(
            self.points,
            fill=(0, 229, 255, 70),
            outline=(0, 229, 255, 255),
            width=4,
        )
        preview = Image.alpha_composite(preview, overlay)

        default_dir = (
            self.image_path.parent
            if self.image_path is not None
            else Path.cwd()
        )
        safe_name = (
            self.badge_var.get()
            .lower()
            .replace(" ", "_")
        )

        selected = filedialog.asksaveasfilename(
            title="Export polygon preview",
            initialdir=default_dir,
            initialfile=f"{safe_name}_preview.png",
            defaultextension=".png",
            filetypes=[("PNG images", "*.png")],
        )
        if not selected:
            return

        preview.save(selected)
        self.status_var.set(
            f"Exported preview to {selected}."
        )


def main() -> None:
    root = tk.Tk()
    BadgePolygonTracer(root)
    root.mainloop()


if __name__ == "__main__":
    main()