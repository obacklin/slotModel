from __future__ import annotations

import random
from collections.abc import Sequence
from dataclasses import dataclass

from game_config import GameConfig, Symbol


Screen = tuple[tuple[Symbol, ...], ...]


@dataclass(frozen=True, slots=True)
class SpinResult:
    """The stops and visible screen produced by one spin."""

    stops: tuple[int, ...]
    screen: Screen


def validate_stops(
    config: GameConfig,
    stops: Sequence[int],
) -> tuple[int, ...]:
    """Validate stops and return them as an immutable tuple."""

    if len(stops) != config.n_reels:
        raise ValueError(
            f"Expected {config.n_reels} stops, received {len(stops)}"
        )

    validated: list[int] = []

    for reel_index, (stop, reel_length) in enumerate(
        zip(stops, config.reel_lengths)
    ):
        # bool is a subclass of int, so reject it explicitly.
        if isinstance(stop, bool) or not isinstance(stop, int):
            raise TypeError(
                f"Stop for reel {reel_index + 1} must be an integer"
            )

        if not 0 <= stop < reel_length:
            raise ValueError(
                f"Stop {stop} is invalid for reel {reel_index + 1}; "
                f"expected 0 to {reel_length - 1}"
            )

        validated.append(stop)

    return tuple(validated)


def build_screen(
    config: GameConfig,
    stops: Sequence[int],
) -> Screen:
    """Build a row-major visible screen from explicit reel stops.

    Convention:
        A stop identifies the top visible symbol on its reel.

    Formula:
        screen[row][reel]
            = reels[reel][(stop[reel] + row) % reel_length]
    """

    valid_stops = validate_stops(config, stops)

    return tuple(
        tuple(
            config.reels[reel_index][
                (valid_stops[reel_index] + row_index)
                % config.reel_lengths[reel_index]
            ]
            for reel_index in range(config.n_reels)
        )
        for row_index in range(config.visible_rows)
    )


def sample_stops(
    config: GameConfig,
    rng: random.Random,
) -> tuple[int, ...]:
    """Sample one independent, uniformly distributed stop per reel."""

    return tuple(
        rng.randrange(reel_length)
        for reel_length in config.reel_lengths
    )


def spin(
    config: GameConfig,
    rng: random.Random,
) -> SpinResult:
    """Generate stops and construct their visible screen."""

    stops = sample_stops(config, rng)
    return SpinResult(
        stops=stops,
        screen=build_screen(config, stops),
    )
