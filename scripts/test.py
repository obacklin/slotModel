import numpy as np

from slotmodel.sim.reels import read_reels
from slotmodel.sim.screens import ScreenModel

from slotmodel.sim.analytics import sim_report

reels = read_reels()

model = ScreenModel.from_reels(
    reels=reels,
    window_offsets=(0, 1, 2),
)

rng = np.random.default_rng(42)

report = sim_report(
    model=model,
    batch_size=1_000_000,
    rng=rng
)

print(report.bonus_freq, report.rtp_base)