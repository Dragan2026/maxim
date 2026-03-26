#!/usr/bin/env python3
"""
Maxim — Penetration Testing Command Center for Kali Linux
"""

import sys
import os

def main():
    # Ensure we can import our package
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

    from PyQt5.QtWidgets import QApplication
    from PyQt5.QtCore import Qt
    from PyQt5.QtGui import QFont
    from maxim.gui.main_window import MaximWindow

    app = QApplication(sys.argv)
    app.setApplicationName("Maxim")
    app.setOrganizationName("Maxim")

    # Set default font
    font = QFont("JetBrains Mono", 11)
    font.setStyleHint(QFont.Monospace)
    app.setFont(font)

    window = MaximWindow()
    window.show()

    sys.exit(app.exec_())


if __name__ == "__main__":
    main()
