from __future__ import annotations

import json
from pathlib import Path

import numpy as np

from slotmodel.paths import REELS_CONFIG_PATH
from slotmodel.sim.reels.reel_def import Reel
from slotmodel.sim.reels.symbols import Symbol

NUMBER_OF_REELS = 5
REEL_LENGTH = 51


def generate_reel_population(
    probabilities: dict[Symbol, float],
    population_size: int,
    number_of_reels: int,
    reel_length: int,
    required_symbols: tuple[Symbol, ...] = tuple(Symbol),
    seed: int | None = None,
    candidate_concentration: float | None = None,
    reel_concentration: float | None = None,
) -> np.ndarray:
    """Generate an in-memory population of valid reel matrices.

    The returned array has shape::

        (population_size, number_of_reels, reel_length)

    By default every candidate uses the same normalized ``probabilities``.
    Setting ``candidate_concentration`` enables Dirichlet jitter around those
    base weights, so each candidate starts with a meaningfully different
    symbol-frequency profile.  ``reel_concentration`` optionally adds a
    second level of jitter between physical reels inside one candidate.

    Larger concentration values stay closer to the parent distribution;
    smaller values create more variety.  A value around 20-40 is deliberately
    broad for a 12-symbol, 51-stop reel set.
    """

    if population_size <= 0:
        raise ValueError("population_size must be positive.")
    if number_of_reels <= 0:
        raise ValueError("number_of_reels must be positive.")
    if reel_length <= 0:
        raise ValueError("reel_length must be positive.")
    if not probabilities:
        raise ValueError("At least one symbol probability is required.")

    symbols = tuple(probabilities.keys())
    symbol_ids = np.asarray(
        [int(symbol) for symbol in symbols],
        dtype=np.int16,
    )
    weights = np.asarray(
        [probabilities[symbol] for symbol in symbols],
        dtype=np.float64,
    )

    if np.any(~np.isfinite(weights)):
        raise ValueError("Probabilities must be finite numbers.")
    if np.any(weights < 0):
        raise ValueError("Probabilities cannot be negative.")
    if weights.sum() <= 0:
        raise ValueError("At least one probability must be positive.")

    for name, concentration in (
        ("candidate_concentration", candidate_concentration),
        ("reel_concentration", reel_concentration),
    ):
        if concentration is not None and (
            not np.isfinite(concentration) or concentration <= 0.0
        ):
            raise ValueError(f"{name} must be a positive finite number.")

    required = tuple(dict.fromkeys(required_symbols))
    if len(required) > reel_length:
        raise ValueError(
            "reel_length must be at least the number of required symbols."
        )

    required_ids = np.asarray(
        [int(symbol) for symbol in required],
        dtype=np.int16,
    )

    weights /= weights.sum()
    rng = np.random.default_rng(seed)

    population = np.empty(
        (population_size, number_of_reels, reel_length),
        dtype=np.int16,
    )
    free_stop_count = reel_length - required_ids.size

    # Dirichlet requires strictly positive alpha values.  Zero-weight symbols
    # remain possible only through required_symbols; the tiny floor merely
    # keeps the distribution numerically valid when jitter is enabled.
    alpha_floor = 1e-6

    for candidate_index in range(population_size):
        if candidate_concentration is None:
            candidate_weights = weights
        else:
            candidate_alpha = np.maximum(
                weights * candidate_concentration,
                alpha_floor,
            )
            candidate_weights = rng.dirichlet(candidate_alpha)

        for reel_index in range(number_of_reels):
            if reel_concentration is None:
                reel_weights = candidate_weights
            else:
                reel_alpha = np.maximum(
                    candidate_weights * reel_concentration,
                    alpha_floor,
                )
                reel_weights = rng.dirichlet(reel_alpha)

            reel = population[candidate_index, reel_index]

            if required_ids.size:
                reel[:required_ids.size] = required_ids

            if free_stop_count:
                reel[required_ids.size:] = rng.choice(
                    symbol_ids,
                    size=free_stop_count,
                    replace=True,
                    p=reel_weights,
                )

            rng.shuffle(reel)

    return population


def generate_weighted_reels(
    probabilities: dict[Symbol, float],
    number_of_reels: int = NUMBER_OF_REELS,
    reel_length: int = REEL_LENGTH,
    seed: int | None = None,
) -> tuple[Reel, ...]:
    if number_of_reels <= 0:
        raise ValueError("number_of_reels must be positive.")

    if reel_length <= 0:
        raise ValueError("reel_length must be positive.")

    if not probabilities:
        raise ValueError("At least one symbol probability is required.")

    symbols = tuple(probabilities.keys())

    symbol_ids = np.asarray(
        [int(symbol) for symbol in symbols],
        dtype=np.int16,
    )

    weights = np.asarray(
        [probabilities[symbol] for symbol in symbols],
        dtype=np.float64,
    )

    if np.any(~np.isfinite(weights)):
        raise ValueError("Probabilities must be finite numbers.")

    if np.any(weights < 0):
        raise ValueError("Probabilities cannot be negative.")

    if weights.sum() <= 0:
        raise ValueError("At least one probability must be positive.")

    weights /= weights.sum()

    rng = np.random.default_rng(seed)

    return tuple(
        rng.choice(
            symbol_ids,
            size=reel_length,
            replace=True,
            p=weights,
        ).astype(np.int16)
        for _ in range(number_of_reels)
    )


def save_reels(
    reels: tuple[Reel, ...],
    output_path: Path = REELS_CONFIG_PATH,
) -> None:
    if not reels:
        raise ValueError("At least one reel is required.")

    reel_length = len(reels[0])

    if reel_length == 0:
        raise ValueError("Reels cannot be empty.")

    if any(len(reel) != reel_length for reel in reels):
        raise ValueError("All reels must have the same length.")

    serialized_reels = [
        [Symbol(int(symbol_id)).name for symbol_id in reel]
        for reel in reels
    ]

    data = {
        "format_version": 1,
        "number_of_reels": len(reels),
        "reel_length": reel_length,
        "reels": serialized_reels,
    }

    output_path.parent.mkdir(parents=True, exist_ok=True)

    with output_path.open("w", encoding="utf-8") as file:
        json.dump(data, file, indent=2)
        file.write("\n")


def main() -> None:
    # Relative weights; they do not need to sum to 1.
    probabilities = {
        Symbol.WILD: 1,
        Symbol.SCATTER: 1,
        Symbol.A: 2,
        Symbol.K: 3,
        Symbol.Q: 4,
        Symbol.J: 5,
        Symbol.CASTLE: 7,
        Symbol.PAWN: 8,
        Symbol.KNIGHT: 6,
        Symbol.CHEST: 6,
        Symbol.COIN: 3,
        Symbol.JEWEL: 2,
    }

    reels = generate_weighted_reels(
        probabilities=probabilities,
        number_of_reels=NUMBER_OF_REELS,
        reel_length=REEL_LENGTH,
        seed=42,
    )

    save_reels(reels)

    print(
        f"Saved {len(reels)} reels of length "
        f"{len(reels[0])} to {REELS_CONFIG_PATH}"
    )


if __name__ == "__main__":
    main()