from __future__ import annotations

from dataclasses import dataclass
from numbers import Real
from typing import TypeAlias

import numpy as np
from numpy.typing import NDArray

from slotmodel.sim.reels import Symbol


PayoutMultipliers: TypeAlias = tuple[float, ...]
PaytableMatrix: TypeAlias = NDArray[np.float64]


@dataclass(frozen=True, slots=True)
class PaytableEntry:
    """
    Multipliers for one payable symbol.

    The first multiplier belongs to ``minimum_match_count`` and each
    following value belongs to the next larger connected match count.
    """

    symbol: Symbol
    multipliers: PayoutMultipliers

    def __post_init__(self) -> None:
        if self.symbol is Symbol.SCATTER:
            raise ValueError(
                "SCATTER cannot have a left-to-right payline entry."
            )

        if not self.multipliers:
            raise ValueError(
                f"Paytable entry for {self.symbol.name} cannot be empty."
            )

        for multiplier in self.multipliers:
            if (
                not isinstance(multiplier, Real)
                or isinstance(multiplier, bool)
            ):
                raise TypeError(
                    "Paytable multipliers must be real numbers."
                )

            if multiplier <= 0.0:
                raise ValueError(
                    "Paytable multipliers must be positive."
                )

            if not np.isfinite(multiplier):
                raise ValueError(
                    "Paytable multiplier must be finite."
                )


@dataclass(frozen=True, slots=True)
class Paytable:
    """Validated left-to-right payline paytable definition."""

    reel_count: int
    minimum_match_count: int
    entries: tuple[PaytableEntry, ...]

    def __post_init__(self) -> None:
        if self.reel_count <= 0:
            raise ValueError("reel_count must be positive.")

        if self.minimum_match_count <= 0:
            raise ValueError(
                "minimum_match_count must be positive."
            )

        if self.minimum_match_count > self.reel_count:
            raise ValueError(
                "minimum_match_count cannot exceed reel_count."
            )

        if not self.entries:
            raise ValueError(
                "At least one paytable entry is required."
            )

        expected_multiplier_count = (
            self.reel_count - self.minimum_match_count + 1
        )
        seen_symbols: set[Symbol] = set()

        for entry in self.entries:
            if entry.symbol in seen_symbols:
                raise ValueError(
                    f"Duplicate paytable entry for {entry.symbol.name}."
                )

            if len(entry.multipliers) != expected_multiplier_count:
                raise ValueError(
                    f"Paytable entry for {entry.symbol.name} has "
                    f"{len(entry.multipliers)} multipliers; expected "
                    f"{expected_multiplier_count}."
                )

            seen_symbols.add(entry.symbol)


def compile_paytable(paytable: Paytable) -> PaytableMatrix:
    """
    Compile a paytable into a direct symbol/count lookup matrix.

    The returned matrix has shape ``(symbol_count, reel_count + 1)``.
    ``matrix[symbol_id, match_count]`` is the corresponding bet
    multiplier. Counts or symbols without a defined win contain zero.
    """

    symbol_count = max(int(symbol) for symbol in Symbol) + 1
    matrix = np.zeros(
        (symbol_count, paytable.reel_count + 1),
        dtype=np.float64,
    )

    first_count = paytable.minimum_match_count

    for entry in paytable.entries:
        last_count = first_count + len(entry.multipliers)
        matrix[
            int(entry.symbol),
            first_count:last_count,
        ] = entry.multipliers

    matrix.flags.writeable = False
    return matrix
