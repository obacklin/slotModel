from __future__ import annotations

import unittest

import numpy as np

from slotmodel.sim.reels import ReelSet
from slotmodel.sim.screens import (
    ScreenModel,
    build_screens,
    iter_spin_batches,
    spin_batch,
)


class ScreenBatchTests(unittest.TestCase):
    def setUp(self) -> None:
        reels: ReelSet = (
            np.asarray([0, 1, 2, 3], dtype=np.int16),
            np.asarray([10, 11, 12, 13], dtype=np.int16),
        )

        self.model = ScreenModel.from_reels(
            reels=reels,
            window_offsets=(0, 1, 2),
        )

    def test_build_screens_uses_spin_row_reel_layout(self) -> None:
        stops = np.asarray(
            [
                [3, 2],
                [1, 0],
            ],
            dtype=np.int32,
        )

        screens = build_screens(self.model, stops)

        expected = np.asarray(
            [
                [
                    [3, 12],
                    [0, 13],
                    [1, 10],
                ],
                [
                    [1, 10],
                    [2, 11],
                    [3, 12],
                ],
            ],
            dtype=np.int16,
        )

        np.testing.assert_array_equal(screens, expected)

    def test_spin_batch_has_expected_shapes_and_dtypes(self) -> None:
        batch = spin_batch(
            model=self.model,
            batch_size=100,
            rng=np.random.default_rng(123),
        )

        self.assertEqual(batch.stops.shape, (100, 2))
        self.assertEqual(batch.screens.shape, (100, 3, 2))
        self.assertEqual(batch.stops.dtype, np.int32)
        self.assertEqual(batch.screens.dtype, np.int16)

    def test_seeded_batches_are_reproducible(self) -> None:
        first = spin_batch(
            model=self.model,
            batch_size=100,
            rng=np.random.default_rng(456),
        )

        second = spin_batch(
            model=self.model,
            batch_size=100,
            rng=np.random.default_rng(456),
        )

        np.testing.assert_array_equal(first.stops, second.stops)
        np.testing.assert_array_equal(first.screens, second.screens)

    def test_out_of_range_stop_is_rejected(self) -> None:
        with self.assertRaises(ValueError):
            build_screens(
                self.model,
                np.asarray([[4, 0]], dtype=np.int32),
            )

    def test_batch_iterator_includes_partial_final_batch(self) -> None:
        batches = list(
            iter_spin_batches(
                model=self.model,
                total_spins=10,
                batch_size=4,
                rng=np.random.default_rng(789),
            )
        )

        self.assertEqual([batch.size for batch in batches], [4, 4, 2])

    def test_visible_window_lookup_contains_every_reel_stop(
    self,
    ) -> None:
        self.assertEqual(
            self.model.visible_windows.shape,
            (
                self.model.reel_count,
                self.model.row_count,
                self.model.reel_length,
            ),
        )

        self.assertEqual(
            self.model.visible_windows.dtype,
            np.int16,
        )

        self.assertFalse(
            self.model.visible_windows.flags.writeable
        )

        stop_positions = np.arange(
            self.model.reel_length,
            dtype=np.int32,
        )

        for reel_index in range(self.model.reel_count):
            for row_index, offset in enumerate(
                self.model.window_offsets
            ):
                expected = self.model.reels[
                    reel_index,
                    (
                        stop_positions + int(offset)
                    ) % self.model.reel_length,
                ]

                np.testing.assert_array_equal(
                    self.model.visible_windows[
                        reel_index,
                        row_index,
                        :,
                    ],
                    expected,
                )


if __name__ == "__main__":
    unittest.main()
