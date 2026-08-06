from __future__ import annotations

from collections.abc import Iterable

from PySide6.QtCore import (
    QSignalBlocker,
    Qt,
)
from PySide6.QtGui import (
    QIcon,
    QPainter,
    QPen,
    QPixmap,
)
from PySide6.QtWidgets import (
    QAbstractItemView,
    QFrame,
    QHBoxLayout,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QPushButton,
    QSizePolicy,
    QVBoxLayout,
)

from gui.pages.base_page import BasePage
from gui.widgets.payline_screen_widget import (
    PaylineScreenWidget,
)
from slotmodel.sim.paylines.paylines import (
    PAYLINES,
)
from slotmodel.sim.reels import Symbol


VISUALIZATION_SCREEN = (
    (
        Symbol.WILD,
        Symbol.JEWEL,
        Symbol.CASTLE,
        Symbol.CHEST,
        Symbol.COIN,
    ),
    (
        Symbol.KNIGHT,
        Symbol.A,
        Symbol.K,
        Symbol.Q,
        Symbol.J,
    ),
    (
        Symbol.PAWN,
        Symbol.SCATTER,
        Symbol.JEWEL,
        Symbol.A,
        Symbol.WILD,
    ),
)


class PaylinesPage(BasePage):
    """Page for inspecting the configured payline geometry."""

    def __init__(self) -> None:
        super().__init__(
            title="Paylines",
            description=(
                "Inspect how each configured "
                "payline crosses the game screen."
            ),
            expand_body=True,
        )

        self._payline_list = QListWidget()
        self._visible_count_label = QLabel()

        self._screen = (
            PaylineScreenWidget(
                row_count=(
                    PAYLINES.row_count
                ),
                reel_count=(
                    PAYLINES.reel_count
                ),
                paylines=PAYLINES.lines,
            )
        )

        self._screen.set_screen(
            VISUALIZATION_SCREEN
        )

        content_card = (
            self._create_content_card()
        )

        self.body_layout.addWidget(
            content_card,
            stretch=1,
        )

        self._populate_payline_list()
        self._connect_signals()

        self._payline_list.setCurrentRow(
            0
        )
        self._set_checked_indices((0,))

    def _create_content_card(
        self,
    ) -> QFrame:
        card = QFrame()
        card.setObjectName(
            "contentCard"
        )
        card.setSizePolicy(
            QSizePolicy.Policy.Expanding,
            QSizePolicy.Policy.Expanding,
        )

        card_layout = QVBoxLayout(card)
        card_layout.setContentsMargins(
            24,
            24,
            24,
            24,
        )
        card_layout.setSpacing(14)

        card_title = QLabel(
            "Configured paylines"
        )
        card_title.setObjectName(
            "cardTitle"
        )

        card_description = QLabel(
            "Select paylines on the left "
            "to draw them over the fixed "
            "5 x 3 visualisation screen."
        )
        card_description.setObjectName(
            "cardDescription"
        )
        card_description.setWordWrap(
            True
        )

        page_content_layout = (
            QHBoxLayout()
        )
        page_content_layout.setContentsMargins(
            0,
            6,
            0,
            0,
        )
        page_content_layout.setSpacing(
            20
        )

        page_content_layout.addWidget(
            self._create_controls_panel()
        )
        page_content_layout.addWidget(
            self._screen,
            stretch=1,
        )

        card_layout.addWidget(card_title)
        card_layout.addWidget(
            card_description
        )
        card_layout.addLayout(
            page_content_layout,
            stretch=1,
        )

        return card

    def _create_controls_panel(
        self,
    ) -> QFrame:
        panel = QFrame()
        panel.setObjectName(
            "paylineControlsPanel"
        )
        panel.setMinimumWidth(255)
        panel.setMaximumWidth(320)
        panel.setSizePolicy(
            QSizePolicy.Policy.Preferred,
            QSizePolicy.Policy.Expanding,
        )

        panel_layout = QVBoxLayout(
            panel
        )
        panel_layout.setContentsMargins(
            14,
            14,
            14,
            14,
        )
        panel_layout.setSpacing(10)

        instruction_label = QLabel(
            "Check one or more lines. "
            "The selected row is emphasized "
            "on the screen."
        )
        instruction_label.setObjectName(
            "paylineInstruction"
        )
        instruction_label.setWordWrap(
            True
        )

        self._payline_list.setObjectName(
            "paylineList"
        )
        self._payline_list.setSelectionMode(
            QAbstractItemView.SelectionMode.SingleSelection
        )
        self._payline_list.setAlternatingRowColors(
            True
        )
        self._payline_list.setVerticalScrollMode(
            QAbstractItemView.ScrollMode.ScrollPerPixel
        )

        button_layout = QHBoxLayout()
        button_layout.setContentsMargins(
            0,
            0,
            0,
            0,
        )
        button_layout.setSpacing(8)

        selected_button = QPushButton(
            "Selected"
        )
        selected_button.setObjectName(
            "primaryButton"
        )
        selected_button.clicked.connect(
            self._show_selected_only
        )

        show_all_button = QPushButton(
            "All"
        )
        show_all_button.setObjectName(
            "paylineSecondaryButton"
        )
        show_all_button.clicked.connect(
            self._show_all
        )

        clear_button = QPushButton(
            "Clear"
        )
        clear_button.setObjectName(
            "paylineSecondaryButton"
        )
        clear_button.clicked.connect(
            self._clear_all
        )

        button_layout.addWidget(
            selected_button
        )
        button_layout.addWidget(
            show_all_button
        )
        button_layout.addWidget(
            clear_button
        )

        self._visible_count_label.setObjectName(
            "paylineStatusLabel"
        )

        panel_layout.addWidget(
            instruction_label
        )
        panel_layout.addWidget(
            self._payline_list,
            stretch=1,
        )
        panel_layout.addLayout(
            button_layout
        )
        panel_layout.addWidget(
            self._visible_count_label
        )

        panel.setStyleSheet(
            """
            QFrame#paylineControlsPanel {
                background-color: #24272c;
                border: 1px solid #383c43;
                border-radius: 9px;
            }

            QLabel#paylineInstruction,
            QLabel#paylineStatusLabel {
                background-color: transparent;
                color: #aeb4bd;
            }

            QListWidget#paylineList {
                background-color: #202327;
                alternate-background-color: #25282d;
                color: #e6e8eb;
                border: 1px solid #383c43;
                border-radius: 7px;
                outline: none;
            }

            QListWidget#paylineList::item {
                min-height: 34px;
                padding: 3px 8px;
                border-bottom: 1px solid #30343a;
            }

            QListWidget#paylineList::item:selected {
                background-color: #3b4266;
                color: #ffffff;
            }

            QPushButton#paylineSecondaryButton {
                background-color: #30343a;
                color: #d9dce1;
                border: 1px solid #444951;
            }

            QPushButton#paylineSecondaryButton:hover {
                background-color: #393e45;
            }

            QPushButton#paylineSecondaryButton:pressed {
                background-color: #2a2e34;
            }
            """
        )

        return panel

    def _populate_payline_list(
        self,
    ) -> None:
        blocker = QSignalBlocker(
            self._payline_list
        )

        for (
            line_index,
            rows,
        ) in enumerate(PAYLINES.lines):
            displayed_rows = "–".join(
                str(row_index + 1)
                for row_index in rows
            )

            item = QListWidgetItem(
                self._payline_icon(
                    line_index
                ),
                (
                    f"Line "
                    f"{line_index + 1:02d}"
                    f"    {displayed_rows}"
                ),
            )

            item.setData(
                Qt.ItemDataRole.UserRole,
                line_index,
            )

            item.setFlags(
                item.flags()
                | Qt.ItemFlag.ItemIsUserCheckable
            )

            item.setCheckState(
                Qt.CheckState.Unchecked
            )

            item.setToolTip(
                "Rows by reel: "
                + ", ".join(
                    str(row_index + 1)
                    for row_index in rows
                )
            )

            self._payline_list.addItem(
                item
            )

        del blocker

    def _connect_signals(
        self,
    ) -> None:
        self._payline_list.itemChanged.connect(
            self._sync_visible_paylines
        )

        self._payline_list.currentRowChanged.connect(
            self._on_current_row_changed
        )

        self._payline_list.itemDoubleClicked.connect(
            lambda _item: (
                self._show_selected_only()
            )
        )

    def _payline_icon(
        self,
        line_index: int,
    ) -> QIcon:
        pixmap = QPixmap(16, 16)

        pixmap.fill(
            Qt.GlobalColor.transparent
        )

        painter = QPainter(pixmap)
        painter.setRenderHint(
            QPainter.RenderHint.Antialiasing,
            True,
        )
        painter.setPen(
            QPen(
                Qt.GlobalColor.black,
                1,
            )
        )
        painter.setBrush(
            self._screen.payline_color(
                line_index
            )
        )
        painter.drawEllipse(
            2,
            2,
            12,
            12,
        )
        painter.end()

        return QIcon(pixmap)

    def _checked_indices(
        self,
    ) -> set[int]:
        checked_indices: set[int] = set()

        for row_index in range(
            self._payline_list.count()
        ):
            item = self._payline_list.item(
                row_index
            )

            if (
                item.checkState()
                == Qt.CheckState.Checked
            ):
                checked_indices.add(
                    int(
                        item.data(
                            Qt.ItemDataRole.UserRole
                        )
                    )
                )

        return checked_indices

    def _set_checked_indices(
        self,
        indices: Iterable[int],
    ) -> None:
        checked_indices = {
            int(index)
            for index in indices
        }

        blocker = QSignalBlocker(
            self._payline_list
        )

        for row_index in range(
            self._payline_list.count()
        ):
            item = self._payline_list.item(
                row_index
            )

            payline_index = int(
                item.data(
                    Qt.ItemDataRole.UserRole
                )
            )

            state = (
                Qt.CheckState.Checked
                if payline_index
                in checked_indices
                else Qt.CheckState.Unchecked
            )

            item.setCheckState(state)

        del blocker

        self._sync_visible_paylines()

    def _sync_visible_paylines(
        self,
        _item: (
            QListWidgetItem | None
        ) = None,
    ) -> None:
        visible_indices = (
            self._checked_indices()
        )

        self._screen.show_paylines(
            visible_indices
        )

        self._visible_count_label.setText(
            "Visible paylines: "
            f"{len(visible_indices)} / "
            f"{len(PAYLINES.lines)}"
        )

    def _on_current_row_changed(
        self,
        row_index: int,
    ) -> None:
        highlighted_index = (
            row_index
            if row_index >= 0
            else None
        )

        self._screen.set_highlighted_payline(
            highlighted_index
        )

    def _show_selected_only(
        self,
    ) -> None:
        selected_row = (
            self._payline_list.currentRow()
        )

        if selected_row >= 0:
            self._set_checked_indices(
                (selected_row,)
            )

    def _show_all(self) -> None:
        self._set_checked_indices(
            range(
                self._payline_list.count()
            )
        )

    def _clear_all(self) -> None:
        self._set_checked_indices(())