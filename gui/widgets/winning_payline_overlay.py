from __future__ import annotations

from collections.abc import Iterable, Sequence
from typing import TypeAlias

from PySide6.QtCore import QPointF, Qt
from PySide6.QtGui import (
    QColor,
    QPaintEvent,
    QPainter,
    QPainterPath,
    QPen,
)
from PySide6.QtWidgets import QWidget


Payline: TypeAlias = tuple[int, ...]

WIN_LINE_COLOR = QColor(242, 193, 78, 190)
WIN_LINE_HALO_COLOR = QColor(15, 16, 18, 150)
WIN_LINE_WIDTH = 5.0
WIN_LINE_HALO_WIDTH = 9.0


class WinningPaylineOverlay(QWidget):
    """Draw selected paylines over a fixed-size animated slot screen."""

    def __init__(
        self,
        *,
        paylines: Sequence[Sequence[int]],
        reel_count: int,
        row_count: int,
        symbol_size: int,
        frame_inset: int,
        column_spacing: int,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)

        if reel_count <= 0:
            raise ValueError("reel_count must be positive.")

        if row_count <= 0:
            raise ValueError("row_count must be positive.")

        if symbol_size <= 0:
            raise ValueError("symbol_size must be positive.")

        if frame_inset < 0:
            raise ValueError("frame_inset cannot be negative.")

        if column_spacing < 0:
            raise ValueError("column_spacing cannot be negative.")

        self._reel_count = int(reel_count)
        self._row_count = int(row_count)
        self._symbol_size = int(symbol_size)
        self._frame_inset = int(frame_inset)
        self._column_spacing = int(column_spacing)
        self._paylines = self._validate_paylines(paylines)
        self._winning_indices: set[int] = set()

        self.setObjectName("winningPaylineOverlay")
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

    @property
    def winning_indices(self) -> frozenset[int]:
        return frozenset(self._winning_indices)

    @property
    def line_count(self) -> int:
        return len(self._paylines)

    def set_winning_paylines(
        self,
        indices: Iterable[int],
    ) -> None:
        winning_indices = {int(index) for index in indices}

        for payline_index in winning_indices:
            self._validate_payline_index(payline_index)

        if winning_indices == self._winning_indices:
            return

        self._winning_indices = winning_indices
        self.update()

    def clear(self) -> None:
        self.set_winning_paylines(())

    def paintEvent(
        self,
        event: QPaintEvent,
    ) -> None:
        super().paintEvent(event)

        if not self._winning_indices:
            return

        painter = QPainter(self)
        painter.setRenderHint(
            QPainter.RenderHint.Antialiasing,
            True,
        )

        for payline_index in sorted(self._winning_indices):
            self._draw_payline(
                painter,
                self._paylines[payline_index],
            )

    def _draw_payline(
        self,
        painter: QPainter,
        payline: Payline,
    ) -> None:
        points = tuple(
            self._cell_center(
                reel_index=reel_index,
                row_index=row_index,
            )
            for reel_index, row_index in enumerate(payline)
        )

        path = QPainterPath()
        path.moveTo(points[0])

        for point in points[1:]:
            path.lineTo(point)

        halo_pen = QPen(
            WIN_LINE_HALO_COLOR,
            WIN_LINE_HALO_WIDTH,
        )
        halo_pen.setCapStyle(Qt.PenCapStyle.RoundCap)
        halo_pen.setJoinStyle(Qt.PenJoinStyle.RoundJoin)

        painter.setBrush(Qt.BrushStyle.NoBrush)
        painter.setPen(halo_pen)
        painter.drawPath(path)

        line_pen = QPen(
            WIN_LINE_COLOR,
            WIN_LINE_WIDTH,
        )
        line_pen.setCapStyle(Qt.PenCapStyle.RoundCap)
        line_pen.setJoinStyle(Qt.PenJoinStyle.RoundJoin)

        painter.setPen(line_pen)
        painter.drawPath(path)

    def _cell_center(
        self,
        *,
        reel_index: int,
        row_index: int,
    ) -> QPointF:
        x = (
            self._frame_inset
            + reel_index
            * (self._symbol_size + self._column_spacing)
            + self._symbol_size / 2.0
        )
        y = (
            self._frame_inset
            + row_index * self._symbol_size
            + self._symbol_size / 2.0
        )
        return QPointF(x, y)

    def _validate_paylines(
        self,
        paylines: Sequence[Sequence[int]],
    ) -> tuple[Payline, ...]:
        if not paylines:
            raise ValueError("At least one payline is required.")

        validated: list[Payline] = []

        for line_index, raw_line in enumerate(paylines):
            line = tuple(int(row_index) for row_index in raw_line)

            if len(line) != self._reel_count:
                raise ValueError(
                    f"Payline {line_index} contains {len(line)} positions; "
                    f"expected {self._reel_count}."
                )

            for reel_index, row_index in enumerate(line):
                if not 0 <= row_index < self._row_count:
                    raise ValueError(
                        f"Payline {line_index}, reel {reel_index}: "
                        f"row {row_index} is outside the displayed screen."
                    )

            validated.append(line)

        return tuple(validated)

    def _validate_payline_index(self, payline_index: int) -> None:
        if not 0 <= payline_index < self.line_count:
            raise IndexError(
                "payline_index must be between 0 and "
                f"{self.line_count - 1}."
            )
