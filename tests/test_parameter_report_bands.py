from __future__ import annotations

import unittest

import numpy as np

from slotmodel.sim.analytics.parameter_reports import (
    estimate_bonus_payout_bands,
    estimate_payout_bands,
)


class PayoutBandBoundaryTests(unittest.TestCase):
    def test_base_bands_use_lower_inclusive_upper_exclusive_boundaries(self) -> None:
        payouts = np.asarray([0.0, 0.5, 1.0, 1.5, 2.0, 4.5, 5.0, 50.0])
        bands = estimate_payout_bands(payouts)

        self.assertAlmostEqual(bands.p_0, 1 / 8)
        self.assertAlmostEqual(bands.p_0_to_1, 1 / 8)
        self.assertAlmostEqual(bands.p_1_to_2, 2 / 8)
        self.assertAlmostEqual(bands.p_2_to_5, 2 / 8)
        self.assertAlmostEqual(bands.p_5_to_10, 1 / 8)
        self.assertAlmostEqual(bands.p_over_50, 1 / 8)
        self.assertAlmostEqual(bands.band_sum, 1.0)

    def test_bonus_bands_put_boundary_values_in_the_next_band(self) -> None:
        payouts = np.asarray([0.0, 9.0, 10.0, 25.0, 50.0, 100.0, 250.0, 1000.0])
        bands = estimate_bonus_payout_bands(payouts)

        self.assertAlmostEqual(bands.p_0, 1 / 8)
        self.assertAlmostEqual(bands.p_0_to_10, 1 / 8)
        self.assertAlmostEqual(bands.p_10_to_25, 1 / 8)
        self.assertAlmostEqual(bands.p_25_to_50, 1 / 8)
        self.assertAlmostEqual(bands.p_50_to_100, 1 / 8)
        self.assertAlmostEqual(bands.p_100_to_250, 1 / 8)
        self.assertAlmostEqual(bands.p_250_to_500, 1 / 8)
        self.assertAlmostEqual(bands.p_over_1000, 1 / 8)
        self.assertAlmostEqual(bands.band_sum, 1.0)


if __name__ == "__main__":
    unittest.main()
