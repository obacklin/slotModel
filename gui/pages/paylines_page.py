from __future__ import annotations

from gui.pages.base_page import BasePage


class PaylinesPage(BasePage):
    """Page for inspecting the configured paylines."""

    def __init__(self) -> None:
        super().__init__(
            title="Paylines",
            description=(
                "Inspect the paylines used by the current game configuration."
            ),
        )

        self.add_placeholder(
            title="Payline definitions",
            description=(
                "Payline paths, row indices, and graphical previews will "
                "be added here."
            ),
        )