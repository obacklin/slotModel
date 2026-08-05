from __future__ import annotations

from PySide6.QtWidgets import (
    QFrame,
    QLabel,
    QVBoxLayout,
    QWidget,
)


class BasePage(QWidget):
    """Base layout shared by the application's content pages."""

    def __init__(
        self,
        title: str,
        description: str,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)

        self.setObjectName("contentArea")

        self._layout = QVBoxLayout(self)
        self._layout.setContentsMargins(40, 34, 40, 34)
        self._layout.setSpacing(10)

        page_title = QLabel(title)
        page_title.setObjectName("pageTitle")

        page_description = QLabel(description)
        page_description.setObjectName("pageDescription")
        page_description.setWordWrap(True)

        self._layout.addWidget(page_title)
        self._layout.addWidget(page_description)
        self._layout.addSpacing(22)

        self.body_layout = QVBoxLayout()
        self.body_layout.setSpacing(14)

        self._layout.addLayout(self.body_layout)
        self._layout.addStretch()

    def add_placeholder(
        self,
        title: str,
        description: str,
    ) -> QFrame:
        """Add a temporary card to the page."""
        card = QFrame()
        card.setObjectName("contentCard")

        card_layout = QVBoxLayout(card)
        card_layout.setContentsMargins(24, 24, 24, 24)
        card_layout.setSpacing(12)

        card_title = QLabel(title)
        card_title.setObjectName("cardTitle")

        card_description = QLabel(description)
        card_description.setObjectName("cardDescription")
        card_description.setWordWrap(True)

        card_layout.addWidget(card_title)
        card_layout.addWidget(card_description)

        self.body_layout.addWidget(card)

        return card