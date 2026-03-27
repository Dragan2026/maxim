"""
Maxim Modern Dark Theme — clean, minimal, professional.
"""

MAIN_STYLE = """
/* ── Global ── */
QWidget {
    background-color: #09090b;
    color: #e4e4e7;
    font-family: 'Inter', 'Segoe UI', 'Helvetica Neue', 'Arial', sans-serif;
    font-size: 16px;
}

QMainWindow {
    background-color: #09090b;
}

/* ── Menu Bar ── */
QMenuBar {
    background-color: #09090b;
    color: #a1a1aa;
    border-bottom: 1px solid #18181b;
    padding: 4px 8px;
    font-size: 15px;
}
QMenuBar::item {
    padding: 6px 14px;
    border-radius: 6px;
}
QMenuBar::item:selected {
    background-color: #27272a;
    color: #fafafa;
}
QMenu {
    background-color: #0c0c0f;
    border: 1px solid #27272a;
    border-radius: 8px;
    padding: 4px;
}
QMenu::item {
    padding: 8px 24px;
    border-radius: 4px;
    font-size: 15px;
}
QMenu::item:selected {
    background-color: #3b82f6;
    color: #ffffff;
}
QMenu::separator {
    height: 1px;
    background: #27272a;
    margin: 4px 8px;
}

/* ── Scroll Bars ── */
QScrollBar:vertical {
    background: transparent;
    width: 8px;
    border-radius: 4px;
}
QScrollBar::handle:vertical {
    background: #27272a;
    border-radius: 4px;
    min-height: 40px;
}
QScrollBar::handle:vertical:hover {
    background: #3f3f46;
}
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
    height: 0;
}
QScrollBar:horizontal {
    background: transparent;
    height: 8px;
    border-radius: 4px;
}
QScrollBar::handle:horizontal {
    background: #27272a;
    border-radius: 4px;
    min-width: 40px;
}

/* ── Splitter ── */
QSplitter::handle {
    background-color: #18181b;
}
QSplitter::handle:horizontal {
    width: 2px;
}

/* ── Tooltip ── */
QToolTip {
    background-color: #18181b;
    color: #fafafa;
    border: 1px solid #27272a;
    border-radius: 6px;
    padding: 6px 10px;
    font-size: 14px;
}

/* ── Combo Box ── */
QComboBox {
    background-color: #0c0c0f;
    border: 1px solid #27272a;
    border-radius: 8px;
    padding: 8px 14px;
    color: #fafafa;
    font-size: 15px;
}
QComboBox::drop-down {
    border: none;
    padding-right: 10px;
}
QComboBox QAbstractItemView {
    background-color: #0c0c0f;
    border: 1px solid #27272a;
    border-radius: 6px;
    selection-background-color: #3b82f6;
    outline: none;
}

/* ── Progress Bar ── */
QProgressBar {
    background-color: #18181b;
    border: none;
    border-radius: 6px;
    text-align: center;
    color: #fafafa;
    height: 8px;
}
QProgressBar::chunk {
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #3b82f6, stop:1 #8b5cf6);
    border-radius: 6px;
}

/* ── Status Bar ── */
QStatusBar {
    background-color: #09090b;
    color: #52525b;
    border-top: 1px solid #18181b;
    font-size: 13px;
}
"""
