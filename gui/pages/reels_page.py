from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QAbstractItemView,
    QFrame,
    QHeaderView,
    QLabel,
    QSizePolicy,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
)

from gui.pages.base_page import BasePage
from slotmodel.runtime_tools import ReelProfile
from slotmodel.sim.reels import ReelSet, Symbol, read_reels


class ReelsPage(BasePage):
    """Page for inspecting the configured reel strips."""

    def __init__(self, profile: ReelProfile) -> None:
        super().__init__(
            title="Reels",
            description=(
                "Inspect the symbols and stop positions in the "
                "currently configured reel set."
            ),
            expand_body=True
        )

        try:
            reels = read_reels(profile.reels_path)
        except (OSError, ValueError) as error:
            self.add_placeholder(
                title="Unable to load reels",
                description=str(error),
            )
            return

        table_card = self._create_table_card(reels, profile)

        self.body_layout.addWidget(
            table_card,
            stretch=1,
        )

    def _create_table_card(
        self,
        reels: ReelSet,
        profile: ReelProfile,
    ) -> QFrame:
        """Create the card containing the reel table."""
        reel_count = len(reels)
        reel_length = reels[0].size

        card = QFrame()
        card.setObjectName("contentCard")
        card.setSizePolicy(
            QSizePolicy.Policy.Expanding,
            QSizePolicy.Policy.Expanding,
        )

        layout = QVBoxLayout(card)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(14)

        card_title = QLabel(f"Active reel set · {profile.label}")
        card_title.setObjectName("cardTitle")

        summary_label = QLabel(
            f"{reel_count} reels · "
            f"{reel_length} stops per reel"
        )
        summary_label.setObjectName("cardDescription")

        self.reels_table = self._create_reels_table(reels)

        layout.addWidget(card_title)
        layout.addWidget(summary_label)
        layout.addSpacing(6)
        layout.addWidget(
            self.reels_table,
            stretch=1,
        )

        return card

    def _create_reels_table(
        self,
        reels: ReelSet,
    ) -> QTableWidget:
        """Create a read-only table containing all reel symbols."""
        reel_count = len(reels)
        reel_length = reels[0].size

        table = QTableWidget(
            reel_length,
            reel_count + 1,
        )
        table.setObjectName("reelsTable")

        column_headers = [
            "Stop index",
            *[
                f"Reel {reel_index}"
                for reel_index in range(1, reel_count + 1)
            ],
        ]
        table.setHorizontalHeaderLabels(column_headers)

        for stop_index in range(reel_length):
            stop_item = QTableWidgetItem(str(stop_index))
            stop_item.setTextAlignment(
                Qt.AlignmentFlag.AlignCenter
            )
            table.setItem(stop_index, 0, stop_item)

            for reel_index, reel in enumerate(reels):
                symbol_id = int(reel[stop_index])
                symbol = Symbol(symbol_id)

                symbol_item = QTableWidgetItem(
                    self._format_symbol_name(symbol)
                )
                symbol_item.setTextAlignment(
                    Qt.AlignmentFlag.AlignCenter
                )

                table.setItem(
                    stop_index,
                    reel_index + 1,
                    symbol_item,
                )

        self._configure_table_behavior(table)
        self._configure_table_headers(table)

        table.setSizePolicy(
            QSizePolicy.Policy.Expanding,
            QSizePolicy.Policy.Expanding
        )

        return table

    @staticmethod
    def _format_symbol_name(symbol: Symbol) -> str:
        """Convert an enum symbol into a display-friendly name."""
        return symbol.name.replace("_", " ").title()

    @staticmethod
    def _configure_table_behavior(
        table: QTableWidget,
    ) -> None:
        """Configure selection, scrolling, and editing behavior."""
        table.setEditTriggers(
            QAbstractItemView.EditTrigger.NoEditTriggers
        )
        table.setSelectionBehavior(
            QAbstractItemView.SelectionBehavior.SelectRows
        )
        table.setSelectionMode(
            QAbstractItemView.SelectionMode.SingleSelection
        )

        table.setVerticalScrollMode(
            QAbstractItemView.ScrollMode.ScrollPerPixel
        )
        table.setHorizontalScrollMode(
            QAbstractItemView.ScrollMode.ScrollPerPixel
        )

        table.setAlternatingRowColors(True)
        table.setShowGrid(False)
        table.setWordWrap(False)
        table.setSortingEnabled(False)
        table.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        table.setCornerButtonEnabled(False)

    @staticmethod
    def _configure_table_headers(
        table: QTableWidget,
    ) -> None:
        """Configure row and column header sizing."""
        vertical_header = table.verticalHeader()
        vertical_header.setVisible(False)
        vertical_header.setDefaultSectionSize(38)

        horizontal_header = table.horizontalHeader()
        horizontal_header.setHighlightSections(False)

        horizontal_header.setSectionResizeMode(
            0,
            QHeaderView.ResizeMode.ResizeToContents,
        )

        for column in range(1, table.columnCount()):
            horizontal_header.setSectionResizeMode(
                column,
                QHeaderView.ResizeMode.Stretch,
            )