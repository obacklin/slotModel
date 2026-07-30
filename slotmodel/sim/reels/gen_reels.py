from __future__ import annotations

import json
from pathlib import Path

import numpy as np

from slotmodel.paths import REELS_CONFIG_PATH
from slotmodel.sim.reels.reel_def import Reel
from slotmodel.sim.reels.symbols import Symbol

NUMBER_OF_REELS = 5
REEL_LENGTH = 51


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