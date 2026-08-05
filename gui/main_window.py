from __future__ import annotations

from PySide6.QtCore import Qt, Slot
from PySide6.QtWidgets import (
    QButtonGroup,
    QFrame,
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QPushButton,
    QSizePolicy,
    QSpacerItem,
    QStackedWidget,
    QVBoxLayout,
    QWidget,
)

from gui.pages import (
    PaylinesPage,
    PaytablePage,
    ReelsPage,
    SlotPage,
    StatisticsPage,
)


class MainWindow(QMainWindow):
    """Main application shell containing navigation and content pages."""

    def __init__(self) -> None:
        super().__init__()

        self._navigation_buttons: dict[str, QPushButton] = {}

        self._configure_window()
        self._build_interface()

    def _configure_window(self) -> None:
        """Configure the operating-system window."""
        self.setWindowTitle("Slot Model")
        self.resize(1100, 720)
        self.setMinimumSize(850, 550)

    def _build_interface(self) -> None:
        """Create the sidebar and page area."""
        root_widget = QWidget()

        root_layout = QHBoxLayout(root_widget)
        root_layout.setContentsMargins(0, 0, 0, 0)
        root_layout.setSpacing(0)

        self.page_stack = self._create_page_stack()
        sidebar = self._create_sidebar()

        root_layout.addWidget(sidebar)
        root_layout.addWidget(self.page_stack, stretch=1)

        self.setCentralWidget(root_widget)
        self.statusBar().showMessage("Ready")

    def _create_page_stack(self) -> QStackedWidget:
        """Create and populate the application's content-page stack."""
        page_stack = QStackedWidget()
        page_stack.setObjectName("pageStack")

        self._pages = (
            SlotPage(),
            ReelsPage(),
            PaytablePage(),
            PaylinesPage(),
            StatisticsPage(),
        )

        for page in self._pages:
            page_stack.addWidget(page)

        page_stack.setCurrentIndex(0)

        return page_stack

    def _create_sidebar(self) -> QFrame:
        """Create the left-hand navigation sidebar."""
        sidebar = QFrame()
        sidebar.setObjectName("sidebar")
        sidebar.setFixedWidth(230)

        layout = QVBoxLayout(sidebar)
        layout.setContentsMargins(22, 28, 22, 22)
        layout.setSpacing(8)

        application_title = QLabel("SLOT MODEL")
        application_title.setObjectName("applicationTitle")

        application_subtitle = QLabel("Simulation workspace")
        application_subtitle.setObjectName("applicationSubtitle")

        layout.addWidget(application_title)
        layout.addWidget(application_subtitle)
        layout.addSpacing(32)

        navigation_heading = QLabel("WORKSPACE")
        navigation_heading.setObjectName("navigationHeading")

        layout.addWidget(navigation_heading)
        layout.addSpacing(4)

        self.navigation_group = QButtonGroup(self)
        self.navigation_group.setExclusive(True)

        page_names = (
            "Slot",
            "Reels",
            "Paytable",
            "Paylines",
            "Statistics",
        )

        for page_index, page_name in enumerate(page_names):
            button = self._create_navigation_button(
                text=page_name,
                page_index=page_index,
            )

            self._navigation_buttons[page_name] = button
            layout.addWidget(button)

        self._navigation_buttons["Slot"].setChecked(True)

        layout.addItem(
            QSpacerItem(
                0,
                0,
                QSizePolicy.Policy.Minimum,
                QSizePolicy.Policy.Expanding,
            )
        )

        version_label = QLabel("Development interface")
        version_label.setObjectName("applicationSubtitle")
        layout.addWidget(version_label)

        return sidebar

    def _create_navigation_button(
        self,
        text: str,
        page_index: int,
    ) -> QPushButton:
        """Create a button that displays one page in the content area."""
        button = QPushButton(text)
        button.setObjectName("navigationButton")
        button.setCheckable(True)
        button.setCursor(Qt.CursorShape.PointingHandCursor)

        button.clicked.connect(
            lambda checked=False, index=page_index: self._show_page(index)
        )

        self.navigation_group.addButton(button)

        return button

    @Slot(int)
    def _show_page(self, page_index: int) -> None:
        """Display the selected content page."""
        if not 0 <= page_index < self.page_stack.count():
            raise IndexError(
                f"Page index {page_index} is outside the page stack."
            )

        self.page_stack.setCurrentIndex(page_index)

        page_name = tuple(self._navigation_buttons)[page_index]
        self.statusBar().showMessage(
            f"{page_name} page selected.",
            2000,
        )