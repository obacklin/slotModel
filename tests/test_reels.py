from __future__ import annotations

import json
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

import numpy as np

from slotmodel.paths import REELS_CANDIDATES_DIR
from slotmodel.sim.paytable import PAYTABLE_HIGH_VOL
from slotmodel.sim.reels import (
    Symbol,
    compile_reels,
    read_reels,
)
from slotmodel.sim.reels.gen_reels import (
    generate_weighted_reels,
    save_reels,
)


def _candidate_reel_paths() -> tuple[Path, ...]:
    """Return all candidate reel JSON files, excluding report files."""

    return tuple(
        path
        for path in sorted(REELS_CANDIDATES_DIR.glob("*.json"))
        if not path.stem.endswith("_report")
    )


class ReelDefinitionTests(unittest.TestCase):
    def test_compile_reels_stacks_reels_and_makes_matrix_read_only(
        self,
    ) -> None:
        reels = (
            np.asarray([0, 1, 2], dtype=np.int16),
            np.asarray([3, 4, 5], dtype=np.int16),
        )

        matrix = compile_reels(reels)

        expected = np.asarray(
            [
                [0, 1, 2],
                [3, 4, 5],
            ],
            dtype=np.int16,
        )

        self.assertEqual(matrix.shape, (2, 3))
        self.assertEqual(matrix.dtype, np.int16)
        self.assertFalse(matrix.flags.writeable)
        np.testing.assert_array_equal(matrix, expected)

    def test_compile_reels_rejects_empty_reel_set(self) -> None:
        with self.assertRaises(ValueError):
            compile_reels(())

    def test_compile_reels_rejects_empty_reel(self) -> None:
        with self.assertRaises(ValueError):
            compile_reels(
                (np.asarray([], dtype=np.int16),)
            )

    def test_compile_reels_rejects_multidimensional_reel(self) -> None:
        with self.assertRaises(ValueError):
            compile_reels(
                (np.asarray([[0, 1]], dtype=np.int16),)
            )

    def test_compile_reels_rejects_wrong_dtype(self) -> None:
        with self.assertRaises(TypeError):
            compile_reels(
                (np.asarray([0, 1], dtype=np.int32),)
            )

    def test_compile_reels_rejects_unequal_lengths(self) -> None:
        with self.assertRaises(ValueError):
            compile_reels(
                (
                    np.asarray([0, 1], dtype=np.int16),
                    np.asarray([2, 3, 4], dtype=np.int16),
                )
            )


class ReelConfigurationTests(unittest.TestCase):
    def _write_json(self, directory: Path, data: object) -> Path:
        path = directory / "reels.json"
        path.write_text(
            json.dumps(data),
            encoding="utf-8",
        )
        return path

    def test_candidate_reel_directory_contains_reel_sets(self) -> None:
        candidate_paths = _candidate_reel_paths()

        self.assertTrue(
            candidate_paths,
            msg=(
                "No candidate reel sets were found in "
                f"{REELS_CANDIDATES_DIR}."
            ),
        )

    def test_candidate_reel_configurations_load_with_declared_geometry(
        self,
    ) -> None:
        candidate_paths = _candidate_reel_paths()

        self.assertTrue(
            candidate_paths,
            msg=(
                "No candidate reel sets were found in "
                f"{REELS_CANDIDATES_DIR}."
            ),
        )

        valid_symbol_ids = {int(symbol) for symbol in Symbol}

        for reels_path in candidate_paths:
            with self.subTest(candidate=reels_path.name):
                data = json.loads(
                    reels_path.read_text(encoding="utf-8")
                )
                reels = read_reels(reels_path)

                self.assertEqual(
                    len(reels),
                    data["number_of_reels"],
                )

                for reel_index, reel in enumerate(reels):
                    with self.subTest(
                        candidate=reels_path.name,
                        reel_index=reel_index,
                    ):
                        self.assertEqual(
                            reel.shape,
                            (data["reel_length"],),
                        )
                        self.assertEqual(reel.dtype, np.int16)
                        self.assertFalse(reel.flags.writeable)
                        self.assertTrue(
                            set(map(int, reel)).issubset(
                                valid_symbol_ids
                            )
                        )

    def test_candidate_reel_sets_contain_every_defined_symbol(
        self,
    ) -> None:
        candidate_paths = _candidate_reel_paths()

        self.assertTrue(
            candidate_paths,
            msg=(
                "No candidate reel sets were found in "
                f"{REELS_CANDIDATES_DIR}."
            ),
        )

        required_symbols = {int(symbol) for symbol in Symbol}

        for reels_path in candidate_paths:
            with self.subTest(candidate=reels_path.name):
                reels = read_reels(reels_path)

                present_symbols = {
                    int(symbol_id)
                    for reel in reels
                    for symbol_id in reel
                }

                self.assertEqual(
                    present_symbols,
                    required_symbols,
                )

    def test_every_candidate_reel_contains_every_payline_symbol(
        self,
    ) -> None:
        """Ensure every candidate reel can realize every payline symbol."""

        candidate_paths = _candidate_reel_paths()

        self.assertTrue(
            candidate_paths,
            msg=(
                "No candidate reel sets were found in "
                f"{REELS_CANDIDATES_DIR}."
            ),
        )

        required_symbol_ids = {
            int(entry.symbol) for entry in PAYTABLE_HIGH_VOL.entries
        }

        for reels_path in candidate_paths:
            reels = read_reels(reels_path)

            for reel_index, reel in enumerate(reels):
                with self.subTest(
                    candidate=reels_path.name,
                    reel_index=reel_index,
                ):
                    self.assertTrue(
                        required_symbol_ids.issubset(
                            set(map(int, reel))
                        ),
                        msg=(
                            f"{reels_path.name}, reel {reel_index} "
                            "is missing at least one payable symbol."
                        ),
                    )

    def test_read_reels_converts_symbol_names_to_read_only_ids(self) -> None:
        with TemporaryDirectory() as temporary_directory:
            directory = Path(temporary_directory)
            path = self._write_json(
                directory,
                {
                    "format_version": 1,
                    "number_of_reels": 2,
                    "reel_length": 3,
                    "reels": [
                        ["WILD", "A", "K"],
                        ["SCATTER", "Q", "J"],
                    ],
                },
            )

            reels = read_reels(path)

        self.assertEqual(len(reels), 2)
        np.testing.assert_array_equal(
            reels[0],
            np.asarray(
                [Symbol.WILD, Symbol.A, Symbol.K],
                dtype=np.int16,
            ),
        )
        np.testing.assert_array_equal(
            reels[1],
            np.asarray(
                [Symbol.SCATTER, Symbol.Q, Symbol.J],
                dtype=np.int16,
            ),
        )
        self.assertTrue(
            all(not reel.flags.writeable for reel in reels)
        )

    def test_read_reels_rejects_missing_file(self) -> None:
        with TemporaryDirectory() as temporary_directory:
            path = Path(temporary_directory) / "missing.json"

            with self.assertRaises(FileNotFoundError):
                read_reels(path)

    def test_read_reels_rejects_invalid_json(self) -> None:
        with TemporaryDirectory() as temporary_directory:
            path = Path(temporary_directory) / "reels.json"
            path.write_text("{not valid json", encoding="utf-8")

            with self.assertRaises(ValueError):
                read_reels(path)

    def test_read_reels_rejects_non_object_root(self) -> None:
        with TemporaryDirectory() as temporary_directory:
            path = self._write_json(
                Path(temporary_directory),
                [],
            )

            with self.assertRaises(ValueError):
                read_reels(path)

    def test_read_reels_rejects_unsupported_format(self) -> None:
        with TemporaryDirectory() as temporary_directory:
            path = self._write_json(
                Path(temporary_directory),
                {
                    "format_version": 2,
                    "number_of_reels": 1,
                    "reel_length": 1,
                    "reels": [["A"]],
                },
            )

            with self.assertRaises(ValueError):
                read_reels(path)

    def test_read_reels_rejects_declared_reel_count_mismatch(
        self,
    ) -> None:
        with TemporaryDirectory() as temporary_directory:
            path = self._write_json(
                Path(temporary_directory),
                {
                    "format_version": 1,
                    "number_of_reels": 2,
                    "reel_length": 1,
                    "reels": [["A"]],
                },
            )

            with self.assertRaises(ValueError):
                read_reels(path)

    def test_read_reels_rejects_declared_reel_length_mismatch(
        self,
    ) -> None:
        with TemporaryDirectory() as temporary_directory:
            path = self._write_json(
                Path(temporary_directory),
                {
                    "format_version": 1,
                    "number_of_reels": 1,
                    "reel_length": 2,
                    "reels": [["A"]],
                },
            )

            with self.assertRaises(ValueError):
                read_reels(path)

    def test_read_reels_rejects_non_string_symbol(self) -> None:
        with TemporaryDirectory() as temporary_directory:
            path = self._write_json(
                Path(temporary_directory),
                {
                    "format_version": 1,
                    "number_of_reels": 1,
                    "reel_length": 1,
                    "reels": [[1]],
                },
            )

            with self.assertRaises(ValueError):
                read_reels(path)

    def test_read_reels_rejects_unknown_symbol(self) -> None:
        with TemporaryDirectory() as temporary_directory:
            path = self._write_json(
                Path(temporary_directory),
                {
                    "format_version": 1,
                    "number_of_reels": 1,
                    "reel_length": 1,
                    "reels": [["UNKNOWN"]],
                },
            )

            with self.assertRaises(ValueError):
                read_reels(path)


class ReelGenerationTests(unittest.TestCase):
    def test_weighted_reel_generation_is_seeded_and_reproducible(
        self,
    ) -> None:
        probabilities = {
            Symbol.A: 2.0,
            Symbol.K: 1.0,
        }

        first = generate_weighted_reels(
            probabilities=probabilities,
            number_of_reels=3,
            reel_length=20,
            seed=123,
        )
        second = generate_weighted_reels(
            probabilities=probabilities,
            number_of_reels=3,
            reel_length=20,
            seed=123,
        )

        self.assertEqual(len(first), 3)

        for first_reel, second_reel in zip(first, second):
            self.assertEqual(first_reel.shape, (20,))
            self.assertEqual(first_reel.dtype, np.int16)
            self.assertTrue(
                set(map(int, first_reel)).issubset(
                    {int(Symbol.A), int(Symbol.K)}
                )
            )
            np.testing.assert_array_equal(
                first_reel,
                second_reel,
            )

    def test_relative_weights_are_normalized(self) -> None:
        reels = generate_weighted_reels(
            probabilities={Symbol.COIN: 7.0},
            number_of_reels=2,
            reel_length=10,
            seed=456,
        )

        for reel in reels:
            np.testing.assert_array_equal(
                reel,
                np.full(
                    10,
                    int(Symbol.COIN),
                    dtype=np.int16,
                ),
            )

    def test_invalid_generation_arguments_are_rejected(self) -> None:
        valid_probabilities = {Symbol.A: 1.0}

        with self.assertRaises(ValueError):
            generate_weighted_reels(
                valid_probabilities,
                number_of_reels=0,
            )

        with self.assertRaises(ValueError):
            generate_weighted_reels(
                valid_probabilities,
                reel_length=0,
            )

        with self.assertRaises(ValueError):
            generate_weighted_reels({})

        with self.assertRaises(ValueError):
            generate_weighted_reels({Symbol.A: -1.0})

        with self.assertRaises(ValueError):
            generate_weighted_reels({Symbol.A: np.inf})

        with self.assertRaises(ValueError):
            generate_weighted_reels(
                {
                    Symbol.A: 0.0,
                    Symbol.K: 0.0,
                }
            )

    def test_save_and_read_reels_round_trip(self) -> None:
        reels = (
            np.asarray(
                [Symbol.WILD, Symbol.A, Symbol.K],
                dtype=np.int16,
            ),
            np.asarray(
                [Symbol.SCATTER, Symbol.Q, Symbol.J],
                dtype=np.int16,
            ),
        )

        with TemporaryDirectory() as temporary_directory:
            path = (
                Path(temporary_directory)
                / "nested"
                / "reels.json"
            )
            save_reels(reels, path)
            loaded = read_reels(path)

        self.assertEqual(len(loaded), len(reels))

        for expected, actual in zip(reels, loaded):
            np.testing.assert_array_equal(actual, expected)
            self.assertFalse(actual.flags.writeable)

    def test_save_reels_rejects_invalid_geometry(self) -> None:
        with TemporaryDirectory() as temporary_directory:
            path = Path(temporary_directory) / "reels.json"

            with self.assertRaises(ValueError):
                save_reels((), path)

            with self.assertRaises(ValueError):
                save_reels(
                    (np.asarray([], dtype=np.int16),),
                    path,
                )

            with self.assertRaises(ValueError):
                save_reels(
                    (
                        np.asarray([0], dtype=np.int16),
                        np.asarray(
                            [0, 1],
                            dtype=np.int16,
                        ),
                    ),
                    path,
                )


if __name__ == "__main__":
    unittest.main()