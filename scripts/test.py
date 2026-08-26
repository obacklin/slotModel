import numpy as np
from pathlib import Path

from slotmodel.runtime_tools import get_payline_evaluator_profile
from slotmodel.sim.analytics import sim_report
from slotmodel.sim.reels import read_reels
from slotmodel.sim.screens import ScreenModel


cand_path = (
    Path(__file__).parents[1]
    / "config"
    / "reels"
    / "candidates"
    / "low_vol_copy.json"
)
reels = read_reels(cand_path)
window = np.asarray([0, 1, 2], dtype=np.int32)

sm = ScreenModel.from_reels(reels=reels, window_offsets=window)
base_spins = 1_000_000
bonus_spins = 1_000_000

PAYLINE_EVALUATOR = "low_vol"
evaluator = get_payline_evaluator_profile(PAYLINE_EVALUATOR).build()

report = sim_report(sm, base_spins, bonus_spins, evaluator=evaluator)
print(report)