import unittest
from pathlib import Path

from config_loader import load_game


PROJECT_ROOT = Path(__file__).resolve().parents[1]
CONFIG_PATH = PROJECT_ROOT / "configs" / "analytics_playground.json"


class ConfigLoaderTests(unittest.TestCase):
    def test_example_configuration_loads(self) -> None:
        loaded = load_game(CONFIG_PATH)

        self.assertEqual(
            loaded.game.name,
            "Analytics Playground",
        )
        self.assertEqual(loaded.game.n_reels, 5)
        self.assertEqual(loaded.game.visible_rows, 3)
        self.assertEqual(
            loaded.game.window_offsets,
            (0, 1, 2),
        )

    def test_active_reel_set_is_loaded(self) -> None:
        loaded = load_game(CONFIG_PATH)

        self.assertEqual(
            loaded.game.reels[0][0],
            "A",
        )

    def test_payline_styles_are_loaded(self) -> None:
        loaded = load_game(CONFIG_PATH)

        self.assertEqual(
            loaded.ui.payline_styles["top"].color,
            "#FF0000",
        )


if __name__ == "__main__":
    unittest.main()