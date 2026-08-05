from __future__ import annotations

from gui.pages.base_page import BasePage


class PaytablePage(BasePage):
    """Page for displaying the current paytable."""

    def __init__(self) -> None:
        super().__init__(
            title="Paytable",
            description=(
                "Inspect payout multipliers for each payable symbol."
            ),
        )

        self.add_placeholder(
            title="Symbol multipliers",
            description=(
                "The table containing symbols and their multipliers for "
                "three, four, and five matching symbols will be added here."
            ),
        )