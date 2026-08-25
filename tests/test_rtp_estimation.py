from __future__ import annotations

import unittest

import numpy as np

from slotmodel.sim.analytics import (
    AdaptiveSamplingStage,
    estimate_rtp_adaptive,
    sim_report,
)
from slotmodel.sim.eval import PaylineEvaluator
from slotmodel.sim.paylines import PAYLINES
from slotmodel.sim.paytable import PAYTABLE_HIGH_VOL
from slotmodel.sim.reels import read_reels
from slotmodel.sim.screens import ScreenModel


class AdaptiveRtpEstimationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.model = ScreenModel.from_reels(
            reels=read_reels(),
            window_offsets=(0, 1, 2),
        )
        cls.evaluator = PaylineEvaluator.from_definitions(
            paylines=PAYLINES,
            paytable=PAYTABLE_HIGH_VOL,
        )

    def test_single_stage_matches_sim_report_rtp_statistics(self) -> None:
        stage = AdaptiveSamplingStage(base_spins=500, bonus_games=500)
        seed = 12345

        estimate = estimate_rtp_adaptive(
            model=self.model,
            target_min=-1.0,
            target_max=10_000.0,
            stages=(stage,),
            seed=seed,
            evaluator=self.evaluator,
        )
        report = sim_report(
            model=self.model,
            total_spins=stage.base_spins,
            total_bonus_games=stage.bonus_games,
            seed=seed,
            evaluator=self.evaluator,
        )

        self.assertAlmostEqual(estimate.rtp_base, report.rtp_base, places=12)
        self.assertAlmostEqual(estimate.bonus_freq, report.bonus_freq, places=12)
        self.assertAlmostEqual(
            estimate.mean_bonus_payout,
            report.mean_bonus_payout,
            places=12,
        )
        self.assertAlmostEqual(estimate.rtp_bonus, report.rtp_bonus, places=12)
        self.assertAlmostEqual(
            estimate.rtp_total_se,
            report.rtp_total_se,
            places=12,
        )
        self.assertFalse(estimate.stopped_early)
        self.assertEqual(estimate.stop_reason, "max_samples")

    def test_confidence_interval_can_stop_after_first_stage(self) -> None:
        stages = (
            AdaptiveSamplingStage(base_spins=100, bonus_games=100),
            AdaptiveSamplingStage(base_spins=500, bonus_games=500),
        )

        estimate = estimate_rtp_adaptive(
            model=self.model,
            target_min=1_000.0,
            target_max=1_001.0,
            stages=stages,
            seed=91,
            evaluator=self.evaluator,
        )

        self.assertTrue(estimate.stopped_early)
        self.assertEqual(estimate.stop_reason, "below_target")
        self.assertEqual(estimate.stage_index, 0)
        self.assertEqual(estimate.base_spins, 100)
        self.assertEqual(estimate.bonus_games, 100)
        self.assertLess(estimate.confidence_high, 1_000.0)

    def test_multistage_estimation_is_seed_reproducible(self) -> None:
        stages = (
            AdaptiveSamplingStage(base_spins=100, bonus_games=100),
            AdaptiveSamplingStage(base_spins=250, bonus_games=250),
        )
        kwargs = dict(
            model=self.model,
            target_min=-1.0,
            target_max=10_000.0,
            stages=stages,
            seed=456,
            evaluator=self.evaluator,
        )

        first = estimate_rtp_adaptive(**kwargs)
        second = estimate_rtp_adaptive(**kwargs)

        self.assertEqual(first, second)
        self.assertEqual(first.base_spins, 250)
        self.assertEqual(first.bonus_games, 250)
        self.assertFalse(first.stopped_early)

    def test_stages_must_be_strictly_increasing(self) -> None:
        with self.assertRaises(ValueError):
            estimate_rtp_adaptive(
                model=self.model,
                target_min=0.9,
                target_max=1.0,
                stages=(
                    AdaptiveSamplingStage(100, 100),
                    AdaptiveSamplingStage(100, 200),
                ),
                evaluator=self.evaluator,
            )


if __name__ == "__main__":
    unittest.main()