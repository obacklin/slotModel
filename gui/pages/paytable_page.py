from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import(
    QAbstractItemView,
    QFrame,
    QHeaderView,
    QLabel,
    QSizePolicy,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout
)

from gui.pages.base_page import BasePage
from slotmodel.runtime_tools import PaylineEvaluatorProfile
from slotmodel.sim.paytable import Paytable
from slotmodel.sim.reels import Symbol

class PaytablePage(BasePage):
    """Page for displaying the configured paytable."""

    def __init__(self, evaluator_profile: PaylineEvaluatorProfile) -> None:
        super().__init__(
            title="Paytable",
            description=(
                "Inspect the payout multipliers for each symbol."
            ),
            expand_body=True
        )

        self._evaluator_profile = evaluator_profile
        table_card = self._create_table_card(evaluator_profile.paytable)

        self.body_layout.addWidget(
            table_card,
            stretch=1,
        )

    def _create_table_card(
        self,
        paytable: Paytable,
    ) -> QFrame:
        """Create the card containing the paytable."""
        card = QFrame()
        card.setObjectName("contentCard")
        card.setSizePolicy(
            QSizePolicy.Policy.Expanding,
            QSizePolicy.Policy.Expanding,
        )

        layout = QVBoxLayout(card)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(14)

        card_title = QLabel(
            f"Symbol multipliers · {self._evaluator_profile.label}"
        )
        card_title.setObjectName("cardTitle")

        card_description = QLabel(
            "Payout values are multipliers of the configured bet. "
            f"Backend paytable: {self._evaluator_profile.paytable_name}; "
            f"evaluator key: {self._evaluator_profile.name}."
        )
        card_description.setWordWrap(True)
        card_description.setObjectName("cardDescription")

        self.paytable_table = self._create_paytable_table(
            paytable
        )

        layout.addWidget(card_title)
        layout.addWidget(card_description)
        layout.addSpacing(6)
        layout.addWidget(
            self.paytable_table,
            stretch=1,
        )

        return card

    def _create_paytable_table(
        self,
        paytable: Paytable,
    ) -> QTableWidget:
        """Create a read-only table from the backend paytable."""
        match_counts = tuple(
            range(
                paytable.minimum_match_count,
                paytable.reel_count + 1,
            )
        )

        table = QTableWidget(
            len(paytable.entries),
            len(match_counts) + 1,
        )
        table.setObjectName("paytableTable")
        table.setSizePolicy(
            QSizePolicy.Policy.Expanding,
            QSizePolicy.Policy.Expanding,
        )

        table.setHorizontalHeaderLabels(
            [
                "Symbol",
                *[
                    f"{match_count} Matches"
                    for match_count in match_counts
                ],
            ]
        )

        for row, entry in enumerate(paytable.entries):
            symbol_item = QTableWidgetItem(
                self._format_symbol_name(entry.symbol)
            )
            symbol_item.setTextAlignment(
                Qt.AlignmentFlag.AlignVCenter
                | Qt.AlignmentFlag.AlignLeft
            )
            table.setItem(row, 0, symbol_item)

            for column, multiplier in enumerate(
                entry.multipliers,
                start=1,
            ):
                multiplier_item = QTableWidgetItem(
                    f"{multiplier:g}×"
                )
                multiplier_item.setTextAlignment(
                    Qt.AlignmentFlag.AlignCenter
                )
                table.setItem(
                    row,
                    column,
                    multiplier_item,
                )

        self._configure_table_behavior(table)
        self._configure_table_headers(table)

        return table

    @staticmethod
    def _format_symbol_name(symbol: Symbol) -> str:
        """Convert enum names into display-friendly text."""
        return symbol.name.replace("_", " ").title()

    @staticmethod
    def _configure_table_behavior(
        table: QTableWidget,
    ) -> None:
        """Configure editing, selection, and scrolling."""
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
        """Configure the table headers and column sizing."""
        vertical_header = table.verticalHeader()
        vertical_header.setVisible(False)
        vertical_header.setDefaultSectionSize(42)

        horizontal_header = table.horizontalHeader()
        horizontal_header.setHighlightSections(False)

        horizontal_header.setSectionResizeMode(
            0,
            QHeaderView.ResizeMode.Stretch,
        )

        for column in range(1, table.columnCount()):
            horizontal_header.setSectionResizeMode(
                column,
                QHeaderView.ResizeMode.Stretch,
            )