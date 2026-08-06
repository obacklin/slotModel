from __future__ import annotations

from collections.abc import (
    Iterable,
    Sequence,
)
from pathlib import Path

from PySide6.QtCore import QRect, QSize
from PySide6.QtGui import (
    QColor,
    QResizeEvent,
)
from PySide6.QtWidgets import (
    QSizePolicy,
    QWidget,
)

from gui.widgets.payline_overlay import (
    PaylineOverlay,
)
from gui.widgets.symbol_grid_widget import (
    SYMBOL_ASSET_DIRECTORY,
    ScreenDefinition,
    SymbolGridWidget,
)


class PaylineScreenWidget(QWidget):
    """
    Composite widget containing a symbol grid and a transparent
    payline drawing layer above it.
    """

    def __init__(
        self,
        *,
        row_count: int,
        reel_count: int,
        paylines: Sequence[
            Sequence[int]
        ],
        symbol_directory: (
            str | Path
        ) = SYMBOL_ASSET_DIRECTORY,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)

        if row_count <= 0:
            raise ValueError(
                "row_count must be positive."
            )

        if reel_count <= 0:
            raise ValueError(
                "reel_count must be positive."
            )

        self._row_count = row_count
        self._reel_count = reel_count

        self._symbol_grid = (
            SymbolGridWidget(
                row_count=row_count,
                reel_count=reel_count,
                symbol_directory=(
                    symbol_directory
                ),
                parent=self,
            )
        )

        self._overlay = PaylineOverlay(
            symbol_grid=self._symbol_grid,
            paylines=paylines,
            parent=self,
        )

        self._overlay.raise_()

        self.setMinimumSize(520, 320)
        self.setSizePolicy(
            QSizePolicy.Policy.Expanding,
            QSizePolicy.Policy.Expanding,
        )

    @property
    def line_count(self) -> int:
        return self._overlay.line_count

    @property
    def visible_payline_indices(
        self,
    ) -> frozenset[int]:
        return (
            self._overlay.visible_indices
        )

    def sizeHint(self) -> QSize:
        return QSize(850, 510)

    def set_screen(
        self,
        screen: ScreenDefinition,
    ) -> None:
        self._symbol_grid.set_screen(
            screen
        )
        self._overlay.update()

    def show_payline(
        self,
        payline_index: int,
    ) -> None:
        self._overlay.set_visible_paylines(
            (payline_index,)
        )
        self._overlay.set_highlighted_payline(
            payline_index
        )

    def show_paylines(
        self,
        indices: Iterable[int],
    ) -> None:
        self._overlay.set_visible_paylines(
            indices
        )

    def show_all_paylines(self) -> None:
        self._overlay.show_all()

    def clear_paylines(self) -> None:
        self._overlay.clear()

    def set_highlighted_payline(
        self,
        payline_index: int | None,
    ) -> None:
        self._overlay.set_highlighted_payline(
            payline_index
        )

    def payline_color(
        self,
        payline_index: int,
    ) -> QColor:
        return self._overlay.color_for_index(
            payline_index
        )

    def resizeEvent(
        self,
        event: QResizeEvent,
    ) -> None:
        super().resizeEvent(event)

        screen_rect = (
            self._fitted_screen_rect(
                self.contentsRect()
            )
        )

        self._symbol_grid.setGeometry(
            screen_rect
        )
        self._overlay.setGeometry(
            screen_rect
        )

        self._overlay.raise_()
        self._overlay.update()

    def _fitted_screen_rect(
        self,
        available_rect: QRect,
    ) -> QRect:
        """
        Fit the screen while keeping each displayed symbol cell
        approximately square.
        """

        if (
            available_rect.width() <= 0
            or available_rect.height() <= 0
        ):
            return QRect()

        target_ratio = (
            self._reel_count
            / self._row_count
        )

        available_ratio = (
            available_rect.width()
            / available_rect.height()
        )

        if available_ratio > target_ratio:
            height = (
                available_rect.height()
            )
            width = round(
                height * target_ratio
            )
        else:
            width = available_rect.width()
            height = round(
                width / target_ratio
            )

        x_position = (
            available_rect.x()
            + (
                available_rect.width()
                - width
            )
            // 2
        )

        y_position = (
            available_rect.y()
            + (
                available_rect.height()
                - height
            )
            // 2
        )

        return QRect(
            x_position,
            y_position,
            width,
            height,
        )