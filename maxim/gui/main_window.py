"""
Maxim Main Window — the primary GUI interface.
"""

import os
import re
import webbrowser
import threading
from datetime import datetime
from functools import partial

from PyQt5.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QTabWidget,
    QPlainTextEdit, QLineEdit, QPushButton, QLabel, QListWidget,
    QListWidgetItem, QSplitter, QFrame, QComboBox, QGroupBox,
    QGridLayout, QScrollArea, QMessageBox, QStatusBar, QAction,
    QMenu, QMenuBar, QProgressBar, QTextBrowser, QDialog, QDialogButtonBox,
    QApplication, QInputDialog,
)
from PyQt5.QtCore import Qt, QThread, pyqtSignal, QTimer, QSize
from PyQt5.QtGui import QFont, QColor, QTextCursor, QIcon, QPalette

from maxim.gui.styles import MAIN_STYLE
from maxim.core.engine import ProcessRunner, Session, ToolInstaller
from maxim.core.ai_assistant import OllamaAI, OnlineAI, AIManager, SmartRouter, PROVIDERS, get_api_key, set_api_key
from maxim.core.updater import check_for_update, perform_update, get_current_version
from maxim.core.workflows import (
    PHASES, ONLINE_RESOURCES, NATURAL_COMMANDS, get_phase, get_all_phases
)
from maxim.tools.tool_registry import (
    TOOLS, TOOL_CATEGORIES, get_tool_by_name,
    find_tools_by_keywords, get_all_packages
)


class OutputSignal(QThread):
    """Thread-safe signal for streaming output to terminal."""
    line_received = pyqtSignal(str)
    finished = pyqtSignal(int, float)

    def __init__(self, runner, cmd, as_root=False):
        super().__init__()
        self.runner = runner
        self.cmd = cmd
        self.as_root = as_root

    def run(self):
        exit_code, output, duration = self.runner.run(
            self.cmd, self.as_root,
            callback=lambda line: self.line_received.emit(line)
        )
        self.finished.emit(exit_code, duration)


class AIStreamSignal(QThread):
    token_received = pyqtSignal(str)
    finished = pyqtSignal(str)

    def __init__(self, ai_manager, message):
        super().__init__()
        self.ai = ai_manager
        self.message = message

    def run(self):
        try:
            response = self.ai.chat(self.message, stream_callback=lambda t: self.token_received.emit(t))
            self.finished.emit(response)
        except Exception as e:
            self.finished.emit(f"[Error] {e}")


class ToolChoiceDialog(QDialog):
    def __init__(self, tools, description, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Choose Tool")
        self.setMinimumWidth(450)
        self.setStyleSheet(MAIN_STYLE)
        self.chosen = None

        layout = QVBoxLayout(self)
        lbl = QLabel(f"Multiple tools can handle: <b>{description}</b><br>"
                     f"<span style='color:#8b949e;'>Which one would you like to use?</span>")
        lbl.setWordWrap(True)
        layout.addWidget(lbl)

        self.list = QListWidget()
        for t in tools:
            root_tag = " [ROOT]" if t.get("needs_root") else ""
            item = QListWidgetItem(f"  {t['name']}{root_tag}  --  {t['description']}")
            item.setData(Qt.UserRole, t["name"])
            self.list.addItem(item)
        self.list.setCurrentRow(0)
        layout.addWidget(self.list)

        btns = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        btns.accepted.connect(self.accept)
        btns.rejected.connect(self.reject)
        layout.addWidget(btns)

    def accept(self):
        item = self.list.currentItem()
        if item:
            self.chosen = item.data(Qt.UserRole)
        super().accept()


class MaximWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("MAXIM -- Penetration Testing Command Center")
        self.setMinimumSize(1280, 800)
        self.setStyleSheet(MAIN_STYLE)

        self.runner = ProcessRunner()
        self.session = Session()
        self.ai = AIManager()
        self.current_thread = None

        self._build_ui()
        self._build_menu()
        self._update_status()

    # ═══════════════════════════════════════
    #  UI CONSTRUCTION
    # ═══════════════════════════════════════

    def _build_ui(self):
        central = QWidget()
        self.setCentralWidget(central)
        root = QVBoxLayout(central)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        # ── Header ──
        header = QFrame()
        header.setFixedHeight(56)
        header.setStyleSheet("background-color: #0d1117; border-bottom: 2px solid #1a8cff;")
        hlay = QHBoxLayout(header)
        hlay.setContentsMargins(16, 0, 16, 0)

        logo = QLabel("MAXIM")
        logo.setStyleSheet("color: #1a8cff; font-size: 24px; font-weight: bold; letter-spacing: 6px;")
        hlay.addWidget(logo)

        sep = QLabel("|")
        sep.setStyleSheet("color: #30363d; font-size: 24px; margin: 0 10px;")
        hlay.addWidget(sep)

        subtitle = QLabel("Penetration Testing Command Center")
        subtitle.setStyleSheet("color: #8b949e; font-size: 13px;")
        hlay.addWidget(subtitle)
        hlay.addStretch()

        self.ai_status = QLabel()
        hlay.addWidget(self.ai_status)

        root.addWidget(header)

        # ── Body ──
        body = QSplitter(Qt.Horizontal)

        # Sidebar
        sidebar = QFrame()
        sidebar.setObjectName("sidebar")
        sidebar.setFixedWidth(240)
        slay = QVBoxLayout(sidebar)
        slay.setContentsMargins(8, 12, 8, 12)

        # Phase navigation
        phase_label = QLabel("PENTEST PHASES")
        phase_label.setStyleSheet("color: #484f58; font-size: 10px; font-weight: bold; letter-spacing: 3px; margin-bottom: 4px;")
        slay.addWidget(phase_label)

        self.phase_list = QListWidget()
        self.phase_list.setFrameShape(QFrame.NoFrame)
        self.phase_list.setStyleSheet("""
            QListWidget { background: transparent; border: none; }
            QListWidget::item { padding: 10px 12px; border-radius: 6px; margin: 2px 0; font-size: 13px; }
            QListWidget::item:selected { background: #1a3a5c; color: #58a6ff; }
            QListWidget::item:hover { background: #161b22; }
        """)
        for phase in PHASES:
            item = QListWidgetItem(f" {phase['icon']}  {phase['name']}")
            item.setData(Qt.UserRole, phase["id"])
            self.phase_list.addItem(item)
        self.phase_list.currentItemChanged.connect(self._on_phase_select)
        slay.addWidget(self.phase_list)

        # Divider
        div1 = QFrame()
        div1.setFixedHeight(1)
        div1.setStyleSheet("background: #1a1f29; margin: 8px 0;")
        slay.addWidget(div1)

        # Tool categories
        cat_label = QLabel("TOOL CATEGORIES")
        cat_label.setStyleSheet("color: #484f58; font-size: 10px; font-weight: bold; letter-spacing: 3px; margin-bottom: 4px;")
        slay.addWidget(cat_label)

        self.cat_list = QListWidget()
        self.cat_list.setFrameShape(QFrame.NoFrame)
        self.cat_list.setMaximumHeight(200)
        self.cat_list.setStyleSheet("""
            QListWidget { background: transparent; border: none; }
            QListWidget::item { padding: 6px 12px; border-radius: 6px; margin: 1px 0; font-size: 12px; }
            QListWidget::item:selected { background: #1a3a5c; color: #58a6ff; }
            QListWidget::item:hover { background: #161b22; }
        """)
        for cat_id, cat in TOOL_CATEGORIES.items():
            item = QListWidgetItem(f"  {cat['name']}")
            item.setData(Qt.UserRole, cat_id)
            self.cat_list.addItem(item)
        self.cat_list.currentItemChanged.connect(self._on_category_select)
        slay.addWidget(self.cat_list)

        slay.addStretch()

        # Online resources button
        online_btn = QPushButton("Online Resources")
        online_btn.setObjectName("ghostBtn")
        online_btn.clicked.connect(lambda: self.tabs.setCurrentIndex(4))
        slay.addWidget(online_btn)

        self.stats_label = QLabel("Session: 0 commands")
        self.stats_label.setStyleSheet("color: #484f58; font-size: 11px; padding: 8px;")
        slay.addWidget(self.stats_label)

        body.addWidget(sidebar)

        # ── Tabs ──
        self.tabs = QTabWidget()
        self.tabs.setDocumentMode(True)

        self.tabs.addTab(self._build_prompt_tab(), "  Command Center  ")
        self.tabs.addTab(self._build_workflow_tab(), "  Workflows  ")
        self.tabs.addTab(self._build_tools_tab(), "  Tools  ")
        self.tabs.addTab(self._build_ai_tab(), "  AI Assistant  ")
        self.tabs.addTab(self._build_online_tab(), "  Online  ")
        self.tabs.addTab(self._build_log_tab(), "  Log  ")

        body.addWidget(self.tabs)
        body.setSizes([240, 1040])
        root.addWidget(body)

        self.statusBar().showMessage("Ready -- Type a command or select a workflow phase")

    # ── Tab: Command Center ──
    def _build_prompt_tab(self):
        w = QWidget()
        lay = QVBoxLayout(w)
        lay.setContentsMargins(16, 16, 16, 16)
        lay.setSpacing(12)

        # Prompt
        prompt_frame = QFrame()
        prompt_frame.setStyleSheet("""
            QFrame { background: #0d1117; border: 1px solid #1a1f29; border-radius: 12px; padding: 8px; }
        """)
        play = QVBoxLayout(prompt_frame)

        hint = QLabel("Type naturally -- Maxim knows which tool and CLI command to use.")
        hint.setStyleSheet("color: #58a6ff; font-size: 12px; margin-bottom: 2px;")
        play.addWidget(hint)

        examples = QLabel(
            '<span style="color:#484f58;">Examples: </span>'
            '<span style="color:#8b949e;">"scan network 192.168.1.0/24" | '
            '"put wlan1 in monitor mode" | "find directories on target.com" | '
            '"install nmap" | "crack this hash" | "who is on my network"</span>'
        )
        examples.setStyleSheet("font-size: 11px; margin-bottom: 4px;")
        examples.setWordWrap(True)
        play.addWidget(examples)

        input_row = QHBoxLayout()
        self.prompt_input = QLineEdit()
        self.prompt_input.setObjectName("promptInput")
        self.prompt_input.setPlaceholderText("What do you want to do?...")
        self.prompt_input.returnPressed.connect(self._on_prompt_submit)
        input_row.addWidget(self.prompt_input)

        self.run_btn = QPushButton("Execute")
        self.run_btn.setFixedWidth(100)
        self.run_btn.setFixedHeight(42)
        self.run_btn.clicked.connect(self._on_prompt_submit)
        input_row.addWidget(self.run_btn)

        self.stop_btn = QPushButton("Stop")
        self.stop_btn.setObjectName("dangerBtn")
        self.stop_btn.setFixedWidth(70)
        self.stop_btn.setFixedHeight(42)
        self.stop_btn.clicked.connect(self._on_stop)
        self.stop_btn.setEnabled(False)
        input_row.addWidget(self.stop_btn)

        play.addLayout(input_row)
        lay.addWidget(prompt_frame)

        # Suggestion area
        self.suggestion_frame = QFrame()
        self.suggestion_frame.setStyleSheet("""
            QFrame { background: #161b22; border: 1px solid #30363d; border-radius: 8px; padding: 10px; }
        """)
        self.suggestion_frame.setVisible(False)
        self.suggestion_layout = QVBoxLayout(self.suggestion_frame)
        self.suggestion_label = QLabel()
        self.suggestion_label.setWordWrap(True)
        self.suggestion_layout.addWidget(self.suggestion_label)
        self.cmd_buttons_layout = QHBoxLayout()
        self.suggestion_layout.addLayout(self.cmd_buttons_layout)
        lay.addWidget(self.suggestion_frame)

        # Terminal
        self.terminal = QPlainTextEdit()
        self.terminal.setObjectName("terminal")
        self.terminal.setReadOnly(True)
        self.terminal.setFont(QFont("JetBrains Mono", 11))
        self.terminal.setPlaceholderText("Output will appear here...")
        lay.addWidget(self.terminal, stretch=1)

        # Quick actions
        qbar = QHBoxLayout()
        for label, cmd in [
            ("My IP", "ip -c addr show"),
            ("Interfaces", "airmon-ng 2>/dev/null; iwconfig 2>/dev/null"),
            ("Ports", "ss -tlnp"),
            ("Processes", "ps aux --sort=-%mem | head -20"),
            ("LAN Scan", "sudo nmap -sn 192.168.1.0/24"),
            ("Routing", "ip route show"),
            ("DNS", "cat /etc/resolv.conf"),
        ]:
            btn = QPushButton(label)
            btn.setObjectName("ghostBtn")
            btn.setFixedHeight(30)
            btn.clicked.connect(partial(self._execute_command, cmd))
            qbar.addWidget(btn)
        qbar.addStretch()
        lay.addLayout(qbar)

        return w

    # ── Tab: Workflows ──
    def _build_workflow_tab(self):
        w = QWidget()
        lay = QVBoxLayout(w)
        lay.setContentsMargins(0, 0, 0, 0)

        # Top: workflow content (scrollable)
        self.workflow_scroll = QScrollArea()
        self.workflow_scroll.setWidgetResizable(True)
        self.workflow_scroll.setFrameShape(QFrame.NoFrame)

        self.workflow_container = QWidget()
        self.workflow_layout = QVBoxLayout(self.workflow_container)
        self.workflow_layout.setContentsMargins(16, 16, 16, 16)
        self.workflow_layout.setSpacing(12)

        # Default: show all phases overview
        self._show_phases_overview()

        self.workflow_scroll.setWidget(self.workflow_container)
        lay.addWidget(self.workflow_scroll)

        return w

    def _show_phases_overview(self):
        self._clear_layout(self.workflow_layout)

        title = QLabel("Pentest Workflow Phases")
        title.setObjectName("heading")
        self.workflow_layout.addWidget(title)

        desc = QLabel("Select a phase from the sidebar, or click below to see step-by-step suggestions with recommended tools and online resources.")
        desc.setObjectName("subheading")
        desc.setWordWrap(True)
        self.workflow_layout.addWidget(desc)

        grid = QGridLayout()
        grid.setSpacing(12)
        col = 0
        row = 0
        for phase in PHASES:
            card = QFrame()
            card.setObjectName("toolCard")
            card.setCursor(Qt.PointingHandCursor)
            card.setFixedHeight(140)
            clay = QVBoxLayout(card)

            icon_name = QLabel(f'<span style="font-size:28px;">{phase["icon"]}</span>  '
                              f'<span style="color:{phase["color"]};font-size:17px;font-weight:bold;">{phase["name"]}</span>')
            clay.addWidget(icon_name)

            d = QLabel(phase["description"])
            d.setStyleSheet("color: #8b949e; font-size: 12px;")
            d.setWordWrap(True)
            clay.addWidget(d)

            steps_count = len(phase["steps"])
            total_cmds = sum(len(s["suggestions"]) for s in phase["steps"])
            total_online = sum(len(s.get("online_tools", [])) for s in phase["steps"])
            meta = QLabel(f'{steps_count} steps | {total_cmds} commands | {total_online} online tools')
            meta.setStyleSheet(f"color: {phase['color']}; font-size: 11px;")
            clay.addWidget(meta)

            clay.addStretch()

            btn = QPushButton(f"Open {phase['name']}")
            btn.setFixedHeight(30)
            btn.clicked.connect(partial(self._show_phase_detail, phase["id"]))
            clay.addWidget(btn)

            grid.addWidget(card, row, col)
            col += 1
            if col >= 3:
                col = 0
                row += 1

        self.workflow_layout.addLayout(grid)
        self.workflow_layout.addStretch()

    def _show_phase_detail(self, phase_id):
        phase = get_phase(phase_id)
        if not phase:
            return

        self._clear_layout(self.workflow_layout)

        # Back button
        back_btn = QPushButton("< Back to Overview")
        back_btn.setObjectName("ghostBtn")
        back_btn.setFixedWidth(180)
        back_btn.clicked.connect(self._show_phases_overview)
        self.workflow_layout.addWidget(back_btn)

        # Phase header
        header = QLabel(f'<span style="font-size:28px;">{phase["icon"]}</span>  '
                       f'<span style="color:{phase["color"]};font-size:22px;font-weight:bold;">{phase["name"]}</span>')
        self.workflow_layout.addWidget(header)

        desc = QLabel(phase["description"])
        desc.setObjectName("subheading")
        desc.setWordWrap(True)
        self.workflow_layout.addWidget(desc)

        # Steps
        for i, step in enumerate(phase["steps"]):
            step_group = QGroupBox(f"Step {i+1}: {step['name']}")
            step_group.setStyleSheet(f"""
                QGroupBox {{
                    border: 1px solid {phase['color']}40;
                    border-radius: 10px;
                    margin-top: 14px;
                    padding-top: 18px;
                    font-weight: bold;
                    color: {phase['color']};
                    font-size: 14px;
                }}
                QGroupBox::title {{ subcontrol-origin: margin; left: 14px; padding: 0 8px; }}
            """)
            slay = QVBoxLayout(step_group)

            sdesc = QLabel(step["description"])
            sdesc.setStyleSheet("color: #8b949e; font-size: 12px; margin-bottom: 6px;")
            slay.addWidget(sdesc)

            # CLI suggestions
            cli_label = QLabel('<span style="color:#3fb950;font-weight:bold;">CLI Commands:</span>')
            slay.addWidget(cli_label)

            for sug in step["suggestions"]:
                row = QHBoxLayout()

                tool_tag = QLabel(f'<span style="color:#58a6ff;background:#1a3a5c;padding:2px 8px;border-radius:4px;font-size:11px;">{sug["tool"]}</span>')
                row.addWidget(tool_tag)

                desc_lbl = QLabel(f'<span style="color:#c5c8c6;">{sug["desc"]}</span>')
                desc_lbl.setMinimumWidth(250)
                row.addWidget(desc_lbl)

                cmd_lbl = QLabel(f'<code style="color:#33ff33;font-size:11px;">{sug["cmd"]}</code>')
                cmd_lbl.setTextInteractionFlags(Qt.TextSelectableByMouse)
                row.addWidget(cmd_lbl, stretch=1)

                run_btn = QPushButton("Run")
                run_btn.setFixedSize(60, 28)
                run_btn.clicked.connect(partial(self._run_workflow_cmd, sug["cmd"], sug["tool"]))
                row.addWidget(run_btn)

                slay.addLayout(row)

            # Online tools
            online = step.get("online_tools", [])
            if online:
                slay.addSpacing(8)
                online_label = QLabel('<span style="color:#d29922;font-weight:bold;">Online Tools:</span>')
                slay.addWidget(online_label)

                orow = QHBoxLayout()
                for ot in online:
                    obtn = QPushButton(f"{ot['name']}")
                    obtn.setToolTip(f"{ot['desc']}\n{ot['url']}")
                    obtn.setObjectName("ghostBtn")
                    obtn.setFixedHeight(28)
                    obtn.setStyleSheet("""
                        QPushButton { border: 1px solid #d29922; color: #d29922; border-radius: 4px; padding: 2px 10px; font-size: 11px; }
                        QPushButton:hover { background: #2d1f00; }
                    """)
                    url = ot["url"]
                    obtn.clicked.connect(partial(self._open_online_tool, url))
                    orow.addWidget(obtn)
                orow.addStretch()
                slay.addLayout(orow)

            self.workflow_layout.addWidget(step_group)

        self.workflow_layout.addStretch()

        # Switch to workflow tab
        self.tabs.setCurrentIndex(1)

    def _run_workflow_cmd(self, cmd_template, tool_name):
        """Fill placeholders and run a workflow command."""
        cmd = self._fill_placeholders(cmd_template)
        if cmd:
            self.tabs.setCurrentIndex(0)
            needs_root = False
            tool = get_tool_by_name(tool_name)
            if tool:
                needs_root = tool.get("needs_root", False)
            self._execute_command(cmd, as_root=needs_root)

    def _open_online_tool(self, url_template):
        """Open online tool — prompt for target if URL has placeholder."""
        if "{target}" in url_template or "{domain}" in url_template:
            target, ok = QInputDialog.getText(
                self, "Target", "Enter target (domain or IP):",
                QLineEdit.Normal, ""
            )
            if not ok or not target:
                return
            url = url_template.replace("{target}", target).replace("{domain}", target)
        else:
            url = url_template
        webbrowser.open(url)

    # ── Tab: Tools ──
    def _build_tools_tab(self):
        w = QWidget()
        lay = QVBoxLayout(w)
        lay.setContentsMargins(16, 16, 16, 16)

        search_row = QHBoxLayout()
        self.tool_search = QLineEdit()
        self.tool_search.setPlaceholderText("Search tools...")
        self.tool_search.textChanged.connect(self._filter_tools)
        search_row.addWidget(self.tool_search)

        install_all_btn = QPushButton("Install All Tools")
        install_all_btn.setObjectName("successBtn")
        install_all_btn.clicked.connect(self._install_all_tools)
        search_row.addWidget(install_all_btn)
        lay.addLayout(search_row)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)

        self.tools_container = QWidget()
        self.tools_grid = QGridLayout(self.tools_container)
        self.tools_grid.setSpacing(10)
        self._populate_tools_grid()

        scroll.setWidget(self.tools_container)
        lay.addWidget(scroll)
        return w

    # ── Tab: AI Assistant ──
    def _build_ai_tab(self):
        w = QWidget()
        lay = QVBoxLayout(w)
        lay.setContentsMargins(16, 16, 16, 16)

        # Provider row
        prov_row = QHBoxLayout()
        prov_row.addWidget(QLabel("Provider:"))
        self.provider_combo = QComboBox()
        self.provider_combo.setMinimumWidth(180)
        for pid, prov in PROVIDERS.items():
            tag = "LOCAL" if prov["type"] == "local" else "ONLINE"
            self.provider_combo.addItem(f"{prov['name']}  [{tag}]", pid)
        # Set current
        idx = list(PROVIDERS.keys()).index(self.ai.active_provider) if self.ai.active_provider in PROVIDERS else 0
        self.provider_combo.setCurrentIndex(idx)
        self.provider_combo.currentIndexChanged.connect(self._on_provider_change)
        prov_row.addWidget(self.provider_combo)

        prov_row.addWidget(QLabel("Model:"))
        self.model_combo = QComboBox()
        self.model_combo.setMinimumWidth(220)
        self._refresh_models()
        self.model_combo.currentIndexChanged.connect(self._on_model_change)
        prov_row.addWidget(self.model_combo)

        self.api_key_btn = QPushButton("API Key")
        self.api_key_btn.setObjectName("ghostBtn")
        self.api_key_btn.setToolTip("Set API key for online provider")
        self.api_key_btn.clicked.connect(self._set_api_key)
        prov_row.addWidget(self.api_key_btn)

        refresh_btn = QPushButton("Refresh")
        refresh_btn.setObjectName("ghostBtn")
        refresh_btn.clicked.connect(self._refresh_models)
        prov_row.addWidget(refresh_btn)

        clear_btn = QPushButton("Clear Chat")
        clear_btn.setObjectName("ghostBtn")
        clear_btn.clicked.connect(self._clear_ai_chat)
        prov_row.addWidget(clear_btn)

        prov_row.addStretch()

        # Status indicator
        self.ai_provider_status = QLabel()
        prov_row.addWidget(self.ai_provider_status)
        self._update_ai_provider_status()

        lay.addLayout(prov_row)

        # Info bar for online providers
        self.ai_info_bar = QFrame()
        self.ai_info_bar.setStyleSheet("""
            QFrame { background: #161b22; border: 1px solid #30363d; border-radius: 6px; padding: 6px 12px; }
        """)
        info_lay = QHBoxLayout(self.ai_info_bar)
        info_lay.setContentsMargins(8, 4, 8, 4)
        self.ai_info_label = QLabel()
        self.ai_info_label.setWordWrap(True)
        self.ai_info_label.setStyleSheet("font-size: 11px;")
        info_lay.addWidget(self.ai_info_label)
        self.ai_get_key_btn = QPushButton("Get API Key")
        self.ai_get_key_btn.setStyleSheet("QPushButton { border: 1px solid #d29922; color: #d29922; border-radius: 4px; padding: 4px 10px; font-size: 11px; } QPushButton:hover { background: #2d1f00; }")
        self.ai_get_key_btn.clicked.connect(self._open_key_url)
        info_lay.addWidget(self.ai_get_key_btn)
        lay.addWidget(self.ai_info_bar)
        self._update_ai_info_bar()

        # Chat area
        self.ai_chat = QTextBrowser()
        self.ai_chat.setStyleSheet("""
            QTextBrowser {
                background-color: #010409; border: 1px solid #1a1f29;
                border-radius: 8px; padding: 12px; font-size: 13px;
            }
        """)
        self.ai_chat.setOpenExternalLinks(False)
        lay.addWidget(self.ai_chat, stretch=1)

        # Input row
        ai_input_row = QHBoxLayout()
        self.ai_input = QLineEdit()
        self.ai_input.setObjectName("promptInput")
        self.ai_input.setPlaceholderText("Ask Maxim AI about pentesting, tools, commands...")
        self.ai_input.returnPressed.connect(self._on_ai_submit)
        ai_input_row.addWidget(self.ai_input)

        ai_send = QPushButton("Send")
        ai_send.setFixedHeight(42)
        ai_send.clicked.connect(self._on_ai_submit)
        ai_input_row.addWidget(ai_send)
        lay.addLayout(ai_input_row)

        return w

    # ── Tab: Online Tools ──
    def _build_online_tab(self):
        w = QWidget()
        lay = QVBoxLayout(w)
        lay.setContentsMargins(16, 16, 16, 16)

        title = QLabel("Online Pentesting Resources")
        title.setObjectName("heading")
        lay.addWidget(title)

        desc = QLabel("Click to open in browser. These complement your local tools — use when you need OSINT, hash lookups, or external scanning.")
        desc.setObjectName("subheading")
        desc.setWordWrap(True)
        lay.addWidget(desc)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)

        container = QWidget()
        grid = QGridLayout(container)
        grid.setSpacing(10)

        # Group by category
        categories = {}
        for r in ONLINE_RESOURCES:
            cat = r.get("category", "other")
            categories.setdefault(cat, []).append(r)

        row = 0
        for cat, resources in categories.items():
            cat_label = QLabel(f'<span style="color:#58a6ff;font-weight:bold;font-size:14px;">{cat.upper()}</span>')
            grid.addWidget(cat_label, row, 0, 1, 3)
            row += 1

            col = 0
            for r in resources:
                card = QFrame()
                card.setObjectName("toolCard")
                card.setCursor(Qt.PointingHandCursor)
                card.setFixedHeight(90)
                clay = QVBoxLayout(card)

                name = QLabel(f'<span style="color:#d29922;font-size:14px;font-weight:bold;">{r["name"]}</span>')
                clay.addWidget(name)

                d = QLabel(r["desc"])
                d.setStyleSheet("color: #8b949e; font-size: 11px;")
                d.setWordWrap(True)
                clay.addWidget(d)

                clay.addStretch()

                btn = QPushButton("Open in Browser")
                btn.setFixedHeight(26)
                btn.setStyleSheet("QPushButton { border: 1px solid #d29922; color: #d29922; border-radius: 4px; } QPushButton:hover { background: #2d1f00; }")
                btn.clicked.connect(partial(self._open_online_tool, r["url"]))
                clay.addWidget(btn)

                grid.addWidget(card, row, col)
                col += 1
                if col >= 3:
                    col = 0
                    row += 1
            if col != 0:
                row += 1

        container.setLayout(grid)
        scroll.setWidget(container)
        lay.addWidget(scroll)
        return w

    # ── Tab: Log ──
    def _build_log_tab(self):
        w = QWidget()
        lay = QVBoxLayout(w)
        lay.setContentsMargins(16, 16, 16, 16)
        lay.addWidget(QLabel("Session Command Log"))

        self.log_view = QPlainTextEdit()
        self.log_view.setObjectName("terminal")
        self.log_view.setReadOnly(True)
        lay.addWidget(self.log_view)

        btn_row = QHBoxLayout()
        QPushButton_refresh = QPushButton("Refresh")
        QPushButton_refresh.setObjectName("ghostBtn")
        QPushButton_refresh.clicked.connect(self._refresh_log)
        btn_row.addWidget(QPushButton_refresh)

        clear_log = QPushButton("Clear")
        clear_log.setObjectName("ghostBtn")
        clear_log.clicked.connect(lambda: self.log_view.clear())
        btn_row.addWidget(clear_log)
        btn_row.addStretch()
        lay.addLayout(btn_row)
        return w

    def _build_menu(self):
        menubar = self.menuBar()

        file_menu = menubar.addMenu("File")
        file_menu.addAction("New Session", self._new_session)
        file_menu.addSeparator()
        file_menu.addAction("Quit", self.close, "Ctrl+Q")

        tools_menu = menubar.addMenu("Tools")
        tools_menu.addAction("Install All Packages", self._install_all_tools)
        tools_menu.addAction("Update System", lambda: self._execute_command("sudo apt-get update && sudo apt-get upgrade -y"))
        tools_menu.addSeparator()
        tools_menu.addAction("Start Tor", lambda: self._execute_command("sudo service tor start"))
        tools_menu.addAction("Start PostgreSQL (MSF)", lambda: self._execute_command("sudo service postgresql start"))

        ai_menu = menubar.addMenu("AI")

        # Offline
        offline_menu = ai_menu.addMenu("Offline (Ollama)")
        offline_menu.addAction("Install Ollama", lambda: self._execute_command("curl -fsSL https://ollama.com/install.sh | sh"))
        offline_menu.addAction("Start Ollama Server", lambda: self._execute_command("ollama serve &"))
        offline_menu.addSeparator()
        offline_menu.addAction("Pull Mistral (7B)", lambda: self._execute_command("ollama pull mistral"))
        offline_menu.addAction("Pull Llama3 (8B)", lambda: self._execute_command("ollama pull llama3"))
        offline_menu.addAction("Pull Phi3 (3.8B)", lambda: self._execute_command("ollama pull phi3"))
        offline_menu.addAction("Pull Gemma2 (9B)", lambda: self._execute_command("ollama pull gemma2"))
        offline_menu.addAction("Pull DeepSeek Coder", lambda: self._execute_command("ollama pull deepseek-coder"))
        offline_menu.addAction("Pull CodeLlama", lambda: self._execute_command("ollama pull codellama"))

        # Online providers
        ai_menu.addSeparator()
        online_menu = ai_menu.addMenu("Online Providers")
        for pid, prov in PROVIDERS.items():
            if prov["type"] == "online":
                prov_action = online_menu.addAction(
                    f"{prov['name']} — {prov['description'][:50]}",
                    partial(self._quick_switch_provider, pid)
                )

        ai_menu.addSeparator()
        ai_menu.addAction("Set API Key...", self._set_api_key)
        ai_menu.addAction("Switch to Ollama (Offline)", lambda: self._quick_switch_provider("ollama"))

        help_menu = menubar.addMenu("Help")
        help_menu.addAction("Check for Updates", self._check_updates)
        help_menu.addSeparator()
        help_menu.addAction("About", self._show_about)

    # ═══════════════════════════════════════
    #  EVENT HANDLERS
    # ═══════════════════════════════════════

    def _on_prompt_submit(self):
        query = self.prompt_input.text().strip()
        if not query:
            return

        # 1. Check NATURAL_COMMANDS (exact phrase matches)
        q_lower = query.lower().strip()
        for phrase, (tool, cmd, desc) in NATURAL_COMMANDS.items():
            if phrase in q_lower:
                cmd_filled = self._fill_placeholders(cmd)
                if cmd_filled:
                    self.prompt_input.clear()
                    tool_obj = get_tool_by_name(tool)
                    needs_root = tool_obj.get("needs_root", False) if tool_obj else False
                    self._execute_command(cmd_filled, as_root=needs_root)
                return

        # 2. SmartRouter
        route = SmartRouter.route(query)

        if route["direct_command"]:
            self._execute_command(route["direct_command"])
            self.prompt_input.clear()
            return

        if route["intent"] == "unknown":
            if self.ai.is_available():
                self.tabs.setCurrentIndex(3)
                self.ai_input.setText(query)
                self._on_ai_submit()
                self.prompt_input.clear()
            else:
                self.terminal.appendPlainText(
                    f"\n[!] Could not determine tool for: {query}\n"
                    f"    Try: 'scan ports on X', 'monitor mode wlan0', etc.\n"
                    f"    Or use the Workflows tab for guided steps.\n"
                )
            return

        if route["needs_choice"] and len(route["tools"]) > 1:
            dlg = ToolChoiceDialog(route["tools"], route["description"], self)
            if dlg.exec_() == QDialog.Accepted and dlg.chosen:
                tool = get_tool_by_name(dlg.chosen)
                self._show_tool_commands(tool, query)
            self.prompt_input.clear()
            return

        if route["tools"]:
            tool = route["tools"][0]
            self._show_tool_commands(tool, query)
            self.prompt_input.clear()

    def _show_tool_commands(self, tool, query=""):
        self.suggestion_frame.setVisible(True)
        self._clear_button_layout(self.cmd_buttons_layout)

        root_note = " [ROOT]" if tool["needs_root"] else ""
        self.suggestion_label.setText(
            f'<span style="color:#58a6ff;font-size:16px;font-weight:bold;">{tool["name"]}</span>'
            f' <span style="color:#8b949e;">-- {tool["description"]}{root_note}</span>'
        )
        for cc in tool["common_commands"]:
            btn = QPushButton(cc["label"])
            btn.setToolTip(cc["cmd"])
            btn.setObjectName("ghostBtn")
            btn.clicked.connect(partial(self._preview_and_run, cc["cmd"], tool["needs_root"]))
            self.cmd_buttons_layout.addWidget(btn)
        self.cmd_buttons_layout.addStretch()

    def _preview_and_run(self, cmd_template, needs_root):
        cmd = self._fill_placeholders(cmd_template)
        if cmd:
            self._execute_command(cmd, as_root=needs_root)

    def _fill_placeholders(self, cmd_template):
        placeholders = re.findall(r'\{(\w+)\}', cmd_template)
        cmd = cmd_template
        for ph in placeholders:
            defaults = {
                "iface": "wlan0", "target": "192.168.1.1", "port": "4444",
                "lhost": "0.0.0.0", "lport": "4444", "domain": "example.com",
                "user": "admin", "wordlist": "/usr/share/wordlists/rockyou.txt",
            }
            val, ok = QInputDialog.getText(
                self, f"Enter: {ph}",
                f"Value for {{{ph}}}:",
                QLineEdit.Normal,
                defaults.get(ph, "")
            )
            if not ok:
                return None
            cmd = cmd.replace(f"{{{ph}}}", val)
        return cmd

    def _execute_command(self, cmd, as_root=False):
        self.tabs.setCurrentIndex(0)
        self.terminal.appendPlainText(f"\n{'='*70}")
        self.terminal.appendPlainText(f" [{datetime.now().strftime('%H:%M:%S')}]  $ {cmd}")
        self.terminal.appendPlainText(f"{'='*70}\n")

        self.run_btn.setEnabled(False)
        self.stop_btn.setEnabled(True)
        self.statusBar().showMessage(f"Running: {cmd[:80]}...")

        self.current_thread = OutputSignal(self.runner, cmd, as_root)
        self.current_thread.line_received.connect(self._on_output_line)
        self.current_thread.finished.connect(
            lambda code, dur: self._on_command_done(cmd, code, dur)
        )
        self.current_thread.start()

    def _on_output_line(self, line):
        self.terminal.moveCursor(QTextCursor.End)
        self.terminal.insertPlainText(line)
        self.terminal.moveCursor(QTextCursor.End)

    def _on_command_done(self, cmd, exit_code, duration):
        status = "OK" if exit_code == 0 else f"FAILED (exit {exit_code})"
        self.terminal.appendPlainText(f"\n[{status}] Completed in {duration:.1f}s\n")
        self.run_btn.setEnabled(True)
        self.stop_btn.setEnabled(False)
        self.statusBar().showMessage(f"{status} -- {duration:.1f}s")

        tool_name = cmd.split()[0].split("/")[-1] if cmd else "unknown"
        self.session.log_command(cmd, tool_name, exit_code, duration)
        self.stats_label.setText(f"Session: {len(self.session.commands)} commands")

    def _on_stop(self):
        self.runner.kill_all()
        self.terminal.appendPlainText("\n[KILLED] Process terminated.\n")
        self.run_btn.setEnabled(True)
        self.stop_btn.setEnabled(False)

    # ── Category / Phase navigation ──

    def _on_phase_select(self, current, previous):
        if not current:
            return
        phase_id = current.data(Qt.UserRole)
        self._show_phase_detail(phase_id)

    def _on_category_select(self, current, previous):
        if not current:
            return
        cat_id = current.data(Qt.UserRole)
        self.tabs.setCurrentIndex(2)
        self.tool_search.setText("")
        self._clear_grid(self.tools_grid)

        col, row = 0, 0
        for tool in TOOLS:
            if tool["category"] == cat_id:
                card = self._make_tool_card(tool)
                self.tools_grid.addWidget(card, row, col)
                col += 1
                if col >= 3:
                    col = 0
                    row += 1

    # ── Tools grid ──

    def _populate_tools_grid(self, filter_text=""):
        self._clear_grid(self.tools_grid)
        col, row = 0, 0
        for tool in TOOLS:
            if filter_text:
                ft = filter_text.lower()
                if ft not in tool["name"].lower() and ft not in tool["description"].lower() \
                        and not any(ft in kw for kw in tool["keywords"]):
                    continue
            card = self._make_tool_card(tool)
            self.tools_grid.addWidget(card, row, col)
            col += 1
            if col >= 3:
                col = 0
                row += 1

    def _make_tool_card(self, tool):
        card = QFrame()
        card.setObjectName("toolCard")
        card.setFixedHeight(130)
        lay = QVBoxLayout(card)
        lay.setSpacing(4)

        cat = TOOL_CATEGORIES.get(tool["category"], {})
        color = cat.get("color", "#58a6ff")

        name_lbl = QLabel(f'<span style="color:{color};font-size:15px;font-weight:bold;">{tool["name"]}</span>')
        lay.addWidget(name_lbl)

        desc_lbl = QLabel(tool["description"])
        desc_lbl.setStyleSheet("color: #8b949e; font-size: 11px;")
        desc_lbl.setWordWrap(True)
        lay.addWidget(desc_lbl)

        cat_lbl = QLabel(cat.get("name", ""))
        cat_lbl.setStyleSheet(f"color: {color}; font-size: 10px;")
        lay.addWidget(cat_lbl)
        lay.addStretch()

        btn_row = QHBoxLayout()
        run_btn = QPushButton("Use")
        run_btn.setFixedSize(60, 28)
        run_btn.clicked.connect(partial(self._show_tool_commands, tool))
        btn_row.addWidget(run_btn)

        install_btn = QPushButton("Install")
        install_btn.setFixedSize(70, 28)
        install_btn.setObjectName("ghostBtn")
        install_btn.clicked.connect(partial(self._execute_command, f"sudo apt-get install -y {tool['package']}"))
        btn_row.addWidget(install_btn)
        btn_row.addStretch()
        lay.addLayout(btn_row)
        return card

    def _filter_tools(self, text):
        self._populate_tools_grid(text)

    def _install_all_tools(self):
        pkgs = get_all_packages()
        self._execute_command(f"sudo apt-get install -y {' '.join(pkgs)}")

    # ── AI ──

    def _on_provider_change(self, index):
        pid = self.provider_combo.itemData(index)
        if pid:
            self.ai.switch_provider(pid)
            self._refresh_models()
            self._update_ai_provider_status()
            self._update_ai_info_bar()
            self._update_status()

    def _on_model_change(self, index):
        model = self.model_combo.currentText()
        if model and not model.startswith("("):
            self.ai.set_model(model)

    def _refresh_models(self):
        self.model_combo.blockSignals(True)
        self.model_combo.clear()
        models = self.ai.get_models()
        if models:
            self.model_combo.addItems(models)
        else:
            self.model_combo.addItem("(no models)")
        self.model_combo.blockSignals(False)

    def _set_api_key(self):
        pid = self.provider_combo.itemData(self.provider_combo.currentIndex())
        if pid == "ollama":
            QMessageBox.information(self, "Ollama", "Ollama runs locally — no API key needed.\n\nInstall: curl -fsSL https://ollama.com/install.sh | sh")
            return

        prov = PROVIDERS.get(pid, {})
        current = get_api_key(pid)
        masked = current[:8] + "..." if len(current) > 8 else current

        key, ok = QInputDialog.getText(
            self, f"API Key — {prov.get('name', pid)}",
            f"Enter your API key for {prov.get('name', pid)}:\n"
            f"Get one at: {prov.get('key_url', 'N/A')}\n\n"
            f"Current: {masked or '(not set)'}",
            QLineEdit.Normal, ""
        )
        if ok and key.strip():
            self.ai.set_api_key(pid, key.strip())
            self._update_ai_provider_status()
            self._update_ai_info_bar()
            self._update_status()
            QMessageBox.information(self, "Saved", f"API key for {prov.get('name', pid)} saved!")

    def _open_key_url(self):
        pid = self.provider_combo.itemData(self.provider_combo.currentIndex())
        prov = PROVIDERS.get(pid, {})
        url = prov.get("key_url")
        if url:
            webbrowser.open(url)

    def _update_ai_provider_status(self):
        status = self.ai.get_status()
        if self.ai.is_available():
            self.ai_provider_status.setText(status)
            self.ai_provider_status.setStyleSheet("color: #3fb950; font-size: 11px; padding: 4px 10px; background: #0d2818; border-radius: 10px;")
        else:
            self.ai_provider_status.setText(status)
            self.ai_provider_status.setStyleSheet("color: #f85149; font-size: 11px; padding: 4px 10px; background: #2d0f0f; border-radius: 10px;")

    def _update_ai_info_bar(self):
        pid = self.provider_combo.itemData(self.provider_combo.currentIndex())
        prov = PROVIDERS.get(pid, {})

        if pid == "ollama":
            if self.ai.ollama.is_available():
                self.ai_info_label.setText(
                    '<span style="color:#3fb950;">Local AI running.</span> '
                    '<span style="color:#8b949e;">Fully offline, no internet needed. Pull more models from the AI menu.</span>'
                )
            else:
                self.ai_info_label.setText(
                    '<span style="color:#d29922;">Ollama not running.</span> '
                    '<span style="color:#8b949e;">Install: <code>curl -fsSL https://ollama.com/install.sh | sh</code> then <code>ollama serve</code></span>'
                )
            self.ai_get_key_btn.setVisible(False)
            self.api_key_btn.setVisible(False)
        else:
            has_key = bool(get_api_key(pid))
            desc = prov.get("description", "")
            if has_key:
                self.ai_info_label.setText(
                    f'<span style="color:#3fb950;">Connected.</span> '
                    f'<span style="color:#8b949e;">{desc}</span>'
                )
            else:
                self.ai_info_label.setText(
                    f'<span style="color:#f85149;">API key required.</span> '
                    f'<span style="color:#8b949e;">{desc}</span>'
                )
            self.ai_get_key_btn.setVisible(not has_key)
            self.api_key_btn.setVisible(True)

    def _clear_ai_chat(self):
        self.ai_chat.clear()
        self.ai.clear_context()

    def _on_ai_submit(self):
        msg = self.ai_input.text().strip()
        if not msg:
            return
        self.ai_input.clear()

        self.ai_chat.append(
            f'<div style="background:#1a3a5c;border-radius:10px;padding:10px;margin:6px 60px 6px 6px;">'
            f'<b style="color:#58a6ff;">You:</b> '
            f'<span style="color:#e6edf3;">{msg}</span></div>'
        )

        if not self.ai.is_available():
            # Fallback to SmartRouter
            route = SmartRouter.route(msg)
            if route["tools"]:
                parts = []
                for t in route["tools"]:
                    parts.append(f"<b>{t['name']}</b> - {t['description']}<br>")
                    for cc in t["common_commands"][:3]:
                        parts.append(f"&nbsp;&nbsp;<code>{cc['cmd']}</code><br>")
                reply = "".join(parts)
            elif route["direct_command"]:
                reply = f"Run: <code>{route['direct_command']}</code>"
            else:
                reply = ("No AI provider available. Options:<br>"
                         "- <b>Offline:</b> Install Ollama: <code>curl -fsSL https://ollama.com/install.sh | sh</code><br>"
                         "- <b>Online:</b> Set an API key (click Provider dropdown > API Key button)")

            provider_tag = self.ai.provider_name
            self.ai_chat.append(
                f'<div style="background:#161b22;border-radius:10px;padding:10px;margin:6px 6px 6px 60px;">'
                f'<b style="color:#d29922;">Maxim (No AI):</b> {reply}</div>'
            )
            return

        # Show thinking indicator
        provider_tag = self.ai.provider_name
        self.ai_chat.append(
            f'<div style="background:#161b22;border-radius:10px;padding:8px;margin:6px 6px 2px 60px;">'
            f'<span style="color:#484f58;">Thinking via {provider_tag}...</span></div>'
        )

        self._ai_thread = AIStreamSignal(self.ai, msg)

        def on_done(full):
            # Remove "thinking" message by replacing last block
            text = full.replace("\n", "<br>")
            # Format code blocks
            text = text.replace("```", "<pre style='background:#0d1117;padding:8px;border-radius:4px;overflow-x:auto;'>")
            self.ai_chat.append(
                f'<div style="background:#161b22;border-radius:10px;padding:10px;margin:6px 6px 6px 60px;">'
                f'<b style="color:#3fb950;">Maxim AI</b> '
                f'<span style="color:#484f58;font-size:10px;">via {provider_tag}</span><br>'
                f'<span style="color:#c5c8c6;">{text}</span></div>'
            )

        self._ai_thread.finished.connect(on_done)
        self._ai_thread.start()

    # ── Session ──

    def _refresh_log(self):
        self.log_view.clear()
        for entry in self.session.commands:
            self.log_view.appendPlainText(
                f"[{entry['timestamp'][:19]}] ({entry['tool']}) "
                f"exit={entry['exit_code']} dur={entry['duration_s']}s\n"
                f"  $ {entry['command']}\n"
            )

    def _new_session(self):
        self.session = Session()
        self.terminal.clear()
        self.stats_label.setText("Session: 0 commands")

    # ── Helpers ──

    def _clear_layout(self, layout):
        while layout.count():
            child = layout.takeAt(0)
            if child.widget():
                child.widget().deleteLater()
            elif child.layout():
                self._clear_layout(child.layout())

    def _clear_grid(self, grid):
        while grid.count():
            child = grid.takeAt(0)
            if child.widget():
                child.widget().deleteLater()

    def _clear_button_layout(self, layout):
        while layout.count():
            child = layout.takeAt(0)
            if child.widget():
                child.widget().deleteLater()

    def _update_status(self):
        status = self.ai.get_status()
        if self.ai.is_available():
            self.ai_status.setText(f"AI: {status}")
            self.ai_status.setStyleSheet("color: #3fb950; font-size: 12px; padding: 4px 12px; background: #0d2818; border-radius: 12px;")
        else:
            self.ai_status.setText(f"AI: {status}")
            self.ai_status.setStyleSheet("color: #d29922; font-size: 12px; padding: 4px 12px; background: #2d1f00; border-radius: 12px;")

    def _quick_switch_provider(self, pid):
        """Switch AI provider from menu."""
        self.ai.switch_provider(pid)
        # Update combo box
        idx = list(PROVIDERS.keys()).index(pid) if pid in PROVIDERS else 0
        self.provider_combo.blockSignals(True)
        self.provider_combo.setCurrentIndex(idx)
        self.provider_combo.blockSignals(False)
        self._refresh_models()
        self._update_ai_provider_status()
        self._update_ai_info_bar()
        self._update_status()
        # If online and no key, prompt
        prov = PROVIDERS.get(pid, {})
        if prov.get("needs_key") and not get_api_key(pid):
            self.tabs.setCurrentIndex(3)  # Switch to AI tab
            self._set_api_key()

    def _check_updates(self):
        info = check_for_update()
        if info["available"]:
            reply = QMessageBox.question(
                self, "Update Available",
                f"<b>Maxim v{info['latest']}</b> is available (you have v{info['current']}).\n\n"
                f"{info['notes'][:300]}\n\nUpdate now?",
                QMessageBox.Yes | QMessageBox.No
            )
            if reply == QMessageBox.Yes:
                self._execute_command(f"cd {os.path.dirname(os.path.dirname(os.path.abspath(__file__)))} && git pull origin main")
        else:
            QMessageBox.information(self, "Up to Date", f"Maxim v{info['current']} is the latest version.")

    def _show_about(self):
        ver = get_current_version()
        QMessageBox.about(self, "About Maxim",
            f"<h2 style='color:#3b82f6;'>MAXIM v{ver}</h2>"
            "<p>Penetration Testing Command Center for Kali Linux</p>"
            "<p>40+ integrated tools | 7 workflow phases | 6 AI providers</p>"
            "<p style='color:#71717a;'>Offline AI: Ollama | Online: OpenAI, Claude, Gemini, Groq, OpenRouter</p>"
        )

    def closeEvent(self, event):
        self.runner.kill_all()
        event.accept()
