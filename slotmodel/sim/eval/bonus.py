from __future__ import annotations

from dataclasses import dataclass
from typing import TypeAlias

import numpy as np
from numpy.typing import NDArray

from slotmodel.sim.eval.payline_eval import(
    PaylineEvaluator,
    PaylineEvaluation
)
from slotmodel.sim.eval.scatter import (
    ScatterCountBatch,
    TriggerMask,
    count_scatter_symbols
)
from slotmodel.sim.reels import Symbol
from slotmodel.sim.screens import ScreenBatchArray

LockMaskBatch: TypeAlias = NDArray[np.bool_]

@dataclass(frozen=True, slots=True)
class BonusStepEvaluation:
    """Evaluate one screen in sticky respin."""
    payline_evaluation: PaylineEvaluation
    scatter_counts: ScatterCountBatch
    retrigger_mask: TriggerMask
    winning_pos_mask: LockMaskBatch
    new_lock_mask: LockMaskBatch

    def __post__init__(self) -> None:
        screen_shape = self.winning_pos_mask.shape

        if self.winning_pos_mask.ndim != 3:
            raise ValueError(
                "winning_pos_mask must be 3-dim"
            )
        if self.new_lock_mask.shape != screen_shape:
            raise ValueError(
                "new_lock_mask must match winning_pos_mask in shape."
            )

        batch_size = screen_shape[0]

        if self.retrigger_mask.shape != (batch_size, ):
            raise ValueError(
                "retrigger_mask must contain one value per screen."
            )
        if self.payline_evaluation.winning_symbols.shape[0] != batch_size:
            raise ValueError(
                "The payline evaluation batch size must match the masks."
            )

    @property
    def cont_mask(self) -> TriggerMask:
        """Return screens that gained one new sticky pos."""

        return np.any(self.new_lock_mask, axis=(1,2))

def winning_pos_mask(
        evaluation: PaylineEvaluation,
        evaluator: PaylineEvaluator,
        row_count: int,
) -> LockMaskBatch:
    """Map paying prefixes back to physical screen positions."""

    if row_count <= 0:
        raise ValueError("row_count must be positive.")

    if evaluation.match_counts.shape[1] != evaluator.line_count:
        raise ValueError(
            "The evaluation line count does not match the evaluator."
        )

    if int(np.max(evaluator.payline_rows)) >= row_count:
        raise ValueError(
            "A payline row index is outside supplied row count."
        )

    batch_size = evaluation.match_counts.shape[0]

    result = np.zeros(
        (
            batch_size,
            row_count,
            evaluator.reel_count,
        ),
        dtype=np.bool_,
    )

    for row_index, reel_index, line_indices in (
        evaluator.payline_position_groups
    ):
        result[:, row_index, reel_index] = np.any(
            evaluation.match_counts[:, line_indices] > reel_index,
            axis=1,
        )

    return result

def evaluate_bonus_step(
        screens: ScreenBatchArray,
        locked_mask: LockMaskBatch,
        evaluator: PaylineEvaluator,
        min_scatter_count: int = 3
) -> BonusStepEvaluation:

    if screens.ndim != 3:
        raise ValueError(
            "screens must have shape "
            "(batch_size, row_count, reel_count)."
        )
    if locked_mask.shape != screens.shape:
        raise ValueError(
            "locked_mask must have the same shape as as screens."
        )
    if locked_mask.dtype != np.bool_:
        raise TypeError("locked_mask must have dtype np.bool_")
    if min_scatter_count <= 0:
        raise ValueError(
            "min_scatter_count must be positive."
        )

    payline_evaluation = evaluator.evaluate(screens)

    win_mask = winning_pos_mask(
        evaluation=payline_evaluation,
        evaluator=evaluator,
        row_count=screens.shape[1]
    )

    win_mask &= screens != int(Symbol.SCATTER)
    new_lock_mask = win_mask & ~locked_mask

    scatter_counts = count_scatter_symbols(screens)
    retrigger_mask = scatter_counts >= min_scatter_count

    return BonusStepEvaluation(
        payline_evaluation=payline_evaluation,
        scatter_counts=scatter_counts,
        retrigger_mask=retrigger_mask,
        winning_pos_mask=win_mask,
        new_lock_mask=new_lock_mask
    )

def overlay_locked_symbols(
        current_screens: ScreenBatchArray,
        replacement_screens: ScreenBatchArray,
        locked_mask: LockMaskBatch,
) -> ScreenBatchArray:
    """Return replacement screens with sticky pos overlaid. """

    if current_screens.shape != replacement_screens.shape:
        raise ValueError(
            "current_screens and replacement_screens "
            "must match in shape."
        )
    if locked_mask.shape != current_screens.shape:
        raise ValueError(
            "locked_mask must have the same shape as the screens."
        )
    if locked_mask.dtype != np.bool_:
        raise TypeError("locked_mask must have dtype np.bool_")

    result = replacement_screens.copy()
    np.copyto(
        result,
        current_screens,
        where=locked_mask
    )

    return result
