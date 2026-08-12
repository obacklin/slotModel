from __future__ import annotations
from dataclasses import dataclass

import numpy as np

from slotmodel.sim.eval import (
    PaylineEvaluator,
    scatter_bonus_trigger_mask,
)
from slotmodel.sim.paylines import PAYLINES
from slotmodel.sim.paytable import PAYTABLE
from slotmodel.sim.screens import ScreenModel, spin_batch
from slotmodel.sim.analytics import simulate_bonus_games

@dataclass(frozen=True, slots=True)
class ParameterReport:
    rtp_base: float
    rtp_bonus: float
    bonus_freq: float
    std: float


def sim_report(
        model: ScreenModel,
        batch_size: int,
        rng: np.random.Generator,
        min_scatter = 3
) -> ParameterReport:
    """
    Performs total_spins simulations and accumulates stats for reporting.
    
    Input:
        model: ScreenModel,
        batch_size: int - number of spin simulations to perform,
        rng: np.random.Generator
    Output:
        ParameterReport
    """
    if batch_size < 0:
        raise ValueError("total_spins must be > 0")

    batch = spin_batch(
        model=model,
        batch_size=batch_size,
        rng=rng
    )

    bonus_freq = estimate_bonus_freq(batch, min_scatter)
    evaluator = PaylineEvaluator.from_definitions(
        paylines=PAYLINES,
        paytable=PAYTABLE
    )
    evaluation = evaluator.evaluate(batch.screens)
    multipliers = evaluation.total_multiplier_per_spin
    


    rtp_base = float(np.mean(multipliers))
    # sample variance
    std = float(np.std(multipliers, ddof=1))


    return ParameterReport(
        rtp_base=rtp_base, 
        rtp_bonus=0, 
        bonus_freq=bonus_freq, 
        std=std
    )

def estimate_bonus_freq(batch, min_scatter):

    trigger_mask = scatter_bonus_trigger_mask(
        screens=batch.screens,
        min_scatter_count=min_scatter
    )

    freq = np.count_nonzero(trigger_mask)/batch.size

    return freq



