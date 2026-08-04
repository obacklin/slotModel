from __future__ import annotations

from typing import TypeAlias

import numpy as np
from numpy.typing import NDArray

from slotmodel.sim.reels import Symbol
from slotmodel.sim.screens import ScreenBatchArray


ScatterCountBatch: TypeAlias = NDArray[np.int16]
TriggerMask: TypeAlias = NDArray[np.bool_]


def count_scatter_symbols(
    screens: ScreenBatchArray,
) -> ScatterCountBatch:
    """Count visible scatter symbols in each screen.

    ``screens`` must use the repository layout ``(spin, row, reel)``.
    The returned array has shape ``(batch_size,)``.
    """

    if screens.ndim != 3:
        raise ValueError(
            "screens must have shape (batch_size, row_count, reel_count)."
        )

    counts = np.count_nonzero(
        screens == int(Symbol.SCATTER),
        axis=(1, 2),
    )

    return counts.astype(np.int16, copy=False)


def scatter_bonus_trigger_mask(
    screens: ScreenBatchArray,
    min_scatter_count: int = 3,
) -> TriggerMask:
    """Return one boolean bonus-trigger result per screen."""

    if min_scatter_count <= 0:
        raise ValueError("minimum_scatter_count must be positive.")

    return count_scatter_symbols(screens) >= min_scatter_count
