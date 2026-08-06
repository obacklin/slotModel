from __future__ import annotations

import numpy as np

from PySide6.QtCore import Qt, Slot
from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QSizePolicy,
    QVBoxLayout,
)

from gui.pages.base_page import BasePage
from gui.widgets.animated_slot_widget import AnimatedSlotWidget
from slotmodel.sim.reels import read_reels
from slotmodel.sim.screens import (
    ScreenModel,
    SpinBatch,
    spin_batch,
)


WINDOW_OFFSETS = (0, 1, 2)


class SlotPage(BasePage):
    """Main slot-game workspace for individual backend spins."""

    def __init__(self) -> None:
        super().__init__(
            title="Slot",
            description=(
                "Run an individual backend spin and display the sampled "
                "reel stops using the animated slot screen."
            ),
            expand_body=True,
        )

        self._rng = np.random.default_rng()
        self._pending_spin: SpinBatch | None = None

        try:
            reels = read_reels()
            self._screen_model = ScreenModel.from_reels(
                reels=reels,
                window_offsets=WINDOW_OFFSETS,
            )
            self._slot_screen = AnimatedSlotWidget(
                reels=reels,
                visible_rows=self._screen_model.row_count,
            )
        except (OSError, TypeError, ValueError) as error:
            self.add_placeholder(
                title="Unable to create slot screen",
                description=str(error),
            )
            return

        self._spin_button = QPushButton("Spin")
        self._spin_button.setObjectName("primaryButton")

        self._status_label = QLabel(
            self._format_ready_status()
        )
        self._status_label.setObjectName("statusLabel")

        workspace = self._create_slot_workspace()
        self.body_layout.addWidget(workspace, stretch=1)

        self._spin_button.clicked.connect(self._start_spin)
        self._slot_screen.spin_finished.connect(
            self._finish_spin
        )

    def _create_slot_workspace(self) -> QFrame:
        """
        Create this page's borderless workspace.

        The page-level title and description are created by BasePage. This
        workspace creates the on-screen text "Base-game spin", the explanatory
        paragraph, the fixed 5 x 3 animation, and the status/control row.
        """
        workspace = QFrame()
        workspace.setObjectName("slotWorkspace")
        workspace.setSizePolicy(
            QSizePolicy.Policy.Expanding,
            QSizePolicy.Policy.Expanding,
        )

        layout = QVBoxLayout(workspace)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(14)

        section_title = QLabel("Base-game spin")
        section_title.setObjectName("cardTitle")

        section_description = QLabel(
            "The backend samples one stop on each configured reel. "
            "The animation receives those stop positions and does not "
            "generate a separate visual outcome."
        )
        section_description.setObjectName("cardDescription")
        section_description.setWordWrap(True)

        controls = QHBoxLayout()
        controls.setContentsMargins(0, 0, 0, 0)
        controls.setSpacing(12)
        controls.addWidget(self._status_label, stretch=1)
        controls.addWidget(self._spin_button)

        layout.addWidget(section_title)
        layout.addWidget(section_description)
        layout.addSpacing(6)

        # AnimatedSlotWidget is fixed-size. The surrounding layout item grows,
        # but alignment keeps the complete 5 x 3 screen centred without
        # changing row height, reel width, or spacing.
        layout.addWidget(
            self._slot_screen,
            stretch=1,
            alignment=Qt.AlignmentFlag.AlignCenter,
        )
        layout.addLayout(controls)

        return workspace

    @Slot()
    def _start_spin(self) -> None:
        if self._slot_screen.is_spinning:
            return

        try:
            result = spin_batch(
                model=self._screen_model,
                batch_size=1,
                rng=self._rng,
            )

            stops = tuple(
                int(stop)
                for stop in result.stops[0]
            )

            self._pending_spin = result
            self._spin_button.setEnabled(False)
            self._status_label.setText(
                "Spinning to backend stops: "
                + self._format_stops(stops)
            )

            self._slot_screen.spin_to_stops(stops)
        except (RuntimeError, TypeError, ValueError) as error:
            self._pending_spin = None
            self._spin_button.setEnabled(True)
            self._status_label.setText(
                f"Spin failed: {error}"
            )

    @Slot()
    def _finish_spin(self) -> None:
        result = self._pending_spin
        self._pending_spin = None
        self._spin_button.setEnabled(True)

        if result is None:
            self._status_label.setText(
                "Animation finished without a pending backend result."
            )
            return

        displayed_screen = np.asarray(
            self._slot_screen.current_screen(),
            dtype=np.int16,
        )
        backend_screen = result.screens[0]
        stops = tuple(
            int(stop)
            for stop in result.stops[0]
        )

        if not np.array_equal(
            displayed_screen,
            backend_screen,
        ):
            self._status_label.setText(
                "Display/backend mismatch at stops: "
                + self._format_stops(stops)
            )
            return

        self._status_label.setText(
            "Stopped at "
            + self._format_stops(stops)
            + " · displayed screen verified"
        )

    def _format_ready_status(self) -> str:
        stops = self._slot_screen.current_stops()
        return "Ready · current stops: " + self._format_stops(stops)

    @staticmethod
    def _format_stops(stops: tuple[int, ...]) -> str:
        return ", ".join(
            f"R{reel_index + 1}={stop}"
            for reel_index, stop in enumerate(stops)
        )