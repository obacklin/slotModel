import random
import unittest

from game_config import GameConfig
from screen_generator import build_screen, sample_stops, spin


class ScreenGeneratorTests(unittest.TestCase):
    def setUp(self) -> None:
        self.config = GameConfig(
            reels=(
                ("A", "B", "C", "D"),
                ("E", "F", "G", "H"),
                ("I", "J", "K", "L"),
            ),
            visible_rows=3,
        )

    def test_build_screen_without_wraparound(self) -> None:
        screen = build_screen(self.config, (0, 1, 0))

        self.assertEqual(
            screen,
            (
                ("A", "F", "I"),
                ("B", "G", "J"),
                ("C", "H", "K"),
            ),
        )

    def test_build_screen_with_wraparound(self) -> None:
        screen = build_screen(self.config, (3, 3, 3))

        self.assertEqual(
            screen,
            (
                ("D", "H", "L"),
                ("A", "E", "I"),
                ("B", "F", "J"),
            ),
        )

    def test_wrong_number_of_stops_is_rejected(self) -> None:
        with self.assertRaises(ValueError):
            build_screen(self.config, (0, 1))

    def test_out_of_range_stop_is_rejected(self) -> None:
        with self.assertRaises(ValueError):
            build_screen(self.config, (0, 4, 0))

    def test_seeded_sampling_is_reproducible(self) -> None:
        rng_1 = random.Random(123)
        rng_2 = random.Random(123)

        sequence_1 = [
            sample_stops(self.config, rng_1)
            for _ in range(10)
        ]
        sequence_2 = [
            sample_stops(self.config, rng_2)
            for _ in range(10)
        ]

        self.assertEqual(sequence_1, sequence_2)

    def test_spin_screen_matches_its_stops(self) -> None:
        result = spin(self.config, random.Random(7))

        self.assertEqual(
            result.screen,
            build_screen(self.config, result.stops),
        )


if __name__ == "__main__":
    unittest.main()
