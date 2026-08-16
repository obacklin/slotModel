import numpy as np
from time import perf_counter

from slotmodel.sim.reels import read_reels
from slotmodel.sim.screens import ScreenModel

from slotmodel.sim.analytics import sim_report, ParameterReport
from slotmodel.optim.optimizer import OptimizerConfig, Optimizer

def rtp_fitness(
    reels: np.ndarray,
    seed: int,
) -> float:
    reel_set = tuple(
        reel.copy()
        for reel in reels
    )

    model = ScreenModel.from_reels(
        reels=reel_set,
        window_offsets=(0, 1, 2),
    )

    report = sim_report(
        model=model,
        total_spins=TOTAL_BASE_SPINS,
        total_bonus_games=TOTAL_BONUS_GAMES,
        seed=seed,
    )
    error = report.rtp_total - TARGET_RTP

    return -(error ** 2)

reels = read_reels()

model = ScreenModel.from_reels(
    reels=reels,
    window_offsets=(0, 1, 2),
)

TARGET_RTP = 0.96

TOTAL_BASE_SPINS = 250_000
TOTAL_BONUS_GAMES = 250_000

config = OptimizerConfig(
    reel_len=51,
    n_reels=5,
    population_size=10,
    crossover_rate=0.8,
    mutation_rate=0.03,
    tournament_size=3,
    elite_count=1,
    maximize=True,
    max_generation=10,
)


optim = Optimizer(config=config, fitness_fun=rtp_fitness, seed=42)
optim.populate()

print("Generation:", optim._generation)
print("Fitness:", optim.fitness())
print("Best fitness:", optim.best_fitness())

for _ in range(10):
    optim.step()

    print(
        f"Generation {optim._generation:>2} | "
        f"Best fitness: {optim.best_fitness():.8f}"
    )

# base_spins = 250_000
# bonus_games = 250_000
# rng_seed = 123
# tic = perf_counter()
# report = sim_report(model=model, total_spins=base_spins, total_bonus_games=bonus_games, seed=rng_seed)
# toc = perf_counter()
# print(report)
# print(f"Time elapsed: {toc-tic}s")

