from __future__ import annotations

from gui.pages.base_page import BasePage


class SlotPage(BasePage):
    """Main slot-game workspace."""

    def __init__(self) -> None:
        super().__init__(
            title="Slot",
            description=(
                "Inspect the current slot configuration and perform "
                "individual game actions."
            ),
        )

        self.add_placeholder(
            title="Slot workspace",
            description=(
                "The slot screen, spin controls, current bet, and "
                "game-state information will be added here."
            ),
        )