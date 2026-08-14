
from __future__ import annotations
import unittest

import numpy as np
from slotmodel.sim.eval import PaylineEvaluator
from slotmodel.sim.reels import Symbol
from slotmodel.sim.paytable import ( 
    PAYTABLE,
    compile_paytable
)
from slotmodel.sim.paylines import PAYLINES


class PayLineEvalTest(unittest.TestCase):
    def setUp(self)->None:
        self.symbol_count = max(
            int(symbol) for symbol in Symbol
        ) + 1

        self.payline_rows = np.asarray(
            [[0,0,0,0,0]], dtype = np.int8,
        )

    def make_evaluator(
            self,
            payout_matrix: np.ndarray,
    ) -> PaylineEvaluator:
        return PaylineEvaluator(
            payline_rows=self.payline_rows,
            payout_matrix=payout_matrix,
            minimum_match_count=3,
        )

    def test_wilds_multiply_base_symbol_payout(self) -> None:
        payout_matrix = compile_paytable(PAYTABLE)

        evaluator = PaylineEvaluator(
            payline_rows=np.asarray(
                [[0, 0, 0, 0, 0]],
                dtype=np.int8,
            ),
            payout_matrix=payout_matrix,
            minimum_match_count=PAYTABLE.minimum_match_count,
        )

        coin = int(Symbol.COIN)
        wild = int(Symbol.WILD)
        other = int(Symbol.J)

        screens = np.asarray(
            [
                [[coin, coin, coin, other, other]],
                [[coin, wild, coin, other, other]],
                [[wild, coin, wild, other, other]],
                [[coin, wild, wild, other, other]],
            ],
            dtype=np.int16,
        )

        result = evaluator.evaluate(screens)

        base_coin_payout = payout_matrix[
            int(Symbol.COIN),
            3,
        ]

        expected = base_coin_payout * np.asarray(
            [1.0, 2.0, 4.0, 4.0],
            dtype=payout_matrix.dtype
        )

        np.testing.assert_allclose(
            result.payout_multipliers[:, 0],
            expected,
            rtol=1e-6,
            atol=1e-6
        )

    def test_lookup_matches_reference_for_every_symbol_sequence(
        self,
    ) -> None:
        payout_matrix = compile_paytable(PAYTABLE)
        evaluator = self.make_evaluator(payout_matrix)

        symbol_count = payout_matrix.shape[0]
        sequence_count = (
            symbol_count ** evaluator.reel_count
        )

        sequence_ids = np.arange(
            sequence_count,
            dtype=np.int32,
        )
        sequences = np.empty(
            (sequence_count, evaluator.reel_count),
            dtype=np.int16,
        )

        remaining = sequence_ids.copy()

        for reel_index in range(
            evaluator.reel_count - 1,
            -1,
            -1,
        ):
            sequences[:, reel_index] = (
                remaining % symbol_count
            )
            remaining //= symbol_count

        screens = sequences[:, np.newaxis, :]

        result = evaluator.evaluate(screens)
        expected = _reference_evaluate(
            evaluator,
            screens,
        )

        np.testing.assert_array_equal(
            result.winning_symbols,
            expected[0],
        )
        np.testing.assert_array_equal(
            result.match_counts,
            expected[1],
        )
        np.testing.assert_array_equal(
            result.payout_multipliers,
            expected[2],
        )
        
    def test_lookup_matches_reference_for_full_payline_set(
        self,
    ) -> None:
        evaluator = PaylineEvaluator.from_definitions(
            PAYLINES,
            PAYTABLE,
        )

        rng = np.random.default_rng(12345)

        screens = rng.integers(
            0,
            self.symbol_count,
            size=(2_000, 3, evaluator.reel_count),
            dtype=np.int16,
        )

        result = evaluator.evaluate(screens)
        expected = _reference_evaluate(
            evaluator,
            screens,
        )

        np.testing.assert_array_equal(
            result.winning_symbols,
            expected[0],
        )
        np.testing.assert_array_equal(
            result.match_counts,
            expected[1],
        )
        np.testing.assert_array_equal(
            result.payout_multipliers,
            expected[2],
        )

def _reference_evaluate(
    evaluator: PaylineEvaluator,
    screens: np.ndarray,
) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    reel_indices = np.arange(evaluator.reel_count)

    line_symbols = screens[
        :,
        evaluator.payline_rows,
        reel_indices,
    ]

    is_wild = line_symbols == evaluator.wild_symbol
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

    target_symbols = np.where(
        has_non_wild
        & (first_non_wild_symbols != evaluator.scatter_symbol),
        first_non_wild_symbols,
        evaluator.wild_symbol,
    ).astype(np.int16, copy=False)

    connected_matches = (
        line_symbols == target_symbols[..., np.newaxis]
    ) | (
        is_wild
        & (
            target_symbols[..., np.newaxis]
            != evaluator.wild_symbol
        )
    )

    connected_prefix = np.logical_and.accumulate(
        connected_matches,
        axis=2,
    )

    match_counts = np.sum(
        connected_prefix,
        axis=2,
        dtype=np.int16,
    )

    base_payouts = evaluator.payout_matrix[
        target_symbols,
        match_counts,
    ]

    base_payouts = np.where(
        match_counts >= evaluator.minimum_match_count,
        base_payouts,
        0.0,
    )

    wild_counts = np.sum(
        is_wild & connected_prefix,
        axis=2,
        dtype=np.int16,
    )

    payouts = base_payouts * np.left_shift(
        np.int64(1),
        wild_counts,
    )

    win_mask = payouts > 0.0

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

    return (
        winning_symbols,
        winning_match_counts,
        payouts,
    )