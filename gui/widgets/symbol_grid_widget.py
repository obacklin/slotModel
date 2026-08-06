from __future__ import annotations

from collections.abc import Sequence
from pathlib import Path

from PySide6.QtCore import QPointF, QSize, Qt, QTimer, Signal
from PySide6.QtGui import QPixmap, QResizeEvent
from PySide6.QtWidgets import (
    QGridLayout,
    QLabel,
    QSizePolicy,
    QWidget,
)

from slotmodel.paths import PROJECT_ROOT
from slotmodel.sim.reels import Symbol


ScreenDefinition = Sequence[Sequence[Symbol | int]]

SYMBOL_ASSET_DIRECTORY = PROJECT_ROOT / "assets" / "source"


class _SymbolLabel(QLabel):
    """A label that keeps a source pixmap scaled to its current size."""

    def __init__(
        self,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)

        self._source_pixmap = QPixmap()

        self.setObjectName("symbolCell")
        self.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.setMinimumSize(72, 72)
        self.setSizePolicy(
            QSizePolicy.Policy.Expanding,
            QSizePolicy.Policy.Expanding,
        )

    def set_source_pixmap(
        self,
        pixmap: QPixmap,
    ) -> None:
        self._source_pixmap = pixmap
        self._update_displayed_pixmap()

    def resizeEvent(
        self,
        event: QResizeEvent,
    ) -> None:
        super().resizeEvent(event)
        self._update_displayed_pixmap()

    def _update_displayed_pixmap(self) -> None:
        if self._source_pixmap.isNull():
            self.clear()
            return

        available_size = self.contentsRect().size()

        if (
            available_size.width() <= 0
            or available_size.height() <= 0
        ):
            return

        scaled_pixmap = self._source_pixmap.scaled(
            available_size,
            Qt.AspectRatioMode.KeepAspectRatio,
            Qt.TransformationMode.SmoothTransformation,
        )

        self.setPixmap(scaled_pixmap)


class SymbolGridWidget(QWidget):
    """
    Display a fixed row-major screen of base symbol images.

    A screen is represented as:

        screen[row_index][reel_index]

    This matches the backend screen representation used in the
    repository.
    """

    cell_geometry_changed = Signal()

    def __init__(
        self,
        *,
        row_count: int,
        reel_count: int,
        symbol_directory: str | Path = SYMBOL_ASSET_DIRECTORY,
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
        self._symbol_directory = Path(
            symbol_directory
        )

        self._asset_paths = (
            self._index_base_assets()
        )

        self._pixmap_cache: dict[
            Symbol,
            QPixmap,
        ] = {}

        self._labels: list[
            list[_SymbolLabel]
        ] = []

        self._build_layout()
        self._apply_style()

    @property
    def row_count(self) -> int:
        return self._row_count

    @property
    def reel_count(self) -> int:
        return self._reel_count

    def sizeHint(self) -> QSize:
        return QSize(850, 510)

    def set_screen(
        self,
        screen: ScreenDefinition,
    ) -> None:
        """Display a row-major symbol screen."""

        rows = tuple(
            tuple(row)
            for row in screen
        )

        if len(rows) != self._row_count:
            raise ValueError(
                f"Expected {self._row_count} rows, "
                f"received {len(rows)}."
            )

        for row_index, row in enumerate(rows):
            if len(row) != self._reel_count:
                raise ValueError(
                    f"Expected {self._reel_count} "
                    f"symbols in row {row_index}, "
                    f"received {len(row)}."
                )

            for reel_index, raw_symbol in enumerate(
                row
            ):
                try:
                    symbol = Symbol(
                        int(raw_symbol)
                    )
                except (
                    TypeError,
                    ValueError,
                ) as error:
                    raise ValueError(
                        "Invalid symbol at "
                        f"row {row_index}, "
                        f"reel {reel_index}: "
                        f"{raw_symbol!r}."
                    ) from error

                label = self._labels[
                    row_index
                ][reel_index]

                label.set_source_pixmap(
                    self._pixmap_for_symbol(
                        symbol
                    )
                )

                label.setToolTip(
                    symbol.name.replace(
                        "_",
                        " ",
                    ).title()
                )

    def cell_center(
        self,
        *,
        reel_index: int,
        row_index: int,
        relative_to: QWidget,
    ) -> QPointF:
        """
        Return a cell centre in another widget's coordinates.

        The actual label geometry is used, ensuring that the paylines
        remain aligned after the window is resized.
        """

        if not (
            0
            <= reel_index
            < self._reel_count
        ):
            raise IndexError(
                "reel_index must be between "
                f"0 and {self._reel_count - 1}."
            )

        if not (
            0
            <= row_index
            < self._row_count
        ):
            raise IndexError(
                "row_index must be between "
                f"0 and {self._row_count - 1}."
            )

        label = self._labels[
            row_index
        ][reel_index]

        global_center = label.mapToGlobal(
            label.rect().center()
        )

        mapped_center = (
            relative_to.mapFromGlobal(
                global_center
            )
        )

        return QPointF(
            float(mapped_center.x()),
            float(mapped_center.y()),
        )

    def resizeEvent(
        self,
        event: QResizeEvent,
    ) -> None:
        super().resizeEvent(event)

        # QGridLayout applies the final child geometries after the
        # resize event. Notify the overlay on the next event-loop
        # iteration.
        QTimer.singleShot(
            0,
            self.cell_geometry_changed.emit,
        )

    def _build_layout(self) -> None:
        layout = QGridLayout(self)

        layout.setContentsMargins(
            8,
            8,
            8,
            8,
        )
        layout.setHorizontalSpacing(8)
        layout.setVerticalSpacing(8)

        for row_index in range(
            self._row_count
        ):
            label_row: list[
                _SymbolLabel
            ] = []

            for reel_index in range(
                self._reel_count
            ):
                label = _SymbolLabel(self)

                layout.addWidget(
                    label,
                    row_index,
                    reel_index,
                )

                label_row.append(label)

            self._labels.append(label_row)

            layout.setRowStretch(
                row_index,
                1,
            )

        for reel_index in range(
            self._reel_count
        ):
            layout.setColumnStretch(
                reel_index,
                1,
            )

    def _apply_style(self) -> None:
        self.setStyleSheet(
            """
            QLabel#symbolCell {
                background-color: #22252a;
                border: 1px solid #3a3e45;
                border-radius: 9px;
                padding: 6px;
            }
            """
        )

    def _index_base_assets(
        self,
    ) -> dict[str, Path]:
        """
        Index files following the `<symbol>_base.png` convention.

        Matching is case-insensitive, which allows both:

            Chest_base.png
            chest_base.png

        Sticky symbol files are not indexed.
        """

        if not self._symbol_directory.is_dir():
            raise FileNotFoundError(
                "Symbol asset directory does "
                "not exist: "
                f"{self._symbol_directory}"
            )

        asset_paths = {
            path.name.casefold(): path
            for path
            in self._symbol_directory.iterdir()
            if (
                path.is_file()
                and path.suffix.casefold()
                == ".png"
                and path.stem.casefold().endswith(
                    "_base"
                )
            )
        }

        if not asset_paths:
            raise FileNotFoundError(
                "No base symbol PNG files were "
                "found in "
                f"{self._symbol_directory}. "
                "Expected names such as "
                "'A_base.png' and "
                "'Wild_base.png'."
            )

        return asset_paths

    def _pixmap_for_symbol(
        self,
        symbol: Symbol,
    ) -> QPixmap:
        cached_pixmap = (
            self._pixmap_cache.get(symbol)
        )

        if cached_pixmap is not None:
            return cached_pixmap

        expected_filename = (
            f"{symbol.name}_base.png"
        )

        asset_path = self._asset_paths.get(
            expected_filename.casefold()
        )

        if asset_path is None:
            raise FileNotFoundError(
                "No base image was found for "
                f"{symbol.name}. Expected "
                f"'{expected_filename}' in "
                f"{self._symbol_directory}."
            )

        pixmap = QPixmap(
            str(asset_path)
        )

        if pixmap.isNull():
            raise ValueError(
                "Qt could not load symbol image: "
                f"{asset_path}"
            )

        self._pixmap_cache[symbol] = pixmap

        return pixmap