from __future__ import annotations

import unittest

import numpy as np

from slotmodel.sim import Symbol
from slotmodel.sim.reels import generate_reel_population


PROBABILITIES = {
    Symbol.SCATTER: 0.01,
    Symbol.WILD: 0.01,
    Symbol.JEWEL: 0.02,
    Symbol.CASTLE: 0.03,
    Symbol.CHEST: 0.03,
    Symbol.COIN: 0.04,
    Symbol.KNIGHT: 0.04,
    Symbol.A: 0.05,
    Symbol.K: 0.06,
    Symbol.Q: 0.07,
    Symbol.J: 0.08,
    Symbol.PAWN: 0.10,
}


class DiversePopulationTests(unittest.TestCase):
    def test_dirichlet_initialization_is_seed_reproducible(self) -> None:
        kwargs = dict(
            probabilities=PROBABILITIES,
            population_size=12,
            number_of_reels=5,
            reel_length=51,
            candidate_concentration=24.0,
            reel_concentration=70.0,
            seed=123,
        )
        first = generate_reel_population(**kwargs)
        second = generate_reel_population(**kwargs)
        np.testing.assert_array_equal(first, second)

    def test_every_generated_reel_still_contains_every_required_symbol(self) -> None:
        population = generate_reel_population(
            probabilities=PROBABILITIES,
            population_size=8,
            number_of_reels=5,
            reel_length=51,
            candidate_concentration=24.0,
            reel_concentration=70.0,
            seed=456,
        )
        required = {int(symbol) for symbol in Symbol}

        for candidate in population:
            for reel in candidate:
                self.assertTrue(required.issubset(set(map(int, reel))))

    def test_dirichlet_jitter_increases_symbol_count_variety(self) -> None:
        fixed = generate_reel_population(
            probabilities=PROBABILITIES,
            population_size=36,
            number_of_reels=5,
            reel_length=51,
            seed=789,
        )
        diverse = generate_reel_population(
            probabilities=PROBABILITIES,
            population_size=36,
            number_of_reels=5,
            reel_length=51,
            candidate_concentration=24.0,
            reel_concentration=70.0,
            seed=789,
        )

        def mean_count_std(population: np.ndarray) -> float:
            counts = np.asarray([
                [np.count_nonzero(candidate == int(symbol)) for symbol in Symbol]
                for candidate in population
            ])
            return float(np.mean(np.std(counts, axis=0)))

        self.assertGreater(mean_count_std(diverse), mean_count_std(fixed) * 1.5)


if __name__ == "__main__":
    unittest.main()
