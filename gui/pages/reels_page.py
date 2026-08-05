from __future__ import annotations

from gui.pages.base_page import BasePage


class ReelsPage(BasePage):
    """Page for inspecting and configuring reel strips."""

    def __init__(self) -> None:
        super().__init__(
            title="Reels",
            description=(
                "Inspect the active reel set and its symbol distribution."
            ),
        )

        self.add_placeholder(
            title="Reel configuration",
            description=(
                "Reel-strip contents, symbol counts, reel lengths, and "
                "reel validation controls will be added here."
            ),
        )