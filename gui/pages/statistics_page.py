from __future__ import annotations

from gui.pages.base_page import BasePage


class StatisticsPage(BasePage):
    """Page for simulation results and game statistics."""

    def __init__(self) -> None:
        super().__init__(
            title="Statistics",
            description=(
                "Run simulations and inspect the resulting game metrics."
            ),
        )

        self.add_placeholder(
            title="Simulation statistics",
            description=(
                "RTP, hit frequency, variance, bonus frequency, confidence "
                "intervals, and related reports will be added here."
            ),
        )