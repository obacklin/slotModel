
from __future__ import annotations
import unittest

import numpy as np
from slotmodel.sim.eval import PaylineEvaluator
from slotmodel.sim.reels import Symbol
from slotmodel.sim.paytable import ( 
    PAYTABLE,
    compile_paytable
)


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