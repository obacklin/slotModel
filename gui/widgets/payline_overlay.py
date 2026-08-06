from __future__ import annotations

from collections.abc import (
    Iterable,
    Sequence,
)
from typing import TypeAlias

from PySide6.QtCore import Qt
from PySide6.QtGui import (
    QColor,
    QPaintEvent,
    QPainter,
    QPainterPath,
    QPen,
)
from PySide6.QtWidgets import QWidget

from gui.widgets.symbol_grid_widget import (
    SymbolGridWidget,
)


Payline: TypeAlias = tuple[int, ...]

PAYLINE_COLORS: tuple[QColor, ...] = (
    QColor("#ff5d5d"),
    QColor("#55d98a"),
    QColor("#5d91ff"),
    QColor("#f5bd4f"),
    QColor("#b878ff"),
    QColor("#46d4dd"),
    QColor("#ff75b5"),
    QColor("#a4d65e"),
    QColor("#ff8a4c"),
    QColor("#7b7cff"),
    QColor("#41c7a6"),
    QColor("#e5d154"),
    QColor("#c16cf2"),
    QColor("#61c970"),
    QColor("#ff667f"),
)


class PaylineOverlay(QWidget):
    """
    Transparent widget that draws paylines over a symbol grid.

    Each payline contains one zero-based row index for every reel.
    """

    def __init__(
        self,
        *,
        symbol_grid: SymbolGridWidget,
        paylines: Sequence[
            Sequence[int]
        ],
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)

        self._symbol_grid = symbol_grid

        self._paylines = (
            self._validate_paylines(
                paylines
            )
        )

        self._visible_indices: set[
            int
        ] = set()

        self._highlighted_index: (
            int | None
        ) = None

        self.setAttribute(
            Qt.WidgetAttribute.WA_TransparentForMouseEvents,
            True,
        )
        self.setAttribute(
            Qt.WidgetAttribute.WA_TranslucentBackground,
            True,
        )
        self.setAttribute(
            Qt.WidgetAttribute.WA_NoSystemBackground,
            True,
        )

        self._symbol_grid.cell_geometry_changed.connect(
            self.update
        )

    @property
    def line_count(self) -> int:
        return len(self._paylines)

    @property
    def visible_indices(
        self,
    ) -> frozenset[int]:
        return frozenset(
            self._visible_indices
        )

    def color_for_index(
        self,
        payline_index: int,
    ) -> QColor:
        self._validate_payline_index(
            payline_index
        )

        color_index = (
            payline_index
            % len(PAYLINE_COLORS)
        )

        return QColor(
            PAYLINE_COLORS[color_index]
        )

    def set_visible_paylines(
        self,
        indices: Iterable[int],
    ) -> None:
        visible_indices = {
            int(index)
            for index in indices
        }

        for payline_index in visible_indices:
            self._validate_payline_index(
                payline_index
            )

        if (
            visible_indices
            == self._visible_indices
        ):
            return

        self._visible_indices = (
            visible_indices
        )

        self.update()

    def set_highlighted_payline(
        self,
        payline_index: int | None,
    ) -> None:
        if payline_index is not None:
            self._validate_payline_index(
                payline_index
            )

        if (
            payline_index
            == self._highlighted_index
        ):
            return

        self._highlighted_index = (
            payline_index
        )

        self.update()

    def show_all(self) -> None:
        self.set_visible_paylines(
            range(self.line_count)
        )

    def clear(self) -> None:
        self.set_visible_paylines(())

    def paintEvent(
        self,
        event: QPaintEvent,
    ) -> None:
        super().paintEvent(event)

        if not self._visible_indices:
            return

        painter = QPainter(self)

        painter.setRenderHint(
            QPainter.RenderHint.Antialiasing,
            True,
        )

        # Draw the highlighted line last so it remains visible where
        # multiple paylines overlap.
        ordered_indices = sorted(
            self._visible_indices,
            key=lambda index: (
                index
                == self._highlighted_index
            ),
        )

        for payline_index in ordered_indices:
            self._draw_payline(
                painter,
                payline_index,
            )

    def _draw_payline(
        self,
        painter: QPainter,
        payline_index: int,
    ) -> None:
        payline = self._paylines[
            payline_index
        ]

        points = [
            self._symbol_grid.cell_center(
                reel_index=reel_index,
                row_index=row_index,
                relative_to=self,
            )
            for reel_index, row_index
            in enumerate(payline)
        ]

        path = QPainterPath()
        path.moveTo(points[0])

        for point in points[1:]:
            path.lineTo(point)

        highlighted = (
            payline_index
            == self._highlighted_index
        )

        line_width = (
            6.0
            if highlighted
            else 4.0
        )

        marker_radius = (
            8.0
            if highlighted
            else 6.0
        )

        halo_pen = QPen(
            QColor(
                15,
                16,
                18,
                210,
            ),
            line_width + 4.0,
        )
        halo_pen.setCapStyle(
            Qt.PenCapStyle.RoundCap
        )
        halo_pen.setJoinStyle(
            Qt.PenJoinStyle.RoundJoin
        )

        painter.setPen(halo_pen)
        painter.setBrush(
            Qt.BrushStyle.NoBrush
        )
        painter.drawPath(path)

        line_color = self.color_for_index(
            payline_index
        )

        line_pen = QPen(
            line_color,
            line_width,
        )
        line_pen.setCapStyle(
            Qt.PenCapStyle.RoundCap
        )
        line_pen.setJoinStyle(
            Qt.PenJoinStyle.RoundJoin
        )

        painter.setPen(line_pen)
        painter.drawPath(path)

        painter.setPen(
            QPen(
                QColor(
                    15,
                    16,
                    18,
                    220,
                ),
                2.0,
            )
        )
        painter.setBrush(line_color)

        for point in points:
            painter.drawEllipse(
                point,
                marker_radius,
                marker_radius,
            )

    def _validate_paylines(
        self,
        paylines: Sequence[
            Sequence[int]
        ],
    ) -> tuple[Payline, ...]:
        if not paylines:
            raise ValueError(
                "At least one payline is required."
            )

        validated: list[Payline] = []

        for line_index, raw_line in enumerate(
            paylines
        ):
            line = tuple(
                int(row_index)
                for row_index in raw_line
            )

            if (
                len(line)
                != self._symbol_grid.reel_count
            ):
                raise ValueError(
                    f"Payline {line_index} "
                    f"contains {len(line)} "
                    "positions; expected "
                    f"{self._symbol_grid.reel_count}."
                )

            for (
                reel_index,
                row_index,
            ) in enumerate(line):
                if not (
                    0
                    <= row_index
                    < self._symbol_grid.row_count
                ):
                    raise ValueError(
                        f"Payline {line_index}, "
                        f"reel {reel_index}: "
                        f"row {row_index} is "
                        "outside the displayed "
                        "screen."
                    )

            validated.append(line)

        return tuple(validated)

    def _validate_payline_index(
        self,
        payline_index: int,
    ) -> None:
        if not (
            0
            <= payline_index
            < self.line_count
        ):
            raise IndexError(
                "payline_index must be "
                f"between 0 and "
                f"{self.line_count - 1}."
            )