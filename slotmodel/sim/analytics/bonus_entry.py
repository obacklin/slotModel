from __future__ import annotations

from dataclasses import dataclass
import math

import numpy as np

from slotmodel.sim.eval import scatter_bonus_trigger_mask
from slotmodel.sim.screens import ScreenModel, iter_spin_batches


@dataclass(frozen=True, slots=True)
class BonusEntrySimulationResult:
    total_spins: int
    bonus_entries: int

    @property
    def estimated_probability(self) -> float:
        if self.total_spins == 0:
            return 0.0
        return self.bonus_entries / self.total_spins

    @property
    def standard_error(self) -> float:
        if self.total_spins == 0:
            return 0.0

        probability = self.estimated_probability
        return math.sqrt(
            probability * (1.0 - probability) / self.total_spins
        )


def simulate_bonus_entry_probability(
    model: ScreenModel,
    total_spins: int,
    batch_size: int,
    rng: np.random.Generator,
    minimum_scatter_count: int = 3,
) -> BonusEntrySimulationResult:
    """Estimate the probability that a screen contains enough scatters."""

    if total_spins <= 0:
        raise ValueError("total_spins must be positive.")

    if batch_size <= 0:
        raise ValueError("batch_size must be positive.")

    if minimum_scatter_count <= 0:
        raise ValueError("minimum_scatter_count must be positive.")

    bonus_entries = 0

    for batch in iter_spin_batches(
        model=model,
        total_spins=total_spins,
        batch_size=batch_size,
        rng=rng,
    ):
        trigger_mask = scatter_bonus_trigger_mask(
            screens=batch.screens,
            min_scatter_count=minimum_scatter_count,
        )
        bonus_entries += int(np.count_nonzero(trigger_mask))

    return BonusEntrySimulationResult(
        total_spins=total_spins,
        bonus_entries=bonus_entries,
    )
