from __future__ import annotations

import math
from collections.abc import Sequence
from pathlib import Path

from PySide6.QtCore import (
    Property,
    QEasingCurve,
    QRectF,
    QSize,
    Qt,
    QPropertyAnimation,
    Signal,
    Slot,
)
from PySide6.QtGui import (
    QColor,
    QPainter,
    QPen,
    QPixmap,
)
from PySide6.QtWidgets import (
    QHBoxLayout,
    QSizePolicy,
    QWidget,
)

from slotmodel.paths import PROJECT_ROOT
from slotmodel.sim.reels import ReelSet, Symbol


SYMBOL_ASSET_DIRECTORY = PROJECT_ROOT / "assets" / "source"

# The source assets are 256 x 256 pixels. They are rendered into fixed
# 128 x 128 display cells so the complete 5 x 3 screen fits the application's
# existing 1100 x 720 default window. The source PNGs are still sampled in full;
# only their on-screen size changes. Set this to 256 for native-size rendering.
SYMBOL_DISPLAY_SIZE = 128

# There is no space between adjacent symbol cells. The only inset is the small
# amount needed to keep the common screen outline visible around its children.
COLUMN_SPACING = 0
SCREEN_FRAME_INSET = 2
SCREEN_OUTLINE_WIDTH = 2
SCREEN_CORNER_RADIUS = 0

SCREEN_BACKGROUND = QColor("#22252a")
SCREEN_OUTLINE = QColor("#4a4f58")


class _SymbolPixmapStore:
    """Load and cache base-symbol images by backend Symbol value."""

    def __init__(
        self,
        symbol_directory: str | Path,
    ) -> None:
        self._symbol_directory = Path(symbol_directory)
        self._asset_paths = self._index_base_assets()
        self._pixmaps: dict[Symbol, QPixmap] = {}

    def pixmap(self, symbol: Symbol) -> QPixmap:
        cached = self._pixmaps.get(symbol)

        if cached is not None:
            return cached

        expected_filename = f"{symbol.name}_base.png"
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

        pixmap = QPixmap(str(asset_path))

        if pixmap.isNull():
            raise ValueError(
                "Qt could not load symbol image: "
                f"{asset_path}"
            )

        self._pixmaps[symbol] = pixmap
        return pixmap

    def _index_base_assets(self) -> dict[str, Path]:
        if not self._symbol_directory.is_dir():
            raise FileNotFoundError(
                "Symbol asset directory does not exist: "
                f"{self._symbol_directory}"
            )

        asset_paths = {
            path.name.casefold(): path
            for path in self._symbol_directory.iterdir()
            if (
                path.is_file()
                and path.suffix.casefold() == ".png"
                and path.stem.casefold().endswith("_base")
            )
        }

        if not asset_paths:
            raise FileNotFoundError(
                "No base symbol PNG files were found in "
                f"{self._symbol_directory}."
            )

        return asset_paths


class AnimatedReelWidget(QWidget):
    """
    Paint and animate one configured backend reel strip.

    This widget is only a transparent viewport and painter. It does not draw a
    background, separator, border, card, or individual symbol container.

    The floating-point scroll position is expressed in reel stops. At an
    integer position ``n``, strip position ``n`` is shown in the top row. The
    next strip positions are shown in the rows below it, matching the backend's
    ``window_offsets=(0, 1, 2)`` convention.
    """

    spin_finished = Signal(int)

    def __init__(
        self,
        *,
        reel: Sequence[Symbol | int],
        pixmaps: _SymbolPixmapStore,
        visible_rows: int,
        symbol_size: int = SYMBOL_DISPLAY_SIZE,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)

        if visible_rows <= 0:
            raise ValueError("visible_rows must be positive.")

        if symbol_size <= 0:
            raise ValueError("symbol_size must be positive.")

        self._strip = tuple(Symbol(int(symbol)) for symbol in reel)

        if not self._strip:
            raise ValueError("A reel strip cannot be empty.")

        self._pixmaps = pixmaps
        self._visible_rows = visible_rows
        self._symbol_size = int(symbol_size)
        self._scroll_position = 0.0
        self._target_stop = 0

        # Load all required assets while constructing the page, rather than
        # failing halfway through an animation.
        for symbol in set(self._strip):
            self._pixmaps.pixmap(symbol)

        self.setObjectName("animatedReel")
        self.setAutoFillBackground(False)
        self.setAttribute(
            Qt.WidgetAttribute.WA_TranslucentBackground,
            True,
        )
        self.setSizePolicy(
            QSizePolicy.Policy.Fixed,
            QSizePolicy.Policy.Fixed,
        )
        self.setFixedSize(
            self._symbol_size,
            self._visible_rows * self._symbol_size,
        )

        self._animation = QPropertyAnimation(
            self,
            b"scrollPosition",
            self,
        )
        self._animation.setEasingCurve(
            QEasingCurve.Type.OutCubic
        )
        self._animation.finished.connect(
            self._finish_animation
        )

    @property
    def reel_length(self) -> int:
        return len(self._strip)

    @property
    def current_stop(self) -> int:
        return int(round(self._scroll_position)) % self.reel_length

    def sizeHint(self) -> QSize:
        return QSize(
            self._symbol_size,
            self._visible_rows * self._symbol_size,
        )

    def get_scroll_position(self) -> float:
        return self._scroll_position

    def set_scroll_position(self, value: float) -> None:
        self._scroll_position = float(value)
        self.update()

    scrollPosition = Property(
        float,
        get_scroll_position,
        set_scroll_position,
    )

    def set_stop_immediately(self, stop: int) -> None:
        """Display a backend stop without animation."""
        self._validate_stop(stop)
        self._animation.stop()
        self._target_stop = int(stop)
        self.set_scroll_position(float(stop))

    def spin_to_stop(
        self,
        stop: int,
        *,
        duration_ms: int,
        full_cycles: int,
    ) -> None:
        """Animate downward and finish at the supplied backend stop."""
        self._validate_stop(stop)

        if duration_ms <= 0:
            raise ValueError("duration_ms must be positive.")

        if full_cycles <= 0:
            raise ValueError("full_cycles must be positive.")

        self._animation.stop()
        self._target_stop = int(stop)

        start_position = self._scroll_position
        start_integer = math.floor(start_position)
        current_stop = start_integer % self.reel_length

        # Decreasing reel positions make the symbols move downward through the
        # viewport.
        backward_distance = (
            current_stop - self._target_stop
        ) % self.reel_length

        end_position = (
            start_integer
            - full_cycles * self.reel_length
            - backward_distance
        )

        if end_position >= start_position:
            end_position -= self.reel_length

        self._animation.setDuration(duration_ms)
        self._animation.setStartValue(start_position)
        self._animation.setEndValue(float(end_position))
        self._animation.start()

    def visible_symbols(self) -> tuple[Symbol, ...]:
        """Return the symbols currently aligned with the visible rows."""
        stop = self.current_stop

        return tuple(
            self._strip[(stop + row_index) % self.reel_length]
            for row_index in range(self._visible_rows)
        )

    def paintEvent(self, event) -> None:  # type: ignore[override]
        del event

        painter = QPainter(self)
        painter.setRenderHint(
            QPainter.RenderHint.SmoothPixmapTransform
        )

        first_strip_position = math.floor(self._scroll_position)
        fractional_offset = (
            self._scroll_position - first_strip_position
        )

        # Paint one extra symbol above and below the viewport so that the
        # transparent reel never exposes an empty strip during movement.
        for visual_row in range(-1, self._visible_rows + 1):
            strip_index = (
                first_strip_position + visual_row
            ) % self.reel_length
            symbol = self._strip[strip_index]
            pixmap = self._pixmaps.pixmap(symbol)

            y = (
                visual_row - fractional_offset
            ) * self._symbol_size

            target = QRectF(
                0.0,
                y,
                float(self._symbol_size),
                float(self._symbol_size),
            )

            painter.drawPixmap(
                target,
                pixmap,
                QRectF(pixmap.rect()),
            )

    @Slot()
    def _finish_animation(self) -> None:
        # Repeated downward spins produce large negative values. Normalize to
        # the equivalent configured stop once the reel is stationary.
        self.set_scroll_position(float(self._target_stop))
        self.spin_finished.emit(self._target_stop)

    def _validate_stop(self, stop: int) -> None:
        if not 0 <= int(stop) < self.reel_length:
            raise ValueError(
                f"Stop {stop} is outside reel positions "
                f"0 through {self.reel_length - 1}."
            )


class AnimatedSlotWidget(QWidget):
    """
    Coordinate the animated reels and paint one common 5 x 3 frame.

    The parent owns the screen background and outer outline. Its child reel
    widgets are transparent and paint only their moving symbol PNGs.
    """

    spin_started = Signal()
    spin_finished = Signal()

    def __init__(
        self,
        *,
        reels: ReelSet,
        visible_rows: int,
        symbol_directory: str | Path = SYMBOL_ASSET_DIRECTORY,
        symbol_size: int = SYMBOL_DISPLAY_SIZE,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)

        if not reels:
            raise ValueError("At least one reel is required.")

        if visible_rows <= 0:
            raise ValueError("visible_rows must be positive.")

        if symbol_size <= 0:
            raise ValueError("symbol_size must be positive.")

        self._visible_rows = visible_rows
        self._symbol_size = int(symbol_size)
        self._remaining_reels = 0
        self._is_spinning = False

        self.setObjectName("animatedSlotScreen")
        self.setSizePolicy(
            QSizePolicy.Policy.Fixed,
            QSizePolicy.Policy.Fixed,
        )

        pixmaps = _SymbolPixmapStore(symbol_directory)

        self._reels = tuple(
            AnimatedReelWidget(
                reel=reel,
                pixmaps=pixmaps,
                visible_rows=visible_rows,
                symbol_size=self._symbol_size,
                parent=self,
            )
            for reel in reels
        )

        layout = QHBoxLayout(self)
        layout.setContentsMargins(
            SCREEN_FRAME_INSET,
            SCREEN_FRAME_INSET,
            SCREEN_FRAME_INSET,
            SCREEN_FRAME_INSET,
        )
        layout.setSpacing(COLUMN_SPACING)

        for reel_widget in self._reels:
            layout.addWidget(reel_widget)
            reel_widget.spin_finished.connect(
                self._on_reel_finished
            )

        screen_width = (
            len(self._reels) * self._symbol_size
            + (len(self._reels) - 1) * COLUMN_SPACING
            + 2 * SCREEN_FRAME_INSET
        )
        screen_height = (
            self._visible_rows * self._symbol_size
            + 2 * SCREEN_FRAME_INSET
        )
        self.setFixedSize(screen_width, screen_height)

    @property
    def is_spinning(self) -> bool:
        return self._is_spinning

    @property
    def reel_count(self) -> int:
        return len(self._reels)

    def sizeHint(self) -> QSize:
        return self.size()

    def paintEvent(self, event) -> None:  # type: ignore[override]
        del event

        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        half_pen = SCREEN_OUTLINE_WIDTH / 2.0
        frame = QRectF(self.rect()).adjusted(
            half_pen,
            half_pen,
            -half_pen,
            -half_pen,
        )

        painter.setBrush(SCREEN_BACKGROUND)
        painter.setPen(
            QPen(SCREEN_OUTLINE, SCREEN_OUTLINE_WIDTH)
        )

        if SCREEN_CORNER_RADIUS > 0:
            painter.drawRoundedRect(
                frame,
                SCREEN_CORNER_RADIUS,
                SCREEN_CORNER_RADIUS,
            )
        else:
            painter.drawRect(frame)

    def spin_to_stops(
        self,
        stops: Sequence[int],
        *,
        base_duration_ms: int = 1250,
        duration_step_ms: int = 180,
        base_cycles: int = 6,
    ) -> None:
        """Animate all reels to backend-provided stop positions."""
        if self._is_spinning:
            raise RuntimeError("A reel animation is already running.")

        stop_values = tuple(int(stop) for stop in stops)

        if len(stop_values) != self.reel_count:
            raise ValueError(
                f"Expected {self.reel_count} stops, "
                f"received {len(stop_values)}."
            )

        self._remaining_reels = self.reel_count
        self._is_spinning = True
        self.spin_started.emit()

        try:
            for reel_index, (reel, stop) in enumerate(
                zip(self._reels, stop_values, strict=True)
            ):
                reel.spin_to_stop(
                    stop,
                    duration_ms=(
                        base_duration_ms
                        + reel_index * duration_step_ms
                    ),
                    full_cycles=base_cycles + reel_index,
                )
        except Exception:
            self._remaining_reels = 0
            self._is_spinning = False
            raise

    def current_stops(self) -> tuple[int, ...]:
        return tuple(reel.current_stop for reel in self._reels)

    def current_screen(self) -> tuple[tuple[Symbol, ...], ...]:
        """Return the displayed screen in backend row-major layout."""
        reel_symbols = tuple(
            reel.visible_symbols()
            for reel in self._reels
        )

        return tuple(
            tuple(
                reel_symbols[reel_index][row_index]
                for reel_index in range(self.reel_count)
            )
            for row_index in range(self._visible_rows)
        )

    @Slot(int)
    def _on_reel_finished(self, stop: int) -> None:
        del stop

        if not self._is_spinning:
            return

        self._remaining_reels -= 1

        if self._remaining_reels == 0:
            self._is_spinning = False
            self.spin_finished.emit()