from __future__ import annotations

import unittest

import numpy as np

from slotmodel.sim.paylines.payline_def import (
    PaylineSet,
    compile_paylines,
)
from slotmodel.sim.paylines.paylines import PAYLINES


class PaylineDefinitionTests(unittest.TestCase):
    def test_configured_paylines_have_expected_geometry(self) -> None:
        self.assertEqual(PAYLINES.reel_count, 5)
        self.assertEqual(PAYLINES.row_count, 3)
        self.assertEqual(len(PAYLINES.lines), 15)

        for line in PAYLINES.lines:
            self.assertEqual(len(line), PAYLINES.reel_count)
            self.assertTrue(
                all(0 <= row < PAYLINES.row_count for row in line)
            )

        self.assertEqual(len(set(PAYLINES.lines)), len(PAYLINES.lines))

    def test_compile_paylines_preserves_lines_and_dtype(self) -> None:
        compiled = compile_paylines(PAYLINES)

        expected = np.asarray(PAYLINES.lines, dtype=np.int8)

        self.assertEqual(
            compiled.shape,
            (len(PAYLINES.lines), PAYLINES.reel_count),
        )
        self.assertEqual(compiled.dtype, np.int8)
        np.testing.assert_array_equal(compiled, expected)

    def test_nonpositive_reel_count_is_rejected(self) -> None:
        with self.assertRaises(ValueError):
            PaylineSet(
                reel_count=0,
                row_count=3,
                lines=((0,),),
            )

    def test_nonpositive_row_count_is_rejected(self) -> None:
        with self.assertRaises(ValueError):
            PaylineSet(
                reel_count=1,
                row_count=0,
                lines=((0,),),
            )

    def test_empty_payline_set_is_rejected(self) -> None:
        with self.assertRaises(ValueError):
            PaylineSet(
                reel_count=5,
                row_count=3,
                lines=(),
            )

    def test_wrong_number_of_reel_positions_is_rejected(self) -> None:
        with self.assertRaises(ValueError):
            PaylineSet(
                reel_count=5,
                row_count=3,
                lines=((0, 0, 0, 0),),
            )

    def test_negative_row_index_is_rejected(self) -> None:
        with self.assertRaises(ValueError):
            PaylineSet(
                reel_count=5,
                row_count=3,
                lines=((0, 0, -1, 0, 0),),
            )

    def test_row_index_equal_to_row_count_is_rejected(self) -> None:
        with self.assertRaises(ValueError):
            PaylineSet(
                reel_count=5,
                row_count=3,
                lines=((0, 0, 3, 0, 0),),
            )

    def test_duplicate_payline_is_rejected(self) -> None:
        with self.assertRaises(ValueError):
            PaylineSet(
                reel_count=5,
                row_count=3,
                lines=(
                    (0, 0, 0, 0, 0),
                    (0, 0, 0, 0, 0),
                ),
            )


if __name__ == "__main__":
    unittest.main()
