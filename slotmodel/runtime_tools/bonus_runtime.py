from __future__ import annotations

from dataclasses import dataclass, field
from typing import TypeAlias

import numpy as np
from numpy.typing import NDArray

from slotmodel.sim.eval import (
    PaylineEvaluation,
    PaylineEvaluator,
    evaluate_bonus_step,
    overlay_locked_symbols,
)
from slotmodel.sim.reels import Symbol
from slotmodel.sim.screens import ScreenModel, spin_batch


ScreenArray: TypeAlias = NDArray[np.int16]
LockMask: TypeAlias = NDArray[np.bool_]


@dataclass(frozen=True, slots=True)
class BonusAnimationStep:
    """One GUI-ready screen in a single bonus game.

    ``stops`` are always the actual sampled backend reel stops. ``screen`` is
    the screen that must be visible after applying the sticky-symbol overlay.
    The two lock masks describe the visual state before and after evaluating
    this screen.
    """

    stops: tuple[int, ...]
    screen: ScreenArray
    locked_mask_before: LockMask
    locked_mask_after: LockMask
    new_lock_mask: LockMask
    winning_pos_mask: LockMask
    payline_evaluation: PaylineEvaluation
    free_spin_number: int
    respin_number: int
    remaining_free_spins: int
    collected_scatter_count: int
    retrigger_free_spins_awarded: int
    terminal_payout_multiplier: float

    def __post_init__(self) -> None:
        if self.screen.ndim != 2:
            raise ValueError("screen must have shape (row_count, reel_count).")

        expected_shape = self.screen.shape
        for name, mask in (
            ("locked_mask_before", self.locked_mask_before),
            ("locked_mask_after", self.locked_mask_after),
            ("new_lock_mask", self.new_lock_mask),
            ("winning_pos_mask", self.winning_pos_mask),
        ):
            if mask.shape != expected_shape:
                raise ValueError(f"{name} must match screen in shape.")
            if mask.dtype != np.bool_:
                raise TypeError(f"{name} must have dtype np.bool_.")

        if len(self.stops) != expected_shape[1]:
            raise ValueError("stops must contain one position per reel.")
        if self.payline_evaluation.winning_symbols.shape[0] != 1:
            raise ValueError(
                "payline_evaluation must contain exactly one screen."
            )
        if self.free_spin_number <= 0:
            raise ValueError("free_spin_number must be positive.")
        if self.respin_number < 0:
            raise ValueError("respin_number cannot be negative.")
        if self.remaining_free_spins < 0:
            raise ValueError("remaining_free_spins cannot be negative.")
        if self.retrigger_free_spins_awarded < 0:
            raise ValueError(
                "retrigger_free_spins_awarded cannot be negative."
            )
        if self.terminal_payout_multiplier < 0.0:
            raise ValueError(
                "terminal_payout_multiplier cannot be negative."
            )
        if self.collected_scatter_count < 0:
            raise ValueError(
                "collected_scatter_count cannot be negative."
            )

    @property
    def is_respin(self) -> bool:
        return self.respin_number > 0

    @property
    def continues(self) -> bool:
        """Return whether this screen created at least one new sticky."""
        return bool(np.any(self.new_lock_mask))

    @property
    def is_terminal(self) -> bool:
        return not self.continues

    @property
    def retriggered(self) -> bool:
        return self.retrigger_free_spins_awarded > 0

    @property
    def new_lock_count(self) -> int:
        return int(np.count_nonzero(self.new_lock_mask))

    @property
    def locked_count(self) -> int:
        return int(np.count_nonzero(self.locked_mask_after))

    @property
    def spin_lock_mask(self) -> LockMask:
        """Return sticky positions that must be visible during this spin.

        For a new free spin this contains only the guaranteed Wild placed by
        the bonus runtime. For a respin it contains every position that was
        already sticky before the new screen was evaluated. Newly winning
        positions are intentionally excluded until the reel animation ends.
        """
        result = self.locked_mask_after & ~self.new_lock_mask
        result.flags.writeable = False
        return result

    @property
    def winning_payline_indices(self) -> tuple[int, ...]:
        payouts = self.payline_evaluation.payout_multipliers[0]
        return tuple(int(index) for index in np.flatnonzero(payouts > 0.0))


@dataclass(slots=True)
class BonusGameRuntime:
    """Step a single sticky-respin bonus game for presentation/runtime use.

    This class mirrors the bonus simulation rules one screen at a time so a
    GUI can animate every free spin and respin. It deliberately lives outside
    ``slotmodel.sim.analytics``: analytics remains batch-oriented, while this
    adapter retains the state needed by an interactive runtime.
    """

    model: ScreenModel
    evaluator: PaylineEvaluator
    rng: np.random.Generator
    initial_free_spins: int = 10
    retrigger_free_spins: int = 10
    min_scatter_count: int = 3

    _remaining_free_spins: int = field(init=False, repr=False)
    _completed_free_spins: int = field(init=False, default=0, repr=False)
    _total_respins: int = field(init=False, default=0, repr=False)
    _total_retriggers: int = field(init=False, default=0, repr=False)
    _total_payout_multiplier: float = field(
        init=False,
        default=0.0,
        repr=False,
    )
    _current_screen: NDArray[np.int16] | None = field(
        init=False,
        default=None,
        repr=False,
    )
    _locked_mask: NDArray[np.bool_] | None = field(
        init=False,
        default=None,
        repr=False,
    )
    _current_free_spin_number: int = field(
        init=False,
        default=0,
        repr=False,
    )
    _current_respin_number: int = field(
        init=False,
        default=0,
        repr=False,
    )
    _current_collected_scatter_count: int = field(
        init=False,
        default=0,
        repr=False
    )
    _current_retrigger_awarded: bool = field(
        init=False,
        default=False,
        repr=False
    )

    def __post_init__(self) -> None:
        if self.initial_free_spins <= 0:
            raise ValueError("initial_free_spins must be positive.")
        if self.retrigger_free_spins <= 0:
            raise ValueError("retrigger_free_spins must be positive.")
        if self.min_scatter_count <= 0:
            raise ValueError("min_scatter_count must be positive.")
        if self.model.reel_count != self.evaluator.reel_count:
            raise ValueError(
                "The screen model and payline evaluator reel counts "
                "must match."
            )
        if int(np.max(self.evaluator.payline_rows)) >= self.model.row_count:
            raise ValueError(
                "A payline row index is outside the screen model."
            )

        self._remaining_free_spins = int(self.initial_free_spins)

    @property
    def remaining_free_spins(self) -> int:
        return self._remaining_free_spins

    @property
    def completed_free_spins(self) -> int:
        return self._completed_free_spins

    @property
    def total_respins(self) -> int:
        return self._total_respins

    @property
    def total_retriggers(self) -> int:
        return self._total_retriggers

    @property
    def total_payout_multiplier(self) -> float:
        return self._total_payout_multiplier

    @property
    def is_complete(self) -> bool:
        return (
            self._remaining_free_spins == 0
            and self._current_screen is None
        )

    def next_step(self) -> BonusAnimationStep | None:
        """Generate and evaluate the next free-spin or respin screen."""
        if self._current_screen is None:
            if self._remaining_free_spins == 0:
                return None
            return self._start_free_spin()

        return self._start_respin()

    def _start_free_spin(self) -> BonusAnimationStep:
        self._remaining_free_spins -= 1
        self._current_free_spin_number = self._completed_free_spins + 1
        self._current_respin_number = 0
        self._current_collected_scatter_count = 0
        self._current_retrigger_awarded = False

        sampled = spin_batch(
            model=self.model,
            batch_size=1,
            rng=self.rng,
        )

        current_screen = sampled.screens.copy()
        locked_mask = np.zeros_like(current_screen, dtype=np.bool_)

        self._place_guaranteed_wild(
            screen=current_screen,
            locked_mask=locked_mask,
        )

        self._current_screen = current_screen
        self._locked_mask = locked_mask

        return self._evaluate_current_screen(
            stops=tuple(int(stop) for stop in sampled.stops[0]),
            locked_mask_before=np.zeros_like(
                locked_mask,
                dtype=np.bool_,
            ),
        )

    def _start_respin(self) -> BonusAnimationStep:
        if self._current_screen is None or self._locked_mask is None:
            raise RuntimeError("No active bonus free spin to respin.")

        self._current_respin_number += 1
        self._total_respins += 1

        sampled = spin_batch(
            model=self.model,
            batch_size=1,
            rng=self.rng,
        )

        locked_before = self._locked_mask.copy()
        self._current_screen = overlay_locked_symbols(
            current_screens=self._current_screen,
            replacement_screens=sampled.screens,
            locked_mask=self._locked_mask,
        )

        return self._evaluate_current_screen(
            stops=tuple(int(stop) for stop in sampled.stops[0]),
            locked_mask_before=locked_before,
        )

    def _evaluate_current_screen(
        self,
        *,
        stops: tuple[int, ...],
        locked_mask_before: NDArray[np.bool_],
    ) -> BonusAnimationStep:
        if self._current_screen is None or self._locked_mask is None:
            raise RuntimeError("No active bonus screen to evaluate.")

        evaluation = evaluate_bonus_step(
            screens=self._current_screen,
            locked_mask=self._locked_mask,
            evaluator=self.evaluator,
            min_scatter_count=self.min_scatter_count,
        )

        self._current_collected_scatter_count += int(
            evaluation.scatter_counts[0]
        )

        retrigger_count = int(
            not self._current_retrigger_awarded
            and self._current_collected_scatter_count
            >= self.min_scatter_count
        )

        if retrigger_count:
            self._current_retrigger_awarded = True

        retrigger_award = retrigger_count * self.retrigger_free_spins

        locked_after = self._locked_mask | evaluation.new_lock_mask
        continues = bool(evaluation.cont_mask[0])

        terminal_payout = 0.0
        reached_max_win = False

        if continues:
            self._locked_mask = locked_after
        else:
            free_spin_payout = float(
                evaluation.payline_evaluation.total_multiplier_per_spin[0]
            )
            remaining_to_cap = max(
                0.0,
                self.evaluator.max_win - self._total_payout_multiplier,
            )
            terminal_payout = min(
                free_spin_payout,
                remaining_to_cap,
            )
            self._total_payout_multiplier += terminal_payout
            self._completed_free_spins += 1
            reached_max_win = (
                self._total_payout_multiplier >= self.evaluator.max_win
            )

        if retrigger_award and not reached_max_win:
            self._remaining_free_spins += retrigger_award
            self._total_retriggers += retrigger_count

        if reached_max_win:
            self._remaining_free_spins = 0
            retrigger_award = 0

        step = BonusAnimationStep(
            stops=stops,
            screen=self._readonly_copy(self._current_screen[0]),
            locked_mask_before=self._readonly_copy(locked_mask_before[0]),
            locked_mask_after=self._readonly_copy(locked_after[0]),
            new_lock_mask=self._readonly_copy(evaluation.new_lock_mask[0]),
            winning_pos_mask=self._readonly_copy(
                evaluation.winning_pos_mask[0]
            ),
            payline_evaluation=evaluation.payline_evaluation,
            free_spin_number=self._current_free_spin_number,
            respin_number=self._current_respin_number,
            remaining_free_spins=self._remaining_free_spins,
            collected_scatter_count=self._current_collected_scatter_count,
            retrigger_free_spins_awarded=retrigger_award,
            terminal_payout_multiplier=terminal_payout,
        )

        if not continues:
            self._current_screen = None
            self._locked_mask = None
            self._current_respin_number = 0
            self._current_collected_scatter_count = 0
            self._current_retrigger_awarded = False

        return step

    def _place_guaranteed_wild(
        self,
        *,
        screen: NDArray[np.int16],
        locked_mask: NDArray[np.bool_],
    ) -> None:
        """Apply the same one-wild initial condition as bonus simulation."""
        position_count = self.model.row_count * self.model.reel_count
        flat_position = int(
            self.rng.integers(
                low=0,
                high=position_count,
                size=1,
                dtype=np.int32,
            )[0]
        )

        row_index = flat_position // self.model.reel_count
        reel_index = flat_position % self.model.reel_count

        screen[0, row_index, reel_index] = self.evaluator.wild_symbol
        locked_mask[0, row_index, reel_index] = True

    @staticmethod
    def _readonly_copy(values: NDArray) -> NDArray:
        result = values.copy()
        result.flags.writeable = False
        return result