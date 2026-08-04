from __future__ import annotations

from dataclasses import dataclass
from typing import TypeAlias

import numpy as np
from numpy.typing import NDArray

from slotmodel.sim.eval.bonus import (
    LockMaskBatch,
    evaluate_bonus_step,
    overlay_locked_symbols
)
from slotmodel.sim.eval.payline_eval import PaylineEvaluator
from slotmodel.sim.screens import (
    ScreenBatchArray,
    ScreenModel,
    spin_batch
)

CountBatch: TypeAlias = NDArray[np.int32]
MultiplierBatch: TypeAlias = NDArray[np.float64]

@dataclass(frozen=True, slots=True)
class BonusFreeSpinBatchResult:
    """Termial outcome for batch of free spins."""

    final_screens: ScreenBatchArray
    final_locked_mask: LockMaskBatch
    payout_multipliers: MultiplierBatch
    respin_counts: CountBatch
    retrigger_counts: CountBatch

    def __post_init__(self) -> None:
        if self.final_screens.ndim != 3:
            raise ValueError(
                "final_screens must be 3 dim."
            )
        if self.final_locked_mask.shape != self.final_screens.shape:
            raise ValueError(
                "final_locked_mask must match final_screens in shape."
            )

        batch_size = self.final_screens.shape[0]

        for name, values in (
            ("payout_multipliers", self.payout_multipliers),
            ("respin_counts", self.respin_counts),
            ("regrigger_counts", self.retrigger_counts)
        ):
            if values.shape != (batch_size, ):
                raise ValueError(
                    f"{name} must contain one value per free spin."
                )

    @property
    def evaluated_screen_counts(self) -> CountBatch:
        """Return initial-screen plus respin counts per free spinn."""
        return self.respin_counts + np.int32(1)

    @property
    def win_mask(self) -> NDArray[np.bool_]:
        return self.payout_multipliers > 0.0

@dataclass(frozen=True, slots=True)
class BonusGameSimulationResult:
    """Bonus results from indep. simulated bonus games."""

    payout_multipliers: MultiplierBatch
    free_spin_counts: CountBatch
    respin_counts: CountBatch
    retrigger_counts: CountBatch
    winning_free_spin_counts: CountBatch

    def __post_init__(self) -> None:
        if self.payout_multipliers.ndim != 1:
            raise ValueError(
                "Result arrays must be one-dim."
            )
        expected_shape = self.payout_multipliers.shape

        for name, values in (
            ("free_spin_counts", self.free_spin_counts),
            ("respin_counts", self.respin_counts),
            ("retrigger_counts", self.retrigger_counts),
            (
                "winning_free_spin_counts",
                self.winning_free_spin_counts
            )
        ):
            if values.shape != expected_shape:
                raise ValueError(
                    f"{name} must match payout_multipliers in shape."
                )

    @property
    def total_bonus_games(self) -> int:
        return int(self.payout_multipliers.size)
    @property
    def mean_payout_multiplier(self) -> float:
        return float(np.mean(self.payout_multipliers))

    @property
    def payout_standard_error(self) -> float:
        if self.total_bonus_games <= 1:
            return 0.0

        return float(
            np.std(self.payout_multipliers, ddof=1)
            / np.sqrt(self.total_bonus_games)
        )
    @property
    def mean_free_spinn_count(self) -> float:
        return float(np.mean(self.free_spin_counts))

    @property
    def mean_respin_count(self) -> float:
        return float(np.mean(self.respin_counts))

    @property
    def mean_retrigger_count(self) -> float:
        return float(np.mean(self.retrigger_counts))

def _validate_bonus_geometry(
    model: ScreenModel,
    evaluator: PaylineEvaluator,
) -> None:
    if model.reel_count != evaluator.reel_count:
        raise ValueError(
            "The screen model and payline evaluator "
            "reel counts must match."
        )
    if int(np.max(evaluator.payline_rows)) >= model.row_count:
        raise ValueError(
            "A payline row index is outside the screen model."
        )

def _place_guaranteed_wilds(
    screens: ScreenBatchArray,
    rng: np.random.Generator,
    wild_symbol: int,
) -> LockMaskBatch:
    """Replace and lock one uniformly selected position per screen."""

    batch_size, row_count, reel_count = screens.shape
    position_count = row_count * reel_count

    flat_positions = rng.integers(
        low=0,
        high=position_count,
        size=batch_size,
        dtype=np.int32,
    )

    row_indices = flat_positions // reel_count
    reel_indices = flat_positions % reel_count
    batch_indices = np.arange(batch_size)

    screens[
        batch_indices,
        row_indices,
        reel_indices,
    ] = wild_symbol

    locked_mask = np.zeros(
        screens.shape,
        dtype=np.bool_,
    )

    locked_mask[
        batch_indices,
        row_indices,
        reel_indices,
    ] = True

    return locked_mask

def simulate_bonus_free_spin_batch(
        model: ScreenModel,
        evaluator: PaylineEvaluator,
        batch_size: int,
        rng: np.random.Generator,
        min_scatter_count: int = 3
) -> BonusFreeSpinBatchResult:
    if batch_size <= 0:
        raise ValueError("batch_size must be positive.")
    if min_scatter_count <= 0:
        raise ValueError(
            "min_scatter_count must be positive."
        )
    _validate_bonus_geometry(
        model=model,
        evaluator=evaluator
    )

    current_screens = spin_batch(
        model=model,
        batch_size=batch_size,
        rng=rng
    ).screens

    locked_mask = _place_guaranteed_wilds(
        screens=current_screens,
        rng=rng,
        wild_symbol=evaluator.wild_symbol
    )

    final_screens = np.empty_like(current_screens)
    final_locked_mask = np.empty_like(locked_mask)

    payout_multipliers = np.zeros(
        batch_size,
        dtype=np.float64
    )
    respin_counts = np.zeros(
        batch_size,
        dtype=np.int32
    )
    retrigger_counts = np.zeros(
        batch_size,
        dtype=np.int32
    )
    active_mask = np.ones(
        batch_size,
        dtype=np.bool_
    )

    while np.any(active_mask):
        active_indices = np.flatnonzero(active_mask)

        active_screens = current_screens[active_indices]
        active_locks = locked_mask[active_indices]

        step = evaluate_bonus_step(
            screens=active_screens,
            locked_mask=active_locks,
            evaluator=evaluator,
            min_scatter_count=min_scatter_count
        )

        retrigger_counts[active_indices] += (
            step.retrigger_mask.astype(
                np.int32,
                copy=False
            )
        )

        continue_local = step.cont_mask
        terminal_local = ~continue_local

        terminal_indices = active_indices[terminal_local]

        if terminal_indices.size:
            terminal_evaluation = (
                step
                .payline_evaluation
                .total_multiplier_per_spin[terminal_local]
            )
            payout_multipliers[terminal_indices] = (
                terminal_evaluation
            )

            final_screens[terminal_indices] = (
                active_screens[terminal_local]
            )

            final_locked_mask[terminal_indices] = (
                active_locks[terminal_local]
            )

            active_mask[terminal_indices] = False

        continuing_indices = active_indices[continue_local]

        if continuing_indices.size:
            updated_locks = (
                active_locks[continue_local]
                | step.new_lock_mask[continue_local]
            )

            locked_mask[continuing_indices] = updated_locks

            replacement_screens = spin_batch(
                model=model,
                batch_size=continuing_indices.size,
                rng=rng
            ).screens

            current_screens[continuing_indices] = (
                overlay_locked_symbols(
                    current_screens=active_screens[continue_local],
                    replacement_screens=replacement_screens,
                    locked_mask=updated_locks
                )
            )

            respin_counts[continuing_indices] += 1

    return BonusFreeSpinBatchResult(
        final_screens=final_screens,
        final_locked_mask=final_locked_mask,
        payout_multipliers=payout_multipliers,
        respin_counts=respin_counts,
        retrigger_counts=retrigger_counts
    )

def _simulate_bonus_game_batch(
        model: ScreenModel,
        evaluator: PaylineEvaluator,
        batch_size: int,
        rng: np.random.Generator,
        initial_free_spins: int,
        retrigger_free_spins: int,
        min_scatter_count: int
) -> BonusGameSimulationResult:

    remaining_free_spins = np.full(
        batch_size,
        initial_free_spins,
        dtype=np.int32
    )

    payout_multipliers = np.zeros(
        batch_size,
        dtype=np.float64
    )
    free_spin_counts = np.zeros(
        batch_size,
        dtype=np.int32
    )
    respin_counts = np.zeros(
        batch_size,
        dtype=np.int32
    )
    retrigger_counts = np.zeros(
        batch_size,
        dtype=np.int32
    )
    winning_free_spin_counts = np.zeros(
        batch_size,
        dtype=np.int32
    )

    while np.any(remaining_free_spins > 0):
        active_indices = np.flatnonzero(
            remaining_free_spins > 0
        )

        remaining_free_spins[active_indices] -= 1

        free_spin_result = simulate_bonus_free_spin_batch(
            model=model,
            evaluator=evaluator,
            batch_size=active_indices.size,
            rng=rng,
            min_scatter_count=min_scatter_count,
        )

        payout_multipliers[active_indices] += (
            free_spin_result.payout_multipliers
        )

        free_spin_counts[active_indices] += 1

        respin_counts[active_indices] += (
            free_spin_result.respin_counts
        )

        retrigger_counts[active_indices] += (
            free_spin_result.retrigger_counts
        )

        winning_free_spin_counts[active_indices] += (
            free_spin_result.win_mask.astype(
                np.int32,
                copy=False
            )
        )

        remaining_free_spins[active_indices] += (
            retrigger_free_spins
            * free_spin_result.retrigger_counts
        )

    return BonusGameSimulationResult(
        payout_multipliers=payout_multipliers,
        free_spin_counts=free_spin_counts,
        respin_counts=respin_counts,
        retrigger_counts=retrigger_counts,
        winning_free_spin_counts=winning_free_spin_counts
    )

def simulate_bonus_games(
    model: ScreenModel,
    evaluator: PaylineEvaluator,
    total_bonus_games: int,
    batch_size: int,
    rng: np.random.Generator,
    initial_free_spins: int = 10,
    retrigger_free_spins: int = 10,
    min_scatter_count: int = 3,
) -> BonusGameSimulationResult:
    """
    Simulate complete bonus games in bounded-memory batches.
    """

    if total_bonus_games <= 0:
        raise ValueError(
            "total_bonus_games must be positive."
        )

    if batch_size <= 0:
        raise ValueError("batch_size must be positive.")

    if initial_free_spins <= 0:
        raise ValueError(
            "initial_free_spins must be positive."
        )

    if retrigger_free_spins <= 0:
        raise ValueError(
            "retrigger_free_spins must be positive."
        )

    if min_scatter_count <= 0:
        raise ValueError(
            "minimum_scatter_count must be positive."
        )

    _validate_bonus_geometry(
        model=model,
        evaluator=evaluator,
    )

    payout_parts: list[MultiplierBatch] = []
    free_spin_parts: list[CountBatch] = []
    respin_parts: list[CountBatch] = []
    retrigger_parts: list[CountBatch] = []
    winning_parts: list[CountBatch] = []

    completed_games = 0

    while completed_games < total_bonus_games:
        current_batch_size = min(
            batch_size,
            total_bonus_games - completed_games,
        )

        batch_result = _simulate_bonus_game_batch(
            model=model,
            evaluator=evaluator,
            batch_size=current_batch_size,
            rng=rng,
            initial_free_spins=initial_free_spins,
            retrigger_free_spins=retrigger_free_spins,
            min_scatter_count=min_scatter_count,
        )

        payout_parts.append(
            batch_result.payout_multipliers
        )
        free_spin_parts.append(
            batch_result.free_spin_counts
        )
        respin_parts.append(
            batch_result.respin_counts
        )
        retrigger_parts.append(
            batch_result.retrigger_counts
        )
        winning_parts.append(
            batch_result.winning_free_spin_counts
        )

        completed_games += current_batch_size

    return BonusGameSimulationResult(
        payout_multipliers=np.concatenate(
            payout_parts
        ),
        free_spin_counts=np.concatenate(
            free_spin_parts
        ),
        respin_counts=np.concatenate(
            respin_parts
        ),
        retrigger_counts=np.concatenate(
            retrigger_parts
        ),
        winning_free_spin_counts=np.concatenate(
            winning_parts
        )
    )