"""
Maxim Modern Dark Theme — clean, minimal, professional.
Uses Inter for UI, JetBrains Mono for terminal/code only.
"""

MAIN_STYLE = """
/* ── Global ── */
QWidget {
    background-color: #09090b;
    color: #e4e4e7;
    font-family: 'Inter', 'Segoe UI', 'Helvetica Neue', 'Arial', sans-serif;
    font-size: 15px;
}

QMainWindow {
    background-color: #09090b;
}

/* ── Menu Bar ── */
QMenuBar {
    background-color: #0c0c0f;
    color: #a1a1aa;
    border-bottom: 1px solid #18181b;
    padding: 4px 8px;
    font-size: 15px;
}
QMenuBar::item {
    padding: 4px 12px;
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
    padding: 6px 24px;
    border-radius: 4px;
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

/* ── Tabs ── */
QTabWidget::pane {
    border: none;
    background: #09090b;
}
QTabBar::tab {
    background: transparent;
    color: #71717a;
    padding: 10px 22px;
    border: none;
    border-bottom: 2px solid transparent;
    font-size: 15px;
    font-weight: 500;
}
QTabBar::tab:selected {
    color: #fafafa;
    border-bottom: 2px solid #3b82f6;
}
QTabBar::tab:hover {
    color: #d4d4d8;
    background: #18181b;
}

/* ── Buttons ── */
QPushButton {
    background-color: #3b82f6;
    color: #ffffff;
    border: none;
    border-radius: 8px;
    padding: 10px 20px;
    font-weight: 600;
    font-size: 15px;
}
QPushButton:hover {
    background-color: #60a5fa;
}
QPushButton:pressed {
    background-color: #2563eb;
}
QPushButton:disabled {
    background-color: #18181b;
    color: #3f3f46;
}
QPushButton#dangerBtn {
    background-color: #ef4444;
}
QPushButton#dangerBtn:hover {
    background-color: #f87171;
}
QPushButton#successBtn {
    background-color: #22c55e;
}
QPushButton#successBtn:hover {
    background-color: #4ade80;
}
QPushButton#ghostBtn {
    background-color: transparent;
    border: 1px solid #27272a;
    color: #a1a1aa;
    font-weight: 500;
}
QPushButton#ghostBtn:hover {
    border-color: #3b82f6;
    color: #3b82f6;
    background-color: #3b82f610;
}

/* ── Input Fields ── */
QLineEdit, QTextEdit, QPlainTextEdit {
    background-color: #0c0c0f;
    color: #fafafa;
    border: 1px solid #27272a;
    border-radius: 8px;
    padding: 10px 14px;
    font-size: 15px;
    selection-background-color: #3b82f6;
}
QLineEdit:focus, QTextEdit:focus, QPlainTextEdit:focus {
    border-color: #3b82f6;
    background-color: #111113;
}

/* ── Prompt Input ── */
QLineEdit#promptInput {
    background-color: #0c0c0f;
    border: 2px solid #27272a;
    border-radius: 12px;
    padding: 14px 18px;
    font-size: 17px;
    font-weight: 400;
    color: #fafafa;
}
QLineEdit#promptInput:focus {
    border-color: #3b82f6;
    background-color: #111113;
}

/* ── Terminal Output ── */
QPlainTextEdit#terminal {
    background-color: #000000;
    color: #4ade80;
    border: 1px solid #18181b;
    border-radius: 8px;
    padding: 12px;
    font-family: 'JetBrains Mono', 'Fira Code', 'Cascadia Code', 'Consolas', monospace;
    font-size: 14px;
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

/* ── Lists & Trees ── */
QListWidget, QTreeWidget, QTableWidget {
    background-color: #0c0c0f;
    border: 1px solid #18181b;
    border-radius: 8px;
    outline: none;
    font-size: 13px;
}
QListWidget::item, QTreeWidget::item {
    padding: 8px 12px;
    border-radius: 6px;
}
QListWidget::item:selected, QTreeWidget::item:selected {
    background-color: #1e3a5f;
    color: #60a5fa;
}
QListWidget::item:hover, QTreeWidget::item:hover {
    background-color: #18181b;
}
QHeaderView::section {
    background-color: #0c0c0f;
    color: #71717a;
    border: 1px solid #18181b;
    padding: 8px;
    font-weight: 600;
}

/* ── Combo Box ── */
QComboBox {
    background-color: #0c0c0f;
    border: 1px solid #27272a;
    border-radius: 8px;
    padding: 8px 14px;
    color: #fafafa;
    font-size: 13px;
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

/* ── Splitter ── */
QSplitter::handle {
    background-color: #18181b;
}
QSplitter::handle:horizontal {
    width: 1px;
}
QSplitter::handle:vertical {
    height: 1px;
}

/* ── Group Box ── */
QGroupBox {
    border: 1px solid #27272a;
    border-radius: 10px;
    margin-top: 14px;
    padding-top: 20px;
    font-weight: 600;
    color: #60a5fa;
    font-size: 14px;
}
QGroupBox::title {
    subcontrol-origin: margin;
    left: 14px;
    padding: 0 8px;
}

/* ── Labels ── */
QLabel#heading {
    color: #fafafa;
    font-size: 22px;
    font-weight: 700;
}
QLabel#subheading {
    color: #71717a;
    font-size: 14px;
    font-weight: 400;
}
QLabel#accent {
    color: #3b82f6;
    font-weight: 600;
}
QLabel#success {
    color: #4ade80;
}
QLabel#warning {
    color: #facc15;
}
QLabel#error {
    color: #f87171;
}

/* ── Tool Cards ── */
QFrame#toolCard {
    background-color: #0c0c0f;
    border: 1px solid #18181b;
    border-radius: 12px;
    padding: 14px;
}
QFrame#toolCard:hover {
    border-color: #3b82f6;
    background-color: #111113;
}

/* ── Status Bar ── */
QStatusBar {
    background-color: #0c0c0f;
    color: #71717a;
    border-top: 1px solid #18181b;
    font-size: 12px;
}

/* ── Tooltip ── */
QToolTip {
    background-color: #18181b;
    color: #fafafa;
    border: 1px solid #27272a;
    border-radius: 6px;
    padding: 6px 10px;
    font-size: 12px;
}

/* ── Sidebar ── */
QFrame#sidebar {
    background-color: #0c0c0f;
    border-right: 1px solid #18181b;
}

/* ── AI Chat ── */
QTextBrowser {
    background-color: #000000;
    border: 1px solid #18181b;
    border-radius: 8px;
    padding: 12px;
    font-size: 13px;
}
"""
