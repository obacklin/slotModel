from __future__ import annotations

from dataclasses import dataclass
from typing import TypeAlias

import numpy as np
from numpy.typing import NDArray

from slotmodel.sim.paylines.payline_def import (
    PaylineSet,
    compile_paylines,
)
from slotmodel.sim.paytable import (
    Paytable,
    PaytableMatrix,
    compile_paytable,
)
from slotmodel.sim.reels import Symbol
from slotmodel.sim.screens import ScreenBatchArray


CompiledPaylines: TypeAlias = NDArray[np.int8]
WinningSymbolBatch: TypeAlias = NDArray[np.int16]
MatchCountBatch: TypeAlias = NDArray[np.int16]
PayoutMultiplierBatch: TypeAlias = NDArray[np.float64]


@dataclass(frozen=True, slots=True)
class PaylineEvaluation:
    """Dense payline results with shape ``(batch_size, line_count)``."""

    winning_symbols: WinningSymbolBatch
    match_counts: MatchCountBatch
    payout_multipliers: PayoutMultiplierBatch

    def __post_init__(self) -> None:
        expected_shape = self.winning_symbols.shape

        if self.winning_symbols.ndim != 2:
            raise ValueError(
                "Payline evaluation arrays must be two-dimensional."
            )

        if self.match_counts.shape != expected_shape:
            raise ValueError(
                "match_counts must match winning_symbols in shape."
            )

        if self.payout_multipliers.shape != expected_shape:
            raise ValueError(
                "payout_multipliers must match winning_symbols in shape."
            )

    @property
    def total_multiplier_per_spin(self) -> PayoutMultiplierBatch:
        """Return the sum of all active payline wins for each spin."""

        return np.sum(
            self.payout_multipliers,
            axis=1,
            dtype=np.float64,
        )


@dataclass(frozen=True, slots=True)
class PaylineEvaluator:
    """
    Precompiled evaluator for one fixed set of always-active paylines.

    Build this object once and reuse it for every simulation batch.
    """

    payline_rows: CompiledPaylines
    payout_matrix: PaytableMatrix
    minimum_match_count: int
    wild_symbol: int = int(Symbol.WILD)
    scatter_symbol: int = int(Symbol.SCATTER)

    def __post_init__(self) -> None:
        if self.payline_rows.ndim != 2:
            raise ValueError(
                "payline_rows must have shape (line_count, reel_count)."
            )

        if self.payline_rows.shape[0] == 0:
            raise ValueError("At least one payline is required.")

        if self.payline_rows.shape[1] == 0:
            raise ValueError("At least one reel is required.")

        if np.any(self.payline_rows < 0):
            raise ValueError("Payline row indices cannot be negative.")

        if self.payout_matrix.ndim != 2:
            raise ValueError(
                "payout_matrix must have shape "
                "(symbol_count, reel_count + 1)."
            )

        if self.payout_matrix.shape[1] != self.reel_count + 1:
            raise ValueError(
                "The payout matrix reel count does not match the "
                "payline reel count."
            )

        if not 0 < self.minimum_match_count <= self.reel_count:
            raise ValueError(
                "minimum_match_count must be between 1 and reel_count."
            )

        symbol_count = self.payout_matrix.shape[0]

        if not 0 <= self.wild_symbol < symbol_count:
            raise ValueError(
                "wild_symbol is outside the payout matrix."
            )

        if not 0 <= self.scatter_symbol < symbol_count:
            raise ValueError(
                "scatter_symbol is outside the payout matrix."
            )

        if self.wild_symbol == self.scatter_symbol:
            raise ValueError(
                "wild_symbol and scatter_symbol must be different."
            )

    @classmethod
    def from_definitions(
        cls,
        paylines: PaylineSet,
        paytable: Paytable,
    ) -> PaylineEvaluator:
        """Compile validated payline and paytable definitions once."""

        if paylines.reel_count != paytable.reel_count:
            raise ValueError(
                "The payline and paytable reel counts must match."
            )

        payline_rows = compile_paylines(paylines)
        payline_rows.flags.writeable = False

        return cls(
            payline_rows=payline_rows,
            payout_matrix=compile_paytable(paytable),
            minimum_match_count=paytable.minimum_match_count,
        )

    @property
    def line_count(self) -> int:
        return int(self.payline_rows.shape[0])

    @property
    def reel_count(self) -> int:
        return int(self.payline_rows.shape[1])

    def evaluate(
        self,
        screens: ScreenBatchArray,
    ) -> PaylineEvaluation:
        """
        Evaluate every configured payline for every supplied screen.

        ``screens`` uses layout ``(spin, row, reel)``. A line begins on
        reel zero and pays only for the longest connected prefix with at
        least ``minimum_match_count`` symbols.

        Wild behavior:
        - Wild substitutes for a regular symbol.
        - Leading wilds substitute for the first connected regular symbol.
        - A connected prefix containing only wilds pays as WILD.
        - Scatter breaks a payline and is never substituted by wild.
        """

        if screens.ndim != 3:
            raise ValueError(
                "screens must have shape "
                "(batch_size, row_count, reel_count)."
            )

        if screens.shape[2] != self.reel_count:
            raise ValueError(
                f"Expected {self.reel_count} screen reels, received "
                f"{screens.shape[2]}."
            )

        if screens.shape[1] == 0:
            raise ValueError("screens must contain at least one row.")

        if int(np.max(self.payline_rows)) >= screens.shape[1]:
            raise ValueError(
                "A payline row index is outside the supplied screen."
            )

        reel_indices = np.arange(self.reel_count)
        line_symbols = screens[
            :,
            self.payline_rows,
            reel_indices,
        ]

        is_wild = line_symbols == self.wild_symbol
        is_non_wild = ~is_wild
        has_non_wild = np.any(is_non_wild, axis=2)

        first_non_wild_indices = np.argmax(
            is_non_wild,
            axis=2,
        )
        first_non_wild_symbols = np.take_along_axis(
            line_symbols,
            first_non_wild_indices[..., np.newaxis],
            axis=2,
        )[..., 0]

        # If the line is all wilds, or if scatter is the first non-wild
        # symbol, the connected leading wild prefix is evaluated as WILD.
        target_symbols = np.where(
            has_non_wild
            & (first_non_wild_symbols != self.scatter_symbol),
            first_non_wild_symbols,
            self.wild_symbol,
        ).astype(np.int16, copy=False)

        matches_target = line_symbols == target_symbols[..., np.newaxis]
        wild_substitutions = is_wild & (
            target_symbols[..., np.newaxis] != self.wild_symbol
        )
        connected_matches = matches_target | wild_substitutions

        connected_prefix = np.logical_and.accumulate(
            connected_matches,
            axis=2,
        )
        match_counts = np.sum(
            connected_prefix,
            axis=2,
            dtype=np.int16,
        )

        base_payout_multipliers = self.payout_matrix[
            target_symbols,
            match_counts,
        ]

        qualifies = match_counts >= self.minimum_match_count

        base_payout_multipliers = np.where(
            qualifies,
            base_payout_multipliers,
            0,
        ).astype(np.float64, copy=False)

        wild_counts = np.sum(
            is_wild & connected_prefix,
            axis=2,
            dtype=np.int16
        )
        wild_multipliers = np.left_shift(
            np.int64(1),
            wild_counts,
        )

        payout_multipliers = (
            base_payout_multipliers * wild_multipliers
        ).astype(np.float64, copy=False)

        win_mask = payout_multipliers > 0.0

        winning_symbols = np.where(
            win_mask,
            target_symbols,
            -1,
        ).astype(np.int16, copy=False)

        winning_match_counts = np.where(
            win_mask,
            match_counts,
            0,
        ).astype(np.int16, copy=False)

        return PaylineEvaluation(
            winning_symbols=winning_symbols,
            match_counts=winning_match_counts,
            payout_multipliers=payout_multipliers,
        )
