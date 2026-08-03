from __future__ import annotations

import argparse

import numpy as np

from slotmodel.sim.reels import read_reels
from slotmodel.sim.screens import ScreenModel
from slotmodel.sim.analytics import simulate_bonus_entry_probability


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Estimate the probability that a base-game screen contains "
            "enough scatter symbols to trigger the bonus game."
        )
    )
    parser.add_argument(
        "--spins",
        type=int,
        default=1_000_000,
        help="Total number of base-game spins to simulate.",
    )
    parser.add_argument(
        "--batch-size",
        type=int,
        default=100_000,
        help="Number of screens generated and evaluated at once.",
    )
    parser.add_argument(
        "--seed",
        type=int,
        default=12345,
        help="NumPy random seed used for reproducibility.",
    )
    parser.add_argument(
        "--minimum-scatters",
        type=int,
        default=3,
        help="Minimum visible scatter count required for a bonus entry.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()

    reels = read_reels()
    model = ScreenModel.from_reels(
        reels=reels,
        window_offsets=(0, 1, 2),
    )

    result = simulate_bonus_entry_probability(
        model=model,
        total_spins=args.spins,
        batch_size=args.batch_size,
        rng=np.random.default_rng(args.seed),
        minimum_scatter_count=args.minimum_scatters,
    )

    probability = result.estimated_probability
    margin_95 = 1.96 * result.standard_error
    lower_95 = max(0.0, probability - margin_95)
    upper_95 = min(1.0, probability + margin_95)

    print(f"Spins: {result.total_spins:,}")
    print(f"Bonus entries: {result.bonus_entries:,}")
    print(f"Estimated probability: {probability:.8f}")
    print(f"Estimated percentage: {100.0 * probability:.5f}%")

    if result.bonus_entries > 0:
        print(f"Estimated frequency: 1 in {1.0 / probability:.2f} spins")

    print(
        "Approximate 95% interval: "
        f"[{lower_95:.8f}, {upper_95:.8f}]"
    )


if __name__ == "__main__":
    main()
