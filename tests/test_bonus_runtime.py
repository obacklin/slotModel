from __future__ import annotations

import unittest

import numpy as np

from slotmodel.runtime_tools import BonusGameRuntime
from slotmodel.sim.analytics.bonus_game import simulate_bonus_games
from slotmodel.sim.eval import PaylineEvaluator
from slotmodel.sim.paylines.payline_def import PaylineSet
from slotmodel.sim.paytable import Paytable, PaytableEntry
from slotmodel.sim.reels import ReelSet, Symbol
from slotmodel.sim.screens import ScreenModel


class BonusRuntimeTests(unittest.TestCase):
    @staticmethod
    def _make_game() -> tuple[ScreenModel, PaylineEvaluator]:
        j = int(Symbol.J)
        reels: ReelSet = tuple(
            np.asarray([j], dtype=np.int16)
            for _ in range(5)
        )
        model = ScreenModel.from_reels(
            reels=reels,
            window_offsets=(0,),
        )
        paylines = PaylineSet(
            reel_count=5,
            row_count=1,
            lines=((0, 0, 0, 0, 0),),
        )
        paytable = Paytable(
            reel_count=5,
            minimum_match_count=3,
            entries=(
                PaytableEntry(
                    symbol=Symbol.WILD,
                    multipliers=(10.0, 20.0, 75.0),
                ),
                PaytableEntry(
                    symbol=Symbol.J,
                    multipliers=(1.0, 2.0, 5.0),
                ),
            ),
        )
        evaluator = PaylineEvaluator.from_definitions(
            paylines,
            paytable,
        )
        return model, evaluator

    def test_runtime_exposes_new_and_retained_sticky_positions(self) -> None:
        model, evaluator = self._make_game()
        runtime = BonusGameRuntime(
            model=model,
            evaluator=evaluator,
            rng=np.random.default_rng(123),
            initial_free_spins=1,
        )

        first_step = runtime.next_step()
        self.assertIsNotNone(first_step)
        assert first_step is not None

        self.assertFalse(first_step.is_respin)
        self.assertEqual(first_step.new_lock_count, 4)
        self.assertEqual(first_step.locked_count, 5)
        self.assertTrue(first_step.continues)
        self.assertEqual(
            int(np.count_nonzero(first_step.locked_mask_before)),
            0,
        )
        self.assertEqual(
            int(np.count_nonzero(first_step.spin_lock_mask)),
            1,
        )
        self.assertTrue(
            np.all(
                first_step.spin_lock_mask
                <= first_step.locked_mask_after
            )
        )
        self.assertFalse(
            np.any(
                first_step.spin_lock_mask
                & first_step.new_lock_mask
            )
        )

        terminal_step = runtime.next_step()
        self.assertIsNotNone(terminal_step)
        assert terminal_step is not None

        self.assertTrue(terminal_step.is_respin)
        self.assertTrue(terminal_step.is_terminal)
        self.assertEqual(terminal_step.new_lock_count, 0)
        self.assertEqual(
            int(np.count_nonzero(terminal_step.locked_mask_before)),
            5,
        )
        self.assertEqual(
            int(np.count_nonzero(terminal_step.spin_lock_mask)),
            5,
        )
        self.assertEqual(terminal_step.terminal_payout_multiplier, 10.0)
        self.assertIsNone(runtime.next_step())

    def test_runtime_matches_single_game_batch_semantics(self) -> None:
        model, evaluator = self._make_game()
        runtime = BonusGameRuntime(
            model=model,
            evaluator=evaluator,
            rng=np.random.default_rng(789),
            initial_free_spins=2,
        )

        while runtime.next_step() is not None:
            pass

        batch_result = simulate_bonus_games(
            model=model,
            evaluator=evaluator,
            total_bonus_games=1,
            batch_size=1,
            rng=np.random.default_rng(789),
            initial_free_spins=2,
        )

        self.assertEqual(
            runtime.total_payout_multiplier,
            float(batch_result.payout_multipliers[0]),
        )
        self.assertEqual(
            runtime.completed_free_spins,
            int(batch_result.free_spin_counts[0]),
        )
        self.assertEqual(
            runtime.total_respins,
            int(batch_result.respin_counts[0]),
        )
        self.assertEqual(
            runtime.total_retriggers,
            int(batch_result.retrigger_counts[0]),
        )


if __name__ == "__main__":
    unittest.main()