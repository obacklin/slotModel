from __future__ import annotations

from PySide6.QtCore import Qt, Slot
from PySide6.QtWidgets import (
    QButtonGroup,
    QComboBox,
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
from slotmodel.runtime_tools import (
    PAYLINE_EVALUATOR_PROFILES,
    discover_reel_profiles,
)


class MainWindow(QMainWindow):
    """Main application shell containing navigation and content pages."""

    _REEL_PROFILE_PAGE_INDICES = (0, 1, 4)
    _PAYTABLE_PAGE_INDICES = (0, 2)

    def __init__(self) -> None:
        super().__init__()

        self._navigation_buttons: dict[str, QPushButton] = {}
        self._profiles = discover_reel_profiles()
        self._active_profile = self._profiles[0]
        self._payline_evaluator_profiles = PAYLINE_EVALUATOR_PROFILES
        self._active_payline_evaluator_profile = self._payline_evaluator_profiles[0]

        self._configure_window()
        self._build_interface()

    def _configure_window(self) -> None:
        """Configure the operating-system window."""
        self.setWindowTitle("OB SlotModel")
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
        self.statusBar().showMessage(
            "Ready · "
            f"{self._active_profile.label} reels · "
            f"{self._active_payline_evaluator_profile.label} paytable"
        )

    def _create_page_stack(self) -> QStackedWidget:
        """Create and populate the application's content-page stack."""
        page_stack = QStackedWidget()
        page_stack.setObjectName("pageStack")

        self._pages: list[QWidget] = [
            SlotPage(
                self._active_profile,
                self._active_payline_evaluator_profile,
            ),
            ReelsPage(self._active_profile),
            PaytablePage(self._active_payline_evaluator_profile),
            PaylinesPage(),
            StatisticsPage(self._active_profile),
        ]

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

        application_title = QLabel("SlotModel")
        application_title.setObjectName("applicationTitle")

        layout.addWidget(application_title)
        layout.addSpacing(24)

        profile_heading = QLabel("REEL PROFILE")
        profile_heading.setObjectName("navigationHeading")
        layout.addWidget(profile_heading)

        self._profile_combo = QComboBox()
        self._profile_combo.setObjectName("profileCombo")
        for profile in self._profiles:
            suffix = "" if profile.has_report else " · no report"
            self._profile_combo.addItem(profile.label + suffix)
        self._profile_combo.setCurrentIndex(0)
        self._profile_combo.currentIndexChanged.connect(self._change_profile)
        layout.addWidget(self._profile_combo)

        layout.addSpacing(12)

        paytable_heading = QLabel("PAYTABLE")
        paytable_heading.setObjectName("navigationHeading")
        layout.addWidget(paytable_heading)

        self._paytable_combo = QComboBox()
        self._paytable_combo.setObjectName("paytableCombo")
        for evaluator_profile in self._payline_evaluator_profiles:
            self._paytable_combo.addItem(evaluator_profile.label)
        self._paytable_combo.setCurrentIndex(0)
        self._paytable_combo.currentIndexChanged.connect(self._change_paytable)
        layout.addWidget(self._paytable_combo)

        layout.addSpacing(24)

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

    def _replace_pages(self, replacements: dict[int, QWidget]) -> None:
        current_page_index = self.page_stack.currentIndex()

        for page_index, new_page in replacements.items():
            old_page = self.page_stack.widget(page_index)
            self.page_stack.removeWidget(old_page)
            self.page_stack.insertWidget(page_index, new_page)
            old_page.deleteLater()
            self._pages[page_index] = new_page

        self.page_stack.setCurrentIndex(current_page_index)

    @Slot(int)
    def _change_profile(self, profile_index: int) -> None:
        """Rebuild reel-dependent pages for the selected reel profile."""
        if not 0 <= profile_index < len(self._profiles):
            return

        profile = self._profiles[profile_index]
        if profile == self._active_profile:
            return

        self._active_profile = profile
        evaluator_profile = self._active_payline_evaluator_profile

        self._replace_pages({
            0: SlotPage(profile, evaluator_profile),
            1: ReelsPage(profile),
            4: StatisticsPage(profile),
        })

        self.statusBar().showMessage(
            f"Active reel profile changed to {profile.label}.",
            3000,
        )

    @Slot(int)
    def _change_paytable(self, paytable_index: int) -> None:
        """Rebuild paytable-dependent pages and compile a fresh evaluator."""
        if not 0 <= paytable_index < len(self._payline_evaluator_profiles):
            return

        evaluator_profile = self._payline_evaluator_profiles[paytable_index]
        if evaluator_profile == self._active_payline_evaluator_profile:
            return

        self._active_payline_evaluator_profile = evaluator_profile

        self._replace_pages({
            0: SlotPage(self._active_profile, evaluator_profile),
            2: PaytablePage(evaluator_profile),
        })

        self.statusBar().showMessage(
            "Active paytable changed to "
            f"{evaluator_profile.label}; payline evaluator recompiled.",
            3000,
        )

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
            f"{page_name} page selected · "
            f"{self._active_profile.label} reels · "
            f"{self._active_payline_evaluator_profile.label} paytable.",
            2000,
        )