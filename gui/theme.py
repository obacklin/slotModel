from __future__ import annotations


DARK_THEME = """
/* ---------------------------------------------------------
   Application defaults
   --------------------------------------------------------- */

QWidget {
    background-color: #202225;
    color: #e6e8eb;
    font-size: 14px;
}

QMainWindow {
    background-color: #181a1d;
}


/* ---------------------------------------------------------
   Sidebar
   --------------------------------------------------------- */

QFrame#sidebar {
    background-color: #181a1d;
    border-right: 1px solid #30343a;
}

QLabel#applicationTitle {
    color: #f4f5f7;
    font-size: 20px;
    font-weight: 700;
}

QLabel#applicationSubtitle {
    color: #8d949e;
    font-size: 12px;
}

QLabel#navigationHeading {
    color: #777e88;
    font-size: 11px;
    font-weight: 700;
}

QPushButton#navigationButton {
    background-color: transparent;
    color: #9299a3;
    border: none;
    border-radius: 7px;
    min-height: 40px;
    padding: 0 12px;
    text-align: left;
    font-weight: 500;
}

QPushButton#navigationButton:hover {
    background-color: #282b30;
    color: #d9dce1;
}

QPushButton#navigationButton:checked {
    background-color: #34383f;
    color: #f3f4f6;
    font-weight: 600;
}

QPushButton#navigationButton:pressed {
    background-color: #2e3238;
}

QStackedWidget#pageStack {
    background-color: #202225;
    border: none;
}




/* ---------------------------------------------------------
   Runtime selectors
   --------------------------------------------------------- */

QComboBox#profileCombo,
QComboBox#paytableCombo {
    background-color: #24272c;
    color: #e6e8eb;
    border: 1px solid #3b3f46;
    border-radius: 7px;
    min-height: 36px;
    padding: 0 10px;
}

QComboBox#profileCombo:hover,
QComboBox#paytableCombo:hover {
    border-color: #555b65;
}

QComboBox#profileCombo::drop-down,
QComboBox#paytableCombo::drop-down {
    border: none;
    width: 24px;
}

QComboBox#profileCombo QAbstractItemView,
QComboBox#paytableCombo QAbstractItemView {
    background-color: #24272c;
    color: #e6e8eb;
    border: 1px solid #3b3f46;
    selection-background-color: #3b4266;
    selection-color: #ffffff;
}


/* ---------------------------------------------------------
   Main content
   --------------------------------------------------------- */

QWidget#contentArea {
    background-color: #202225;
}

QLabel#pageTitle {
    color: #f4f5f7;
    font-size: 26px;
    font-weight: 700;
}

QLabel#pageDescription {
    color: #9ca3ad;
    font-size: 14px;
}

QFrame#contentCard {
    background-color: #292c31;
    border: 1px solid #383c43;
    border-radius: 12px;
}

/* The Slot page uses a borderless workspace instead of contentCard. */
QFrame#slotWorkspace {
    background-color: transparent;
    border: none;
}

/* The animation parent paints the single common 5 x 3 frame itself. */
QWidget#animatedSlotScreen {
    background-color: transparent;
    border: none;
}

/* Reel children are transparent painters, not cards or symbol boxes. */
QWidget#animatedReel {
    background-color: transparent;
    border: none;
}

QGraphicsView#scalableSlotView {
    background-color: transparent;
    border: none;
}

QLabel#cardTitle {
    background-color: transparent;
    color: #f2f3f5;
    font-size: 17px;
    font-weight: 600;
}

QLabel#cardDescription {
    background-color: transparent;
    color: #9da3ac;
}

QLabel#statusLabel {
    background-color: #22252a;
    color: #aeb4bd;
    border: 1px solid #373b42;
    border-radius: 7px;
    padding: 10px 12px;
}

QLabel#payoutDisplay {
    background-color: #22252a;
    color: #f2c14e;
    border: 1px solid #5f5331;
    border-radius: 7px;
    padding: 9px 12px;
    font-size: 16px;
    font-weight: 700;
}

QWidget#slotGroup,
QWidget#slotControlPanel,
QWidget#winningPaylineOverlay {
    background-color: transparent;
    border: none;
}

QLabel#freeSpinsDisplay,
QLabel#scatterCountDisplay {
    background-color: #22252a;
    color: #e5c76b;
    border: 1px solid #5f5331;
    border-radius: 7px;
    padding: 9px 12px;
    font-weight: 700;
}

QCheckBox#autoSpinCheckbox {
    background-color: #24272c;
    color: #c5cad1;
    border: 1px solid #454a52;
    border-radius: 7px;
    padding: 0 12px;
    spacing: 8px;
    min-height: 36px;
    font-weight: 600;
}

QCheckBox#autoSpinCheckbox:hover {
    background-color: #2b2e34;
    border-color: #5b616b;
    color: #e6e8eb;
}

QCheckBox#autoSpinCheckbox:checked {
    background-color: #3b4266;
    color: #ffffff;
    border: 1px solid #6672e5;
}

QCheckBox#autoSpinCheckbox:checked:hover {
    background-color: #454d78;
    border-color: #7883eb;
}

QCheckBox#autoSpinCheckbox:disabled {
    background-color: #2b2e32;
    color: #777d86;
    border-color: #3d4148;
}

QCheckBox#autoSpinCheckbox:checked:disabled {
    background-color: #34394f;
    color: #858b9a;
    border-color: #484f72;
}


/* ---------------------------------------------------------
   Buttons
   --------------------------------------------------------- */

QPushButton {
    min-height: 38px;
    padding: 0 18px;
    border-radius: 7px;
    font-weight: 600;
}

QPushButton#primaryButton {
    background-color: #5965d8;
    color: #ffffff;
    border: 1px solid #6672e5;
}

QPushButton#primaryButton:hover {
    background-color: #6874e6;
    border-color: #7883eb;
}

QPushButton#primaryButton:pressed {
    background-color: #4d58c4;
    border-color: #5964d1;
}

QPushButton#primaryButton:disabled {
    background-color: #3d4148;
    color: #777d86;
    border-color: #484d55;
}

QPushButton#bonusButton {
    background-color: #332f22;
    color: #e5c76b;
    border: 1px solid #8f7935;
}

QPushButton#bonusButton:hover {
    background-color: #403a27;
    color: #f0d77f;
    border-color: #b49a45;
}

QPushButton#bonusButton:pressed {
    background-color: #2b281d;
    border-color: #806c2f;
}

QPushButton#bonusButton:disabled {
    background-color: #3d4148;
    color: #777d86;
    border-color: #484d55;
}

/* ---------------------------------------------------------
   Reel table
   --------------------------------------------------------- */

QTableWidget#reelsTable {
    background-color: #24272c;
    alternate-background-color: #292c31;
    color: #e6e8eb;

    border: 1px solid #383c43;
    border-radius: 8px;

    selection-background-color: #3b4266;
    selection-color: #ffffff;
}

QTableWidget#reelsTable::item {
    border: none;
    border-bottom: 1px solid #30343a;
    padding: 7px 10px;
}

QTableWidget#reelsTable::item:hover {
    background-color: #31353b;
}

QTableWidget#reelsTable::item:selected {
    background-color: #3b4266;
    color: #ffffff;
}

QTableWidget#reelsTable QHeaderView::section {
    background-color: #1f2226;
    color: #aeb4bd;

    border: none;
    border-bottom: 1px solid #3b3f46;

    padding: 10px 12px;
    font-weight: 600;
}

/* ---------------------------------------------------------
   Paytable
   --------------------------------------------------------- */

QTableWidget#paytableTable {
    background-color: #24272c;
    alternate-background-color: #292c31;
    color: #e6e8eb;

    border: 1px solid #383c43;
    border-radius: 8px;

    selection-background-color: #3b4266;
    selection-color: #ffffff;
}

QTableWidget#paytableTable::item {
    border: none;
    border-bottom: 1px solid #30343a;
    padding: 8px 12px;
}

QTableWidget#paytableTable::item:hover {
    background-color: #31353b;
}

QTableWidget#paytableTable::item:selected {
    background-color: #3b4266;
    color: #ffffff;
}

QTableWidget#paytableTable QHeaderView::section {
    background-color: #1f2226;
    color: #aeb4bd;

    border: none;
    border-bottom: 1px solid #3b3f46;

    padding: 10px 12px;
    font-weight: 600;
}



/* ---------------------------------------------------------
   Statistics
   --------------------------------------------------------- */

QScrollArea#statisticsScrollArea,
QWidget#statisticsContent {
    background-color: transparent;
    border: none;
}

QFrame#metricCard {
    background-color: #24272c;
    border: 1px solid #383c43;
    border-radius: 8px;
}

QLabel#metricValue {
    background-color: transparent;
    color: #f2f3f5;
    font-size: 17px;
    font-weight: 700;
}

QLabel#metricLabel {
    background-color: transparent;
    color: #9299a3;
    font-size: 12px;
}

QTableWidget#statisticsTable {
    background-color: #24272c;
    alternate-background-color: #292c31;
    color: #e6e8eb;
    border: 1px solid #383c43;
    border-radius: 8px;
}

QTableWidget#statisticsTable::item {
    border: none;
    border-bottom: 1px solid #30343a;
    padding: 6px 10px;
}

QTableWidget#statisticsTable QHeaderView::section {
    background-color: #1f2226;
    color: #aeb4bd;
    border: none;
    border-bottom: 1px solid #3b3f46;
    padding: 9px 10px;
    font-weight: 600;
}


/* ---------------------------------------------------------
   Scrollbars
   --------------------------------------------------------- */

QScrollBar:vertical {
    background-color: #202328;
    width: 12px;
    margin: 0;
}

QScrollBar::handle:vertical {
    background-color: #4a4f58;
    min-height: 30px;
    margin: 2px;
    border-radius: 5px;
}

QScrollBar::handle:vertical:hover {
    background-color: #5a606a;
}

QScrollBar::add-line:vertical,
QScrollBar::sub-line:vertical {
    height: 0;
    border: none;
    background: none;
}

QScrollBar:horizontal {
    background-color: #202328;
    height: 12px;
    margin: 0;
}

QScrollBar::handle:horizontal {
    background-color: #4a4f58;
    min-width: 30px;
    margin: 2px;
    border-radius: 5px;
}

QScrollBar::handle:horizontal:hover {
    background-color: #5a606a;
}

QScrollBar::add-line:horizontal,
QScrollBar::sub-line:horizontal {
    width: 0;
    border: none;
    background: none;
}


/* ---------------------------------------------------------
   Status bar
   --------------------------------------------------------- */

QStatusBar {
    background-color: #181a1d;
    color: #8e959f;
    border-top: 1px solid #30343a;
}

QStatusBar::item {
    border: none;
}


/* ---------------------------------------------------------
   Tooltips
   --------------------------------------------------------- */

QToolTip {
    background-color: #30343a;
    color: #f2f3f5;
    border: 1px solid #484d55;
    padding: 5px;
}
"""