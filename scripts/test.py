import numpy as np

from slotmodel.sim.reels import read_reels
from slotmodel.sim.screens import ScreenModel

from slotmodel.sim.analytics import sim_report, ParameterReport

reels = read_reels()

model = ScreenModel.from_reels(
    reels=reels,
    window_offsets=(0, 1, 2),
)


base_spins = 1_000_000
bonus_games = 1_000_000
rng_seed = 123

report = sim_report(model=model, total_spins=base_spins, total_bonus_games=bonus_games, seed=rng_seed)
print(report)