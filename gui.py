from __future__ import annotations

import random
import tkinter as tk
from tkinter import messagebox, ttk

from game_config import GameConfig, Payline
from screen_generator import Screen, build_screen, spin


EXAMPLE_CONFIG = GameConfig(
    name="Analytics Playground",
    reels=(
        ("A", "K", "Q", "J", "10", "A", "Q", "K"),
        ("K", "Q", "J", "10", "A", "K", "J", "Q"),
        ("Q", "J", "10", "A", "K", "Q", "10", "J"),
        ("J", "10", "A", "K", "Q", "J", "A", "10"),
        ("10", "A", "K", "Q", "J", "10", "K", "A"),
    ),
    visible_rows=3,
    paylines=(
        Payline("Top", (0, 0, 0, 0, 0)),
        Payline("Middle", (1, 1, 1, 1, 1)),
        Payline("Bottom", (2, 2, 2, 2, 2)),
        Payline("V", (0, 1, 2, 1, 0)),
        Payline("Inverted V", (2, 1, 0, 1, 2)),
        Payline("Top W", (0, 1, 0, 1, 0)),
        Payline("Top Inverted W", (1, 0, 1, 0, 1)),
        Payline("Lower W", (2, 1, 2, 1, 2)),
        Payline("Lower Inverted W", (1, 2, 1, 2, 1)),
        Payline("Upper Wave", (1, 1, 0, 1, 1)),
        Payline("Lower Wave", (1, 1, 2, 1, 1)),
    ),
)


class SlotScreenApp:
    """GUI for inspecting reel windows and configured paylines."""

    def __init__(
        self,
        root: tk.Tk,
        config: GameConfig,
        *,
        seed: int | None = None,
    ) -> None:
        self.root = root
        self.config = config
        self.rng = random.Random(seed)

        self.stop_variables = [
            tk.StringVar(value="0")
            for _ in range(config.n_reels)
        ]

        # GUI state: determines which configured paylines are displayed.
        self.payline_variables = [
            tk.BooleanVar(value=True)
            for _ in config.paylines
        ]

        self.status_variable = tk.StringVar(value="")
        self.is_spinning = False
        self.animation_delay_ms = 60
        self.animations_steps = 18

        self.current_screen: Screen | None = None
        self.current_stops: tuple[int, ...] | None = None

        # One color per configured payline.
        self.payline_colors = (
            "#ff0000",  # Top
            "#ff5300",  # Middle
            "#ffa500",  # Bottom
            "#ffd200",  # V
            "#ffff00",  # Inverted V
            "#80c000",  # Top W
            "#008000",  # Top Inverted W
            "#004080",  # Lower W
            "#0000ff",  # Lower Inverted W
            "#2600c1",  # Upper Wave
            "#4b0082",  # Lower Wave
        )

        self.cell_width = 100
        self.cell_height = 80

        self._configure_window()
        self._build_interface()
        self.show_stops()

    def _configure_window(self) -> None:
        self.root.title(
            f"{self.config.name} — Screen Inspector"
        )
        self.root.resizable(False, False)

        style = ttk.Style(self.root)

        style.configure(
            "Heading.TLabel",
            font=("Segoe UI", 11, "bold"),
        )

    def _build_interface(self) -> None:
        outer = ttk.Frame(self.root, padding=16)
        outer.grid(row=0, column=0, sticky="nsew")

        ttk.Label(
            outer,
            text=self.config.name,
            style="Heading.TLabel",
        ).grid(
            row=0,
            column=0,
            sticky="w",
        )

        ttk.Label(
            outer,
            text=(
                "Each stop identifies the top visible symbol. "
                "The reel strip wraps cyclically."
            ),
        ).grid(
            row=1,
            column=0,
            sticky="w",
            pady=(2, 12),
        )

        self._create_stop_controls(outer)
        self._create_payline_controls(outer)
        self._create_buttons(outer)
        self._create_screen_canvas(outer)

        ttk.Label(
            outer,
            textvariable=self.status_variable,
        ).grid(
            row=6,
            column=0,
            sticky="w",
            pady=(10, 0),
        )

    def _create_stop_controls(
        self,
        parent: ttk.Frame,
    ) -> None:
        controls = ttk.LabelFrame(
            parent,
            text="Reel stops",
            padding=10,
        )
        controls.grid(
            row=2,
            column=0,
            sticky="ew",
        )

        for reel_index, reel_length in enumerate(
            self.config.reel_lengths
        ):
            ttk.Label(
                controls,
                text=f"Reel {reel_index + 1}",
            ).grid(
                row=0,
                column=reel_index,
                padx=5,
                pady=(0, 4),
            )

            spinbox = ttk.Spinbox(
                controls,
                from_=0,
                to=reel_length - 1,
                width=6,
                justify="center",
                textvariable=self.stop_variables[reel_index],
                command=self.show_stops,
            )
            spinbox.grid(
                row=1,
                column=reel_index,
                padx=5,
            )

            spinbox.bind(
                "<Return>",
                self._on_enter,
            )
            spinbox.bind(
                "<FocusOut>",
                self._on_focus_out,
            )

    def _create_payline_controls(
        self,
        parent: ttk.Frame,
    ) -> None:
        payline_frame = ttk.LabelFrame(
            parent,
            text="Visible paylines",
            padding=10,
        )
        payline_frame.grid(
            row=3,
            column=0,
            sticky="ew",
            pady=(10, 0),
        )

        columns = 3

        for payline_index, payline in enumerate(
            self.config.paylines
        ):
            row = payline_index // columns
            column = payline_index % columns

            item_frame = ttk.Frame(payline_frame)
            item_frame.grid(
                row=row,
                column=column,
                sticky="w",
                padx=8,
                pady=3,
            )

            color = self._payline_color(payline_index)

            color_marker = tk.Canvas(
                item_frame,
                width=16,
                height=16,
                highlightthickness=0,
                borderwidth=0,
            )
            color_marker.grid(
                row=0,
                column=0,
                padx=(0, 4),
            )

            color_marker.create_rectangle(
                2,
                2,
                14,
                14,
                fill=color,
                outline=color,
            )

            ttk.Checkbutton(
                item_frame,
                text=payline.name,
                variable=self.payline_variables[payline_index],
                command=self._on_payline_toggle,
            ).grid(
                row=0,
                column=1,
                sticky="w",
            )

        control_row = (
            len(self.config.paylines) + columns - 1
        ) // columns

        payline_buttons = ttk.Frame(payline_frame)
        payline_buttons.grid(
            row=control_row,
            column=0,
            columnspan=columns,
            sticky="w",
            pady=(8, 0),
        )

        ttk.Button(
            payline_buttons,
            text="Select all",
            command=lambda: self._set_all_paylines(True),
        ).grid(
            row=0,
            column=0,
            padx=(0, 5),
        )

        ttk.Button(
            payline_buttons,
            text="Clear all",
            command=lambda: self._set_all_paylines(False),
        ).grid(
            row=0,
            column=1,
        )

    def _create_buttons(
        self,
        parent: ttk.Frame,
    ) -> None:
        buttons = ttk.Frame(parent)
        buttons.grid(
            row=4,
            column=0,
            pady=12,
        )

        ttk.Button(
            buttons,
            text="Spin",
            command=self.animated_spin,
        ).grid(
            row=0,
            column=0,
            padx=5,
        )

        ttk.Button(
            buttons,
            text="Reset",
            command=self.reset,
        ).grid(
            row=0,
            column=1,
            padx=5,
        )

    def _create_screen_canvas(
        self,
        parent: ttk.Frame,
    ) -> None:
        screen_frame = ttk.LabelFrame(
            parent,
            text="Visible screen",
            padding=10,
        )
        screen_frame.grid(
            row=5,
            column=0,
        )

        canvas_width = (
            self.config.n_reels * self.cell_width
        )
        canvas_height = (
            self.config.visible_rows * self.cell_height
        )

        self.screen_canvas = tk.Canvas(
            screen_frame,
            width=canvas_width,
            height=canvas_height,
            background="#ffffff",
            highlightthickness=0,
        )
        self.screen_canvas.grid(
            row=0,
            column=0,
        )

    def _payline_color(
        self,
        payline_index: int,
    ) -> str:
        """Return a configured color, cycling if necessary."""

        return self.payline_colors[
            payline_index % len(self.payline_colors)
        ]

    def _read_stops(self) -> tuple[int, ...]:
        stops: list[int] = []

        for reel_index, variable in enumerate(
            self.stop_variables
        ):
            raw_value = variable.get().strip()

            try:
                stop = int(raw_value)
            except ValueError as error:
                raise ValueError(
                    f"Reel {reel_index + 1} stop "
                    "must be an integer"
                ) from error

            stops.append(stop)

        return tuple(stops)

    def _cell_center(
        self,
        reel_index: int,
        row_index: int,
    ) -> tuple[float, float]:
        x = (
            reel_index * self.cell_width
            + self.cell_width / 2
        )
        y = (
            row_index * self.cell_height
            + self.cell_height / 2
        )

        return x, y

    def _draw_screen(
        self,
        screen: Screen,
    ) -> None:
        self.screen_canvas.delete("all")

        for row_index, row in enumerate(screen):
            for reel_index, symbol in enumerate(row):
                x0 = reel_index * self.cell_width
                y0 = row_index * self.cell_height
                x1 = x0 + self.cell_width
                y1 = y0 + self.cell_height

                self.screen_canvas.create_rectangle(
                    x0,
                    y0,
                    x1,
                    y1,
                    fill="#ffffff",
                    outline="#404040",
                    width=2,
                    tags=("cell",),
                )

                center_x, center_y = self._cell_center(
                    reel_index,
                    row_index,
                )

                self.screen_canvas.create_text(
                    center_x,
                    center_y,
                    text=symbol,
                    fill="#111111",
                    font=("Segoe UI", 18, "bold"),
                    tags=("symbol",),
                )

        self._draw_paylines()

    def _draw_paylines(self) -> None:
        self.screen_canvas.delete("payline")

        for payline_index, (
            payline,
            variable,
        ) in enumerate(
            zip(
                self.config.paylines,
                self.payline_variables,
            )
        ):
            if not variable.get():
                continue

            color = self._payline_color(payline_index)
            points: list[float] = []

            for reel_index, row_index in enumerate(
                payline.rows
            ):
                x, y = self._cell_center(
                    reel_index,
                    row_index,
                )
                points.extend((x, y))

            self.screen_canvas.create_line(
                *points,
                fill=color,
                width=4,
                capstyle=tk.ROUND,
                joinstyle=tk.ROUND,
                tags=("payline",),
            )

            marker_radius = 6

            for reel_index, row_index in enumerate(
                payline.rows
            ):
                x, y = self._cell_center(
                    reel_index,
                    row_index,
                )

                self.screen_canvas.create_oval(
                    x - marker_radius,
                    y - marker_radius,
                    x + marker_radius,
                    y + marker_radius,
                    fill=color,
                    outline="#ffffff",
                    width=1,
                    tags=("payline",),
                )

        # Keep symbol text readable above the payline graphics.
        self.screen_canvas.tag_raise("symbol")

    def _render_screen(
        self,
        screen: Screen,
        stops: tuple[int, ...],
    ) -> None:
        self.current_screen = screen
        self.current_stops = stops

        self._draw_screen(screen)
        self._update_status()

    def _update_status(self) -> None:
        if self.current_stops is None:
            return

        active_count = sum(
            variable.get()
            for variable in self.payline_variables
        )

        self.status_variable.set(
            f"Stops: {self.current_stops}    "
            f"Active paylines: "
            f"{active_count}/{len(self.config.paylines)}"
        )

    def _on_payline_toggle(self) -> None:
        if self.current_screen is not None:
            self._draw_paylines()

        self._update_status()

    def _set_all_paylines(
        self,
        enabled: bool,
    ) -> None:
        for variable in self.payline_variables:
            variable.set(enabled)

        self._on_payline_toggle()

    def show_stops(self) -> None:
        if self.is_spinning:
            return
        try:
            stops = self._read_stops()
            screen = build_screen(
                self.config,
                stops,
            )
        except (TypeError, ValueError) as error:
            messagebox.showerror(
                title="Invalid reel stops",
                message=str(error),
                parent=self.root,
            )
            return

        self._render_screen(
            screen,
            stops,
        )

    def animated_spin(self) -> None:
        """Config animation"""

        if self.is_spinning:
            return

        self.is_spinning = True
        result = spin(self.config, self.rng)

        self._animate_reels(
            final_stops = result.stops,
            step=0,
        )

    def _animate_reels(
            self,
            final_stops: tuple[int, ...],
            step: int,
    )-> None:
        """ Advance one frame"""
        animated_stops: list[int] = []

        for reel_index, reel_length in enumerate(
            self.config.reel_lengths
        ):
            # Stop reels left to right
            stop_step = self.animations_steps + reel_index * 4

            if step >= stop_step:
                stop = final_stops[reel_index]
            else:
                current_stops = int(self.stop_variables[reel_index].get())
                stop = (current_stops + 1) % reel_length

            animated_stops.append(stop)
            self.stop_variables[reel_index].set(str(stop))

        stops = tuple(animated_stops)
        screen = build_screen(self.config, stops)
        self._render_screen(screen, stops)

        final_step = self.animations_steps + (self.config.n_reels -1)*4
        if step < final_step:
            self.root.after(
                self.animation_delay_ms,
                self._animate_reels,
                final_stops,
                step +1,
            )
        else:
            self.is_spinning = False

    
    def random_spin(self) -> None:
        result = spin(
            self.config,
            self.rng,
        )

        for variable, stop in zip(
            self.stop_variables,
            result.stops,
        ):
            variable.set(str(stop))

        self._render_screen(
            result.screen,
            result.stops,
        )

    def reset(self) -> None:
        if self.is_spinning:
            return

        for variable in self.stop_variables:
            variable.set("0")

        self.show_stops()

    def _on_enter(
        self,
        _event: tk.Event,
    ) -> None:
        self.show_stops()

    def _on_focus_out(
        self,
        _event: tk.Event,
    ) -> None:
        # Avoid popup errors while the user is editing a stop.
        try:
            stops = self._read_stops()
            screen = build_screen(
                self.config,
                stops,
            )
        except (TypeError, ValueError):
            return

        self._render_screen(
            screen,
            stops,
        )


def main() -> None:
    root = tk.Tk()

    SlotScreenApp(
        root,
        EXAMPLE_CONFIG,
        seed=12345,
    )

    root.mainloop()


if __name__ == "__main__":
    main()