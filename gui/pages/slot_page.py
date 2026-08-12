from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from PySide6.QtCore import QTimer, Qt, Slot
from PySide6.QtWidgets import (
    QCheckBox,
    QFrame,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)

from gui.pages.base_page import BasePage
from gui.widgets.animated_slot_widget import AnimatedSlotWidget
from gui.widgets.scalable_slot_view import ScalableSlotView
from slotmodel.runtime_tools import (
    BonusAnimationStep,
    BonusGameRuntime,
    BonusStopGenerator,
)
from slotmodel.sim.eval import (
    PaylineEvaluation,
    PaylineEvaluator,
    count_scatter_symbols,
)
from slotmodel.sim.paylines.paylines import PAYLINES
from slotmodel.sim.paytable import PAYTABLE
from slotmodel.sim.reels import read_reels
from slotmodel.sim.screens import (
    ScreenModel,
    SpinBatch,
    spin_batch,
)


WINDOW_OFFSETS = (0, 1, 2)
BASE_GAME_BET = 1.0
BONUS_STEP_PAUSE_MS = 650
BONUS_SPIN_DURATION_MS = 900
BONUS_SPIN_DURATION_STEP_MS = 120
BONUS_SPIN_CYCLES = 4
AUTO_SPIN_PAUSE_MS = 300


@dataclass(frozen=True, slots=True)
class _PendingSpin:
    spin: SpinBatch
    evaluation: PaylineEvaluation
    enters_bonus: bool


class SlotPage(BasePage):
    """Main slot-game workspace for individual backend spins."""

    def __init__(self) -> None:
        super().__init__(
            title="Slot",
            description=(
                "Run an individual backend spin or force and animate a "
                "complete sticky-respin bonus game."
            ),
            expand_body=True,
        )

        self._rng = np.random.default_rng()
        self._pending_spin: _PendingSpin | None = None
        self._pending_bonus_step: BonusAnimationStep | None = None
        self._bonus_runtime: BonusGameRuntime | None = None

        try:
            reels = read_reels()
            self._screen_model = ScreenModel.from_reels(
                reels=reels,
                window_offsets=WINDOW_OFFSETS,
            )
            self._payline_evaluator = (
                PaylineEvaluator.from_definitions(
                    paylines=PAYLINES,
                    paytable=PAYTABLE,
                )
            )
            self._bonus_stop_generator = BonusStopGenerator(
                model=self._screen_model,
            )
            self._validate_game_geometry()

            self._slot_screen = AnimatedSlotWidget(
                reels=reels,
                visible_rows=self._screen_model.row_count,
                paylines=PAYLINES.lines,
            )
        except (OSError, TypeError, ValueError) as error:
            self.add_placeholder(
                title="Unable to create slot screen",
                description=str(error),
            )
            return

        self._spin_button = QPushButton("Spin")
        self._spin_button.setObjectName("primaryButton")
        self._spin_button.setFixedWidth(170)

        self._auto_spin_checkbox = QCheckBox("Auto Spin")
        self._auto_spin_checkbox.setObjectName("autoSpinCheckbox")

        self._bonus_button = QPushButton("Bonus Game")
        self._bonus_button.setObjectName("bonusButton")
        self._bonus_button.setFixedWidth(170)

        self._free_spins_label = QLabel(
            self._format_free_spins_remaining(0)
        )
        self._free_spins_label.setObjectName("freeSpinsDisplay")
        self._free_spins_label.setAlignment(
            Qt.AlignmentFlag.AlignLeft
            | Qt.AlignmentFlag.AlignVCenter
        )
        self._free_spins_label.setFixedWidth(190)

        self._scatter_count_label = QLabel(
            self._format_collected_scatters(0)
        )
        self._scatter_count_label.setObjectName(
            "scatterCountDisplay"
        )
        self._scatter_count_label.setAlignment(
            Qt.AlignmentFlag.AlignLeft
            | Qt.AlignmentFlag.AlignVCenter
        )
        self._scatter_count_label.setFixedWidth(190)

        self._status_label = QLabel(self._format_ready_status())
        self._status_label.setObjectName("statusLabel")

        self._payout_label = QLabel(self._format_payout(0.0))
        self._payout_label.setObjectName("payoutDisplay")
        self._payout_label.setAlignment(
            Qt.AlignmentFlag.AlignRight
            | Qt.AlignmentFlag.AlignVCenter
        )
        self._payout_label.setMinimumWidth(190)

        self._slot_view = ScalableSlotView(self._slot_screen)

        workspace = self._create_slot_workspace()
        self.body_layout.addWidget(workspace, stretch=1)

        self._spin_button.clicked.connect(self._start_spin)
        self._bonus_button.clicked.connect(self._start_bonus_game)
        self._slot_screen.spin_finished.connect(
            self._finish_animation
        )

    def _create_slot_workspace(self) -> QFrame:
        """Create a responsive left-aligned slot workspace."""
        workspace = QFrame()
        workspace.setObjectName("slotWorkspace")
        workspace.setSizePolicy(
            QSizePolicy.Policy.Expanding,
            QSizePolicy.Policy.Expanding,
        )

        layout = QVBoxLayout(workspace)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(8)

        section_title = QLabel("Slot spin")
        section_title.setObjectName("cardTitle")

        section_description = QLabel(
            "Spin samples a normal backend outcome. Bonus Game first "
            "forces a valid feature trigger, then animates the complete "
            "backend bonus with sticky winning symbols and retriggers."
        )
        section_description.setObjectName("cardDescription")
        section_description.setWordWrap(True)

        # The slot column is the only horizontally flexible part of the game
        # row. The native AnimatedSlotWidget lives inside ScalableSlotView, so
        # it can shrink uniformly without changing any animation coordinates.
        slot_column = QWidget()
        slot_column.setObjectName("slotGroup")
        slot_column.setSizePolicy(
            QSizePolicy.Policy.Expanding,
            QSizePolicy.Policy.Expanding,
        )
        slot_column.setMinimumWidth(1)

        slot_column_layout = QVBoxLayout(slot_column)
        slot_column_layout.setContentsMargins(0, 0, 0, 0)
        slot_column_layout.setSpacing(8)

        payout_row = QWidget()
        payout_row.setObjectName("slotGroup")
        payout_row.setSizePolicy(
            QSizePolicy.Policy.Expanding,
            QSizePolicy.Policy.Fixed,
        )
        payout_layout = QHBoxLayout(payout_row)
        payout_layout.setContentsMargins(0, 0, 0, 0)
        payout_layout.setSpacing(0)
        payout_layout.addStretch(1)
        payout_layout.addWidget(self._payout_label)

        slot_column_layout.addWidget(payout_row)
        slot_column_layout.addWidget(self._slot_view, stretch=1)

        control_panel = QWidget()
        control_panel.setObjectName("slotControlPanel")
        control_panel.setSizePolicy(
            QSizePolicy.Policy.Fixed,
            QSizePolicy.Policy.Fixed,
        )

        control_layout = QVBoxLayout(control_panel)
        control_layout.setContentsMargins(0, 0, 0, 0)
        control_layout.setSpacing(10)
        control_layout.setAlignment(
            Qt.AlignmentFlag.AlignLeft
            | Qt.AlignmentFlag.AlignTop
        )
        control_layout.addWidget(
            self._spin_button,
            alignment=Qt.AlignmentFlag.AlignLeft,
        )
        control_layout.addWidget(
            self._auto_spin_checkbox,
            alignment=Qt.AlignmentFlag.AlignLeft,
        )
        control_layout.addSpacing(4)
        control_layout.addWidget(
            self._bonus_button,
            alignment=Qt.AlignmentFlag.AlignLeft,
        )
        control_layout.addSpacing(8)
        control_layout.addWidget(
            self._free_spins_label,
            alignment=Qt.AlignmentFlag.AlignLeft,
        )
        control_layout.addWidget(
            self._scatter_count_label,
            alignment=Qt.AlignmentFlag.AlignLeft
        )

        game_row = QHBoxLayout()
        game_row.setContentsMargins(0, 0, 0, 0)
        game_row.setSpacing(18)
        game_row.setAlignment(
            Qt.AlignmentFlag.AlignLeft
            | Qt.AlignmentFlag.AlignTop
        )
        game_row.addWidget(slot_column, stretch=1)
        game_row.addWidget(
            control_panel,
            stretch=0,
            alignment=(
                Qt.AlignmentFlag.AlignLeft
                | Qt.AlignmentFlag.AlignTop
            ),
        )

        layout.addWidget(section_title)
        layout.addWidget(section_description)
        layout.addLayout(game_row, stretch=1)
        layout.addWidget(self._status_label)

        return workspace

    @Slot()
    def _start_spin(self) -> None:
        """Generate and animate one normal base-game spin."""
        if self._animation_or_bonus_active():
            return

        try:
            result = spin_batch(
                model=self._screen_model,
                batch_size=1,
                rng=self._rng,
            )
            self._begin_spin(
                result=result,
                enters_bonus=False,
                status_prefix="Spinning to backend stops: ",
            )
        except (RuntimeError, TypeError, ValueError) as error:
            self._handle_spin_error(error)

    @Slot()
    def _start_bonus_game(self) -> None:
        """Generate a guaranteed entry and animate the complete bonus."""
        if self._animation_or_bonus_active():
            return

        self._auto_spin_checkbox.setChecked(False)
        self._auto_spin_checkbox.setEnabled(False)

        try:
            result = self._bonus_stop_generator.spin(self._rng)
            self._begin_spin(
                result=result,
                enters_bonus=True,
                status_prefix="Spinning to forced bonus stops: ",
            )
        except (RuntimeError, TypeError, ValueError) as error:
            self._handle_spin_error(error)

    def _begin_spin(
        self,
        *,
        result: SpinBatch,
        enters_bonus: bool,
        status_prefix: str,
    ) -> None:
        """Prepare shared GUI state and animate a backend result."""
        evaluation = self._payline_evaluator.evaluate(result.screens)
        stops = tuple(int(stop) for stop in result.stops[0])

        self._bonus_runtime = None
        self._pending_bonus_step = None
        self._slot_screen.clear_winning_paylines()
        self._slot_screen.clear_sticky_symbols()
        self._slot_screen.set_bonus_mode(False)
        self._payout_label.setText(self._format_payout(0.0))
        self._free_spins_label.setText(
            self._format_free_spins_remaining(0)
        )
        self._scatter_count_label.setText(
            self._format_collected_scatters(0)
        )

        self._pending_spin = _PendingSpin(
            spin=result,
            evaluation=evaluation,
            enters_bonus=enters_bonus,
        )
        self._set_spin_controls_enabled(False)
        self._status_label.setText(
            status_prefix + self._format_stops(stops)
        )

        self._slot_screen.spin_to_stops(stops)

    def _handle_spin_error(self, error: Exception) -> None:
        self._pending_spin = None
        self._pending_bonus_step = None
        self._bonus_runtime = None
        self._slot_screen.clear_winning_paylines()
        self._slot_screen.clear_sticky_symbols()
        self._slot_screen.set_bonus_mode(False)
        self._free_spins_label.setText(
            self._format_free_spins_remaining(0)
        )
        self._scatter_count_label.setText(
            self._format_collected_scatters(0)
        )
        self._auto_spin_checkbox.setEnabled(True)
        self._set_spin_controls_enabled(True)
        self._status_label.setText(f"Spin failed: {error}")

    @Slot()
    def _finish_animation(self) -> None:
        if self._pending_bonus_step is not None:
            self._finish_bonus_step()
            return

        self._finish_base_or_entry_spin()

    def _finish_base_or_entry_spin(self) -> None:
        pending = self._pending_spin
        self._pending_spin = None

        if pending is None:
            self._set_spin_controls_enabled(True)
            self._status_label.setText(
                "Animation finished without a pending backend result."
            )
            return

        displayed_screen = np.asarray(
            self._slot_screen.current_screen(),
            dtype=np.int16,
        )
        backend_screen = pending.spin.screens[0]
        stops = tuple(
            int(stop)
            for stop in pending.spin.stops[0]
        )

        if not np.array_equal(displayed_screen, backend_screen):
            self._handle_display_mismatch(stops)
            return

        line_payouts = pending.evaluation.payout_multipliers[0]
        winning_indices = tuple(
            int(index)
            for index in np.flatnonzero(line_payouts > 0.0)
        )
        payout = (
            float(
                pending.evaluation.total_multiplier_per_spin[0]
            )
            * BASE_GAME_BET
        )

        self._slot_screen.show_winning_paylines(winning_indices)
        self._payout_label.setText(self._format_payout(payout))

        if pending.enters_bonus:
            self._enter_bonus(pending, stops)
            return

        self._slot_screen.set_bonus_mode(False)

        if winning_indices:
            displayed_line_numbers = ", ".join(
                str(index + 1)
                for index in winning_indices
            )
            self._status_label.setText(
                "Win on payline"
                + ("s " if len(winning_indices) > 1 else " ")
                + displayed_line_numbers
                + " · stopped at "
                + self._format_stops(stops)
                + " · displayed screen verified"
            )
        else:
            self._status_label.setText(
                "No payline win · stopped at "
                + self._format_stops(stops)
                + " · displayed screen verified"
            )

        if self._auto_spin_checkbox.isChecked():
            self._set_spin_controls_enabled(False)
            QTimer.singleShot(
                AUTO_SPIN_PAUSE_MS,
                self._continue_auto_spin,
            )
        else:
            self._set_spin_controls_enabled(True)

    @Slot()
    def _continue_auto_spin(self) -> None:
        """Start the next base spin while Auto Spin remains selected."""
        if self._animation_or_bonus_active():
            return

        if not self._auto_spin_checkbox.isChecked():
            self._set_spin_controls_enabled(True)
            return

        self._start_spin()

    def _enter_bonus(
        self,
        pending: _PendingSpin,
        stops: tuple[int, ...],
    ) -> None:
        scatter_count = int(
            count_scatter_symbols(pending.spin.screens)[0]
        )

        self._slot_screen.set_bonus_mode(True)
        self._bonus_runtime = BonusGameRuntime(
            model=self._screen_model,
            evaluator=self._payline_evaluator,
            rng=self._rng,
        )
        self._free_spins_label.setText(
            self._format_free_spins_remaining(
                self._bonus_runtime.remaining_free_spins
            )
        )
        self._scatter_count_label.setText(
            self._format_collected_scatters(0)
        )

        self._status_label.setText(
            f"Bonus triggered with {scatter_count} scatters · "
            + self._format_stops(stops)
            + f" · {self._bonus_runtime.remaining_free_spins} "
            "free spins awarded"
        )

        QTimer.singleShot(
            BONUS_STEP_PAUSE_MS,
            self._start_next_bonus_step,
        )

    @Slot()
    def _start_next_bonus_step(self) -> None:
        runtime = self._bonus_runtime

        if runtime is None or self._slot_screen.is_spinning:
            return

        try:
            step = runtime.next_step()

            if step is None:
                self._finish_bonus_game()
                return

            self._pending_bonus_step = step
            self._slot_screen.clear_winning_paylines()

            if not step.is_respin:
                self._slot_screen.clear_sticky_symbols()
                self._scatter_count_label.setText(
                    self._format_collected_scatters(0)
                )

            # The guaranteed Wild is part of the bonus state before the reel
            # motion starts. Existing stickies are likewise retained during
            # respins. Newly won sticky positions are still revealed only
            # after this animation completes.
            self._slot_screen.set_sticky_screen(
                step.screen,
                step.spin_lock_mask,
            )
            self._free_spins_label.setText(
                self._format_free_spins_remaining(
                    step.remaining_free_spins
                )
            )

            self._payout_label.setText(
                self._format_payout(
                    runtime.total_payout_multiplier
                    * BASE_GAME_BET
                )
            )
            self._status_label.setText(
                self._format_bonus_step_start(step)
            )

            self._slot_screen.spin_to_stops(
                step.stops,
                base_duration_ms=BONUS_SPIN_DURATION_MS,
                duration_step_ms=BONUS_SPIN_DURATION_STEP_MS,
                base_cycles=BONUS_SPIN_CYCLES,
            )
        except (RuntimeError, TypeError, ValueError) as error:
            self._handle_bonus_error(error)

    def _finish_bonus_step(self) -> None:
        step = self._pending_bonus_step
        self._pending_bonus_step = None
        runtime = self._bonus_runtime

        if step is None or runtime is None:
            self._handle_bonus_error(
                RuntimeError("Missing active bonus runtime state.")
            )
            return

        try:
            self._slot_screen.set_sticky_screen(
                step.screen,
                step.locked_mask_after,
            )
            self._slot_screen.show_winning_paylines(
                step.winning_payline_indices
            )

            displayed_screen = np.asarray(
                self._slot_screen.current_screen(),
                dtype=np.int16,
            )

            if not np.array_equal(displayed_screen, step.screen):
                self._handle_display_mismatch(step.stops)
                return

            self._payout_label.setText(
                self._format_payout(
                    runtime.total_payout_multiplier
                    * BASE_GAME_BET
                )
            )
            self._free_spins_label.setText(
                self._format_free_spins_remaining(
                    step.remaining_free_spins
                )
            )
            self._scatter_count_label.setText(
                self._format_collected_scatters(
                    step.collected_scatter_count
                )
            )
            self._status_label.setText(
                self._format_bonus_step_result(step)
            )

            QTimer.singleShot(
                BONUS_STEP_PAUSE_MS,
                self._start_next_bonus_step,
            )
        except (RuntimeError, TypeError, ValueError) as error:
            self._handle_bonus_error(error)

    def _finish_bonus_game(self) -> None:
        runtime = self._bonus_runtime

        if runtime is None:
            return

        total_payout = (
            runtime.total_payout_multiplier * BASE_GAME_BET
        )
        completed_free_spins = runtime.completed_free_spins
        total_respins = runtime.total_respins
        total_retriggers = runtime.total_retriggers

        self._bonus_runtime = None
        self._pending_bonus_step = None
        self._free_spins_label.setText(
            self._format_free_spins_remaining(0)
        )
        self._scatter_count_label.setText(
            self._format_collected_scatters(0)
        )
        self._auto_spin_checkbox.setEnabled(True)
        self._set_spin_controls_enabled(True)
        self._payout_label.setText(self._format_payout(total_payout))
        self._status_label.setText(
            "Bonus complete · "
            f"{completed_free_spins} free spins · "
            f"{total_respins} respins · "
            f"{total_retriggers} retriggers · "
            f"payout {total_payout:.2f}"
        )

    def _handle_bonus_error(self, error: Exception) -> None:
        self._pending_bonus_step = None
        self._bonus_runtime = None
        self._slot_screen.clear_winning_paylines()
        self._slot_screen.clear_sticky_symbols()
        self._slot_screen.set_bonus_mode(False)
        self._free_spins_label.setText(
            self._format_free_spins_remaining(0)
        )
        self._scatter_count_label.setText(
            self._format_collected_scatters(0)
        )
        self._auto_spin_checkbox.setEnabled(True)
        self._set_spin_controls_enabled(True)
        self._status_label.setText(f"Bonus animation failed: {error}")

    def _handle_display_mismatch(
        self,
        stops: tuple[int, ...],
    ) -> None:
        self._pending_spin = None
        self._pending_bonus_step = None
        self._bonus_runtime = None
        self._slot_screen.clear_winning_paylines()
        self._slot_screen.clear_sticky_symbols()
        self._slot_screen.set_bonus_mode(False)
        self._payout_label.setText(self._format_payout(0.0))
        self._free_spins_label.setText(
            self._format_free_spins_remaining(0)
        )
        self._scatter_count_label.setText(
            self._format_collected_scatters(0)
        )
        self._auto_spin_checkbox.setEnabled(True)
        self._set_spin_controls_enabled(True)
        self._status_label.setText(
            "Display/backend mismatch at stops: "
            + self._format_stops(stops)
        )

    def _animation_or_bonus_active(self) -> bool:
        return (
            self._slot_screen.is_spinning
            or self._bonus_runtime is not None
            or self._pending_spin is not None
        )

    def _set_spin_controls_enabled(self, enabled: bool) -> None:
        self._spin_button.setEnabled(enabled)
        self._bonus_button.setEnabled(enabled)

    def _validate_game_geometry(self) -> None:
        if PAYLINES.reel_count != self._screen_model.reel_count:
            raise ValueError(
                "Configured paylines and reel set use different "
                "reel counts."
            )

        if PAYLINES.row_count != self._screen_model.row_count:
            raise ValueError(
                "Configured paylines and slot window use different "
                "row counts."
            )

    def _format_ready_status(self) -> str:
        stops = self._slot_screen.current_stops()
        return "Ready · current stops: " + self._format_stops(stops)

    @staticmethod
    def _format_bonus_step_start(
        step: BonusAnimationStep,
    ) -> str:
        if step.is_respin:
            return (
                f"Bonus free spin {step.free_spin_number} · "
                f"respin {step.respin_number} · "
                f"{step.locked_count - step.new_lock_count} "
                "sticky positions held"
            )

        return (
            f"Bonus free spin {step.free_spin_number} · "
            f"{step.remaining_free_spins} free spins currently remaining"
        )

    @staticmethod
    def _format_bonus_step_result(
        step: BonusAnimationStep,
    ) -> str:
        parts: list[str] = [
            f"Bonus free spin {step.free_spin_number}"
        ]

        if step.is_respin:
            parts.append(f"respin {step.respin_number}")

        if step.new_lock_count:
            parts.append(
                f"{step.new_lock_count} new sticky "
                + (
                    "position"
                    if step.new_lock_count == 1
                    else "positions"
                )
            )

        if step.retriggered:
            parts.append(
                f"retrigger +{step.retrigger_free_spins_awarded} "
                "free spins"
            )

        if step.is_terminal:
            parts.append(
                "terminal payout "
                f"{step.terminal_payout_multiplier * BASE_GAME_BET:.2f}"
            )
            parts.append(
                f"{step.remaining_free_spins} free spins remaining"
            )
        else:
            parts.append("respin continues")

        return " · ".join(parts)

    @staticmethod
    def _format_free_spins_remaining(count: int) -> str:
        return f"Free Spins: {int(count)}"

    @staticmethod
    def _format_collected_scatters(count: int) -> str:
        return f"Scatters Collected: {int(count)}"

    @staticmethod
    def _format_payout(payout: float) -> str:
        return f"Payout: {payout:.2f}"

    @staticmethod
    def _format_stops(stops: tuple[int, ...]) -> str:
        return ", ".join(
            f"R{reel_index + 1}={stop}"
            for reel_index, stop in enumerate(stops)
        )