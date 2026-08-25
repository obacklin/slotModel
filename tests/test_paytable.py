from __future__ import annotations

import unittest

import numpy as np

from slotmodel.sim.paytable import (
    PAYTABLE_HIGH_VOL,
    Paytable,
    PaytableEntry,
    compile_paytable,
)
from slotmodel.sim.reels import Symbol


class PaytableDefinitionTests(unittest.TestCase):
    def test_configured_paytable_covers_every_payline_symbol(self) -> None:
        configured_symbols = {entry.symbol for entry in PAYTABLE_HIGH_VOL.entries}
        expected_symbols = set(Symbol) - {Symbol.SCATTER}

        self.assertEqual(configured_symbols, expected_symbols)
        self.assertEqual(PAYTABLE_HIGH_VOL.reel_count, 5)
        self.assertEqual(PAYTABLE_HIGH_VOL.minimum_match_count, 3)

    def test_configured_multipliers_increase_with_match_count(self) -> None:
        for entry in PAYTABLE_HIGH_VOL.entries:
            with self.subTest(symbol=entry.symbol.name):
                self.assertTrue(
                    all(
                        later > earlier
                        for earlier, later in zip(
                            entry.multipliers,
                            entry.multipliers[1:],
                        )
                    )
                )

    def test_compile_paytable_creates_direct_lookup_matrix(self) -> None:
        matrix = compile_paytable(PAYTABLE_HIGH_VOL)
        symbol_count = max(int(symbol) for symbol in Symbol) + 1

        self.assertEqual(
            matrix.shape,
            (symbol_count, PAYTABLE_HIGH_VOL.reel_count + 1),
        )
        self.assertEqual(matrix.dtype, np.float64)
        self.assertFalse(matrix.flags.writeable)

        for entry in PAYTABLE_HIGH_VOL.entries:
            with self.subTest(symbol=entry.symbol.name):
                np.testing.assert_allclose(
                    matrix[
                        int(entry.symbol),
                        PAYTABLE_HIGH_VOL.minimum_match_count:
                        PAYTABLE_HIGH_VOL.reel_count + 1,
                    ],
                    np.asarray(entry.multipliers, dtype=np.float64),
                )

    def test_compile_paytable_leaves_nonwinning_lookups_at_zero(self) -> None:
        matrix = compile_paytable(PAYTABLE_HIGH_VOL)

        np.testing.assert_array_equal(
            matrix[:, :PAYTABLE_HIGH_VOL.minimum_match_count],
            np.zeros_like(matrix[:, :PAYTABLE_HIGH_VOL.minimum_match_count]),
        )
        np.testing.assert_array_equal(
            matrix[int(Symbol.SCATTER)],
            np.zeros(PAYTABLE_HIGH_VOL.reel_count + 1, dtype=np.float64),
        )

    def test_scatter_paytable_entry_is_rejected(self) -> None:
        with self.assertRaises(ValueError):
            PaytableEntry(
                symbol=Symbol.SCATTER,
                multipliers=(1.0, 2.0, 3.0),
            )

    def test_empty_multiplier_tuple_is_rejected(self) -> None:
        with self.assertRaises(ValueError):
            PaytableEntry(
                symbol=Symbol.A,
                multipliers=(),
            )

    def test_boolean_multiplier_is_rejected(self) -> None:
        with self.assertRaises(TypeError):
            PaytableEntry(
                symbol=Symbol.A,
                multipliers=(1.0, True, 3.0),
            )

    def test_non_real_multiplier_is_rejected(self) -> None:
        with self.assertRaises(TypeError):
            PaytableEntry(
                symbol=Symbol.A,
                multipliers=(1.0, "2", 3.0),  # type: ignore[arg-type]
            )

    def test_nonpositive_multiplier_is_rejected(self) -> None:
        for multiplier in (0.0, -1.0):
            with self.subTest(multiplier=multiplier):
                with self.assertRaises(ValueError):
                    PaytableEntry(
                        symbol=Symbol.A,
                        multipliers=(1.0, multiplier, 3.0),
                    )

    def test_nonfinite_multiplier_is_rejected(self) -> None:
        for multiplier in (np.inf, -np.inf, np.nan):
            with self.subTest(multiplier=multiplier):
                with self.assertRaises(ValueError):
                    PaytableEntry(
                        symbol=Symbol.A,
                        multipliers=(1.0, multiplier, 3.0),
                    )

    def test_nonpositive_reel_count_is_rejected(self) -> None:
        with self.assertRaises(ValueError):
            Paytable(
                reel_count=0,
                minimum_match_count=1,
                entries=(
                    PaytableEntry(Symbol.A, (1.0,)),
                ),
            )

    def test_invalid_minimum_match_count_is_rejected(self) -> None:
        entry = PaytableEntry(Symbol.A, (1.0,))

        with self.assertRaises(ValueError):
            Paytable(
                reel_count=1,
                minimum_match_count=0,
                entries=(entry,),
            )

        with self.assertRaises(ValueError):
            Paytable(
                reel_count=1,
                minimum_match_count=2,
                entries=(entry,),
            )

    def test_empty_paytable_is_rejected(self) -> None:
        with self.assertRaises(ValueError):
            Paytable(
                reel_count=5,
                minimum_match_count=3,
                entries=(),
            )

    def test_wrong_number_of_multipliers_is_rejected(self) -> None:
        with self.assertRaises(ValueError):
            Paytable(
                reel_count=5,
                minimum_match_count=3,
                entries=(
                    PaytableEntry(Symbol.A, (1.0, 2.0)),
                ),
            )

    def test_duplicate_symbol_entry_is_rejected(self) -> None:
        entry = PaytableEntry(Symbol.A, (1.0, 2.0, 3.0))

        with self.assertRaises(ValueError):
            Paytable(
                reel_count=5,
                minimum_match_count=3,
                entries=(entry, entry),
            )


if __name__ == "__main__":
    unittest.main()