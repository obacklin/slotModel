from __future__ import annotations

import unittest

import numpy as np

from slotmodel.sim.analytics import (
    simulate_bonus_free_spin_batch,
    simulate_bonus_games
)
from slotmodel.sim.eval import (
    PaylineEvaluator,
    evaluate_bonus_step,
    overlay_locked_symbols,
    winning_pos_mask
)
from slotmodel.sim.paytable import Paytable, PaytableEntry
from slotmodel.sim.reels import ReelSet, Symbol
from slotmodel.sim.screens import ScreenModel
from slotmodel.sim.paylines import PAYLINES


class ScriptedRng:
    """Minimal deterministic replacement for Generator in unit tests."""

    def __init__(self, outputs: list[np.ndarray]) -> None:
        self._outputs = iter(outputs)

    def integers(
        self,
        low: int,
        high: int,
        size: object,
        dtype: object,
    ) -> np.ndarray:
        del low, high, size
        return np.asarray(next(self._outputs), dtype=dtype)


class BonusGameTests(unittest.TestCase):
    @staticmethod
    def make_evaluator(
        lines: tuple[tuple[int, ...], ...] = ((0, 0, 0, 0, 0),),
    ) -> PaylineEvaluator:
        from slotmodel.sim.paylines.payline_def import PaylineSet

        paylines = PaylineSet(
            reel_count=5,
            row_count=3,
            lines=lines,
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
        return PaylineEvaluator.from_definitions(paylines, paytable)

    def test_winning_position_mask_maps_only_paying_prefix(self) -> None:
        evaluator = self.make_evaluator()
        j = int(Symbol.J)
        scatter = int(Symbol.SCATTER)
        screens = np.asarray(
            [[[j, j, j, scatter, j]]],
            dtype=np.int16,
        )

        evaluation = evaluator.evaluate(screens)
        result = winning_pos_mask(
            evaluation=evaluation,
            evaluator=evaluator,
            row_count=1,
        )

        expected = np.asarray(
            [[[True, True, True, False, False]]],
            dtype=np.bool_,
        )
        np.testing.assert_array_equal(result, expected)

    def test_bonus_step_never_locks_scatters(self) -> None:
        evaluator = self.make_evaluator()
        j = int(Symbol.J)
        scatter = int(Symbol.SCATTER)
        screens = np.asarray(
            [
                [
                    [j, j, j, scatter, scatter],
                    [scatter, scatter, scatter, scatter, scatter],
                    [scatter, scatter, scatter, scatter, scatter],
                ]
            ],
            dtype=np.int16,
        )
        locked = np.zeros_like(screens, dtype=np.bool_)

        result = evaluate_bonus_step(
            screens=screens,
            locked_mask=locked,
            evaluator=evaluator,
        )

        self.assertTrue(bool(result.retrigger_mask[0]))
        self.assertTrue(bool(result.cont_mask[0]))
        self.assertFalse(
            bool(np.any(result.new_lock_mask[screens == scatter]))
        )

    def test_overlay_uses_new_reel_screen_only_where_unlocked(self) -> None:
        current = np.asarray(
            [[[1, 2, 3], [4, 5, 6]]],
            dtype=np.int16,
        )
        replacement = np.asarray(
            [[[10, 20, 30], [40, 50, 60]]],
            dtype=np.int16,
        )
        locked = np.asarray(
            [[[True, False, True], [False, True, False]]],
            dtype=np.bool_,
        )

        result = overlay_locked_symbols(
            current_screens=current,
            replacement_screens=replacement,
            locked_mask=locked,
        )

        expected = np.asarray(
            [[[1, 20, 3], [40, 5, 60]]],
            dtype=np.int16,
        )
        np.testing.assert_array_equal(result, expected)

    def test_free_spin_retriggers_at_most_once_and_scatters_stay_unlocked(
        self,
    ) -> None:
        j = int(Symbol.J)
        scatter = int(Symbol.SCATTER)
        reels: ReelSet = (
            np.asarray([j], dtype=np.int16),
            np.asarray([j], dtype=np.int16),
            np.asarray([j], dtype=np.int16),
            np.asarray([scatter], dtype=np.int16),
            np.asarray([scatter], dtype=np.int16),
        )
        model = ScreenModel.from_reels(
            reels=reels,
            window_offsets=(0, 0, 0),
        )
        evaluator = self.make_evaluator()

        result = simulate_bonus_free_spin_batch(
            model=model,
            evaluator=evaluator,
            batch_size=8,
            rng=np.random.default_rng(123),
        )

        # The initial screen creates a sticky J win, causing one respin.
        # Both evaluated screens contain at least three scatters, so each
        # screen awards exactly one retrigger.
        np.testing.assert_array_equal(
            result.respin_counts,
            np.ones(8, dtype=np.int32),
        )
        np.testing.assert_array_equal(
            result.retrigger_counts,
            np.ones(8, dtype=np.int32)
        )
        self.assertFalse(
            bool(
                np.any(
                    result.final_locked_mask[
                        result.final_screens == scatter
                    ]
                )
            )
        )

    def test_only_terminal_screen_payout_is_returned(self) -> None:
        j = int(Symbol.J)
        q = int(Symbol.Q)
        reels: ReelSet = (
            np.asarray([j, q], dtype=np.int16),
            np.asarray([j, q], dtype=np.int16),
            np.asarray([j, q], dtype=np.int16),
            np.asarray([q, j], dtype=np.int16),
            np.asarray([q, q], dtype=np.int16),
        )
        model = ScreenModel.from_reels(
            reels=reels,
            window_offsets=(0,),
        )
        evaluator = self.make_evaluator()
        rng = ScriptedRng(
            outputs=[
                np.asarray([[0, 0, 0, 0, 0]], dtype=np.int32),
                np.asarray([4], dtype=np.int32),
                np.asarray([[1, 1, 1, 1, 1]], dtype=np.int32),
                np.asarray([[0, 0, 0, 0, 0]], dtype=np.int32),
            ]
        )

        result = simulate_bonus_free_spin_batch(
            model=model,
            evaluator=evaluator,
            batch_size=1,
            rng=rng,  # type: ignore[arg-type]
        )

        # The first screen is J-J-J-Q-W and would pay 1.0. The first
        # respin expands it to J-J-J-J-W; all positions then lock and the
        # terminal screen pays the 5-symbol J win with one wild: 5 * 2.
        np.testing.assert_array_equal(
            result.respin_counts,
            np.asarray([2], dtype=np.int32),
        )
        np.testing.assert_allclose(
            result.payout_multipliers,
            np.asarray([10.0]),
        )

    def test_complete_bonus_consumes_configured_free_spins(self) -> None:
        j = int(Symbol.J)
        reels: ReelSet = tuple(
            np.asarray([j], dtype=np.int16)
            for _ in range(5)
        )
        model = ScreenModel.from_reels(
            reels=reels,
            window_offsets=(0,),
        )
        evaluator = self.make_evaluator()

        result = simulate_bonus_games(
            model=model,
            evaluator=evaluator,
            total_bonus_games=5,
            batch_size=2,
            rng=np.random.default_rng(789),
            initial_free_spins=2,
        )

        np.testing.assert_array_equal(
            result.free_spin_counts,
            np.full(5, 2, dtype=np.int32),
        )
        np.testing.assert_array_equal(
            result.respin_counts,
            np.full(5, 2, dtype=np.int32),
        )
        np.testing.assert_array_equal(
            result.retrigger_counts,
            np.zeros(5, dtype=np.int32),
        )
        np.testing.assert_allclose(
            result.payout_multipliers,
            np.full(5, 20.0),
        )
        np.testing.assert_array_equal(
            result.winning_free_spin_counts,
            np.full(5, 2, dtype=np.int32),
        )
        
    def test_scatter_hits_accumulate_across_respins_for_retrigger(self) -> None:
        j = int(Symbol.J)
        q = int(Symbol.Q)
        scatter = int(Symbol.SCATTER)

        reels: ReelSet = (
            np.asarray([j, j], dtype=np.int16),
            np.asarray([j, j], dtype=np.int16),
            np.asarray([j, j], dtype=np.int16),
            np.asarray([scatter, scatter], dtype=np.int16),
            np.asarray([q, scatter], dtype=np.int16),
        )
        model = ScreenModel.from_reels(
            reels=reels,
            window_offsets=(0,),
        )
        evaluator = self.make_evaluator()
        rng = ScriptedRng(
            outputs=[
                # Initial screen: J-J-J-SCATTER-Q.
                np.asarray([[0, 0, 0, 0, 0]], dtype=np.int32),

                # Guaranteed Wild goes over the first J:
                # W-J-J-SCATTER-Q.
                np.asarray([0], dtype=np.int32),

                # Sticky W-J-J remain. The two free positions produce
                # SCATTER-SCATTER:
                # W-J-J-SCATTER-SCATTER.
                np.asarray([[0, 0, 0, 0, 1]], dtype=np.int32),
            ]
        )

        result = simulate_bonus_free_spin_batch(
            model=model,
            evaluator=evaluator,
            batch_size=1,
            rng=rng,  # type: ignore[arg-type]
        )

        # Initial screen collects 1 scatter.
        # Respin collects another 2.
        # 1 + 2 = 3 => one retrigger.
        np.testing.assert_array_equal(
            result.respin_counts,
            np.asarray([1], dtype=np.int32),
        )
        np.testing.assert_array_equal(
            result.retrigger_counts,
            np.asarray([1], dtype=np.int32),
        )

    def test_winning_position_mask_matches_reference_mapping(
    self,
    ) -> None:
        evaluator = self.make_evaluator(
            lines=PAYLINES.lines,
        )

        rng = np.random.default_rng(12345)

        symbols = np.asarray(
            [
                int(Symbol.J),
                int(Symbol.WILD),
                int(Symbol.SCATTER),
            ],
            dtype=np.int16,
        )

        screens = rng.choice(
            symbols,
            size=(1_000, 3, 5),
        ).astype(np.int16)

        evaluation = evaluator.evaluate(screens)

        result = winning_pos_mask(
            evaluation=evaluation,
            evaluator=evaluator,
            row_count=3,
        )

        expected = np.zeros(
            (screens.shape[0], 3, 5),
            dtype=np.bool_,
        )

        line_count, reel_count = evaluator.payline_rows.shape

        for line_index in range(line_count):
            match_counts = evaluation.match_counts[:, line_index]

            for reel_index in range(reel_count):
                row_index = int(
                    evaluator.payline_rows[
                        line_index,
                        reel_index,
                    ]
                )

                expected[:, row_index, reel_index] |= (
                    match_counts > reel_index
                )

        np.testing.assert_array_equal(result, expected)

if __name__ == "__main__":
    unittest.main()
