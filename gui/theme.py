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