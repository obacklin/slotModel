from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from typing import Any, TypeAlias

import numpy as np
from numpy.typing import NDArray

from slotmodel.sim import Symbol
from slotmodel.sim.reels import generate_reel_population

FitnessArray: TypeAlias = NDArray[np.float64] 
ReelPopulation: TypeAlias = NDArray[np.int16]
ReelMatrix: TypeAlias = NDArray[np.int16]


@dataclass(frozen=True, slots=True)
class FitnessEvaluation:
    """Fitness value plus optional caller-owned evaluation metadata."""

    value: float
    payload: Any = None


@dataclass(frozen=True, slots=True)
class OptimizerConfig:
    reel_len: int
    n_reels: int

    population_size: int = 10
    crossover_rate: float = 0.8
    mutation_rate: float = 0.03
    tournament_size: int = 3
    elite_count: int = 1
    maximize: bool = True
    max_generation: int = 100
    max_workers: int = 1
    initial_candidate_concentration: float | None = 30.0
    initial_reel_concentration: float | None = 90.0

class Optimizer:
    """Genetic optimization of reel symbols.
    Population has shape:
        (population_size, reel_count, reel_length)
    """
    def __init__(
            self,
            config: OptimizerConfig,
            fitness_fun = None,
            seed: int | None = None,
    ) -> None:
        self.reel_len = config.reel_len
        self.n_reels = config.n_reels
        self.config = config
        self._fitness_fun = fitness_fun
        self._population: ReelPopulation | None = None
        self._fitness : FitnessArray | None  = None
        self._evaluation_payloads: tuple[Any, ...] | None = None
        self._generation = 0
        self._rng = np.random.default_rng(seed)

        if self.config.reel_len <= 0:
            raise ValueError("reel_len must be positive.")
        if self.config.n_reels <= 0:
            raise ValueError("n_reels must be positive.")
        if self.config.population_size <= 0:
            raise ValueError("population_size must be positive.")
        if not 0.0 <= self.config.crossover_rate <= 1.0:
            raise ValueError("crossover_rate must be between 0 and 1.")
        if not 0.0 <= self.config.mutation_rate <= 1.0:
            raise ValueError("mutation_rate must be between 0 and 1.")
        if not 1 <= self.config.tournament_size <= self.config.population_size:
            raise ValueError(
                "tournament_size must be between 1 and population_size."
            )
        if not 0 <= self.config.elite_count <= self.config.population_size:
            raise ValueError(
                "elite_count must be between 0 and population_size."
            )
        if self.config.max_generation <= 0:
            raise ValueError("max_generation must be positive.")
        if self.config.max_workers <= 0:
            raise ValueError("max_workers must be positive.")

        self._probs = {
            Symbol.SCATTER: 0.05,
            Symbol.WILD: 0.05,
            Symbol.JEWEL: 0.05,
            Symbol.CASTLE: 0.08,
            Symbol.CHEST: 0.08,
            Symbol.COIN: 0.09,
            Symbol.KNIGHT: 0.09,
            Symbol.A : 0.1,
            Symbol.K : 0.1,
            Symbol.Q : 0.1,
            Symbol.J : 0.1,
            Symbol.PAWN: 0.1,
        }
        self._symbols = np.asarray(
            [int(symbol) for symbol in self._probs],
            dtype=np.int16,
        )

        self._weights = np.asarray(
            list(self._probs.values()),
            dtype=np.float64,
        )

        self._weights /= self._weights.sum()

        self._required_symbols = np.asarray(
            [int(symbol) for symbol in Symbol],
            dtype=np.int16,
        )

    def populate(self) -> None:
        population_seed = int(
            self._rng.integers(
                0,
                np.iinfo(np.uint32).max,
                dtype=np.uint32,
            )
        )

        self._population = generate_reel_population(
            probabilities=self._probs, 
            population_size=self.config.population_size, 
            number_of_reels=self.n_reels,
            reel_length=self.reel_len,
            seed=population_seed,
            candidate_concentration=(
                self.config.initial_candidate_concentration
            ),
            reel_concentration=self.config.initial_reel_concentration,
        )

    def step(self) -> None:
        """Process one complete generation."""

        population = self._require_population()

        if self._generation >= self.config.max_generation:
            raise RuntimeError(
                "Maximum number of generations has been reached."
            )

        fitness = self.fitness()

        elites = self._select_elites(
            population,
            fitness,
        )

        n_offspring = (
            self.config.population_size
            - self.config.elite_count
        )

        offspring = self._make_offspring(
            population,
            fitness,
            n_offspring,
        )

        next_population = np.concatenate(
            (elites, offspring),
            axis=0,
        )

        self._repair_population(
            next_population
        )

        self._population = next_population
        self._fitness = None
        self._evaluation_payloads = None

        self._generation += 1

        self._evaluate_population()

    def fitness(self) -> FitnessArray:
        """Return fitness values for the current generation."""

        self._require_population()

        if self._fitness is None:
            self._evaluate_population()

        assert self._fitness is not None

        return self._fitness

    def evaluation_payloads(self) -> tuple[Any, ...]:
        """Return metadata produced alongside current-generation fitness."""

        self.fitness()

        assert self._evaluation_payloads is not None
        return self._evaluation_payloads

    def best_index(self) -> int:
        fitness = self.fitness()

        if self.config.maximize:
            return int(np.argmax(fitness))

        return int(np.argmin(fitness))

    def best_fitness(self) -> float:
        return float(
            self.fitness()[self.best_index()]
        )

    def best_reels(self) -> ReelMatrix:
        population = self._require_population()

        return population[
            self.best_index()
        ].copy()

    def _evaluate_population(self) -> None:
        population = self._require_population()

        if self._fitness_fun is None:
            raise RuntimeError(
                "No fitness function has been supplied."
            )

        fitness = np.empty(
            self.config.population_size,
            dtype=np.float64,
        )

        # Same Monte Carlo seed for all candidates in this generation.
        evaluation_seed = int(
            self._rng.integers(
                0,
                np.iinfo(np.uint32).max,
                dtype=np.uint32,
            )
        )

        def evaluate(candidate: ReelMatrix) -> object:
            return self._fitness_fun(
                candidate,
                evaluation_seed,
            )

        if self.config.max_workers == 1:
            raw_results = [
                evaluate(candidate)
                for candidate in population
            ]
        else:
            with ThreadPoolExecutor(
                max_workers=self.config.max_workers
            ) as executor:
                # executor.map preserves input order even when workers finish
                # out of order, keeping GA results deterministic.
                raw_results = list(
                    executor.map(evaluate, population)
                )

        payloads: list[Any] = []

        for i, result in enumerate(raw_results):
            if isinstance(result, FitnessEvaluation):
                value = float(result.value)
                payload = result.payload
            else:
                value = float(result)
                payload = None

            if not np.isfinite(value):
                raise ValueError(
                    f"Fitness for candidate {i} is not finite."
                )

            fitness[i] = value
            payloads.append(payload)

        self._fitness = fitness
        self._evaluation_payloads = tuple(payloads)

    def _select_elites(
        self,
        population: ReelPopulation,
        fitness: FitnessArray,
    ) -> ReelPopulation:
        """Copy the best individuals directly into the next generation."""

        n_elites = self.config.elite_count

        if n_elites == 0:
            return np.empty(
                (
                    0,
                    self.n_reels,
                    self.reel_len,
                ),
                dtype=np.int16,
            )

        if self.config.maximize:
            indices = np.argsort(fitness)[-n_elites:]
        else:
            indices = np.argsort(fitness)[:n_elites]

        return population[indices].copy()

    def _tournament_index(
        self,
        fitness: FitnessArray,
    ) -> int:
        """Select one parent using tournament selection."""

        competitors = self._rng.choice(
            self.config.population_size,
            size=self.config.tournament_size,
            replace=False,
        )

        competitor_fitness = fitness[
            competitors
        ]

        if self.config.maximize:
            winner = np.argmax(
                competitor_fitness
            )
        else:
            winner = np.argmin(
                competitor_fitness
            )

        return int(
            competitors[winner]
        )

    def _make_offspring(
        self,
        population: ReelPopulation,
        fitness: FitnessArray,
        n_offspring: int,
    ) -> ReelPopulation:
        offspring = np.empty(
            (
                n_offspring,
                self.n_reels,
                self.reel_len,
            ),
            dtype=np.int16,
        )

        child_index = 0

        while child_index < n_offspring:
            parent_a = population[
                self._tournament_index(fitness)
            ]

            parent_b = population[
                self._tournament_index(fitness)
            ]

            child_a, child_b = self._crossover(
                parent_a,
                parent_b,
            )

            self._mutate(child_a)
            self._mutate(child_b)

            offspring[child_index] = child_a
            child_index += 1

            if child_index < n_offspring:
                offspring[child_index] = child_b
                child_index += 1

        return offspring

    def _crossover(
        self,
        parent_a: ReelMatrix,
        parent_b: ReelMatrix,
    ) -> tuple[ReelMatrix, ReelMatrix]:
        """Perform one-point crossover independently on each reel."""

        child_a = parent_a.copy()
        child_b = parent_b.copy()

        if self._rng.random() >= self.config.crossover_rate:
            return child_a, child_b

        for reel_index in range(self.n_reels):
            crossover_point = int(
                self._rng.integers(
                    1,
                    self.reel_len,
                )
            )

            child_a[
                reel_index,
                crossover_point:
            ] = parent_b[
                reel_index,
                crossover_point:
            ]

            child_b[
                reel_index,
                crossover_point:
            ] = parent_a[
                reel_index,
                crossover_point:
            ]

        return child_a, child_b

    def _mutate(
        self,
        candidate: ReelMatrix,
    ) -> None:
        """Replace reel positions independently with mutation_rate."""

        mutation_mask = (
            self._rng.random(candidate.shape)
            < self.config.mutation_rate
        )

        n_mutations = int(
            np.count_nonzero(
                mutation_mask
            )
        )

        if n_mutations == 0:
            return

        candidate[mutation_mask] = self._rng.choice(
            self._symbols,
            size=n_mutations,
            p=self._weights,
        )

    def _repair_population(
        self,
        population: ReelPopulation,
    ) -> None:
        """Ensure every required symbol remains present on every reel."""

        for candidate in population:
            for reel in candidate:
                self._repair_reel(reel)

    def _repair_reel(
        self,
        reel: NDArray[np.int16],
    ) -> None:
        for required_symbol in self._required_symbols:
            if np.any(reel == required_symbol):
                continue

            replacement_positions = []

            for position, symbol in enumerate(reel):
                # We may safely overwrite a symbol if it occurs
                # more than once on this reel.
                if np.count_nonzero(reel == symbol) > 1:
                    replacement_positions.append(
                        position
                    )

            if not replacement_positions:
                raise RuntimeError(
                    "Unable to repair reel."
                )

            position = int(
                self._rng.choice(
                    replacement_positions
                )
            )

            reel[position] = required_symbol

    def _require_population(
        self,
    ) -> ReelPopulation:
        if self._population is None:
            raise RuntimeError(
                "Call populate() before using the optimizer."
            )

        return self._population
