"""
Maxim Main Window — clean CLI-style pentesting interface.
"""

import os
import re
import html
import subprocess
import webbrowser
import threading
from datetime import datetime
from functools import partial

from PyQt5.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QPlainTextEdit, QLineEdit, QPushButton, QLabel,
    QFrame, QComboBox, QMessageBox, QAction,
    QMenu, QMenuBar, QApplication, QInputDialog, QSplitter,
    QTextBrowser, QProgressBar, QFileDialog,
)
from PyQt5.QtCore import Qt, QThread, pyqtSignal, QTimer
from PyQt5.QtGui import QFont, QTextCursor

from maxim.gui.styles import MAIN_STYLE
from maxim.core.engine import ProcessRunner, Session, ToolInstaller
from maxim.core.ai_assistant import AIManager, SmartRouter, PROVIDERS, get_api_key, set_api_key
from maxim.core.updater import check_for_update, perform_update, get_current_version
from maxim.core.workflows import NATURAL_COMMANDS
from maxim.tools.tool_registry import (
    TOOLS, get_tool_by_name, get_all_packages
)


class DropTerminal(QPlainTextEdit):
    """Terminal that accepts drag & drop of files."""
    file_dropped = pyqtSignal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setAcceptDrops(True)
        self._normal_style = ""

    def setStyleSheet(self, style):
        super().setStyleSheet(style)
        if "border: 1px solid #18181b" in style:
            self._normal_style = style

    def dragEnterEvent(self, event):
        if event.mimeData().hasUrls():
            event.setDropAction(Qt.CopyAction)
            event.accept()
            if self._normal_style:
                super().setStyleSheet(self._normal_style.replace(
                    "border: 1px solid #18181b", "border: 2px solid #3b82f6"
                ))
        else:
            event.ignore()

    def dragMoveEvent(self, event):
        if event.mimeData().hasUrls():
            event.setDropAction(Qt.CopyAction)
            event.accept()
        else:
            event.ignore()

    def dragLeaveEvent(self, event):
        if self._normal_style:
            super().setStyleSheet(self._normal_style)

    def dropEvent(self, event):
        if self._normal_style:
            super().setStyleSheet(self._normal_style)
        if event.mimeData().hasUrls():
            for url in event.mimeData().urls():
                filepath = url.toLocalFile()
                if filepath:
                    self.file_dropped.emit(filepath)
                    break
            event.setDropAction(Qt.CopyAction)
            event.accept()
        else:
            event.ignore()


class OutputSignal(QThread):
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


class MaximWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("MAXIM")
        self.setMinimumSize(1100, 700)
        self.setStyleSheet(MAIN_STYLE)

        self.runner = ProcessRunner()
        self.session = Session()
        self.ai = None
        self.current_thread = None
        self._running = False

        self._build_ui()
        self._build_menu()

        # Non-blocking startup
        QTimer.singleShot(50, self._startup)

    def _startup(self):
        self._ask_sudo_password()
        # Init AI in background thread to not block UI
        self._init_ai_thread = threading.Thread(target=self._init_ai, daemon=True)
        self._init_ai_thread.start()

    def _init_ai(self):
        self.ai = AIManager()
        # Schedule UI update on main thread
        QTimer.singleShot(0, self._update_status)

    def _ask_sudo_password(self):
        # Auto-set sudo password
        self.runner.set_sudo_password("5505")
        self.terminal.appendPlainText("[OK] Sudo password set.\n")
        return
        # Fallback dialog (kept but unreachable)
        pwd, ok = QInputDialog.getText(
            self, "Sudo Password",
            "Enter your sudo password (needed to run privileged commands):",
            QLineEdit.Password, ""
        )
        if ok and pwd:
            self.runner.set_sudo_password(pwd)
            self.terminal.appendPlainText("[OK] Sudo password set.\n")
        elif not ok:
            self.terminal.appendPlainText("[!] No sudo password — privileged commands may fail.\n")

    # ═══════════════════════════════════════
    #  UI
    # ═══════════════════════════════════════

    def _build_ui(self):
        central = QWidget()
        self.setCentralWidget(central)
        root = QVBoxLayout(central)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        # ── Header ──
        header = QFrame()
        header.setFixedHeight(52)
        header.setStyleSheet("background-color: #09090b; border-bottom: 2px solid #3b82f6;")
        hlay = QHBoxLayout(header)
        hlay.setContentsMargins(20, 0, 20, 0)

        logo = QLabel("MAXIM")
        logo.setStyleSheet("color: #3b82f6; font-size: 26px; font-weight: bold; letter-spacing: 8px;")
        hlay.addWidget(logo)

        subtitle = QLabel("Penetration Testing Command Center")
        subtitle.setStyleSheet("color: #52525b; font-size: 14px; margin-left: 16px;")
        hlay.addWidget(subtitle)
        hlay.addStretch()

        self.ai_status = QLabel("AI: Loading...")
        self.ai_status.setStyleSheet("color: #52525b; font-size: 13px; padding: 4px 14px; background: #18181b; border-radius: 12px;")
        hlay.addWidget(self.ai_status)

        self.cmd_count_label = QLabel("0 commands")
        self.cmd_count_label.setStyleSheet("color: #52525b; font-size: 13px; margin-left: 8px;")
        hlay.addWidget(self.cmd_count_label)

        root.addWidget(header)

        # ── Prompt ──
        prompt_frame = QFrame()
        prompt_frame.setStyleSheet("QFrame { background: #0c0c0f; border-bottom: 1px solid #18181b; }")
        play = QVBoxLayout(prompt_frame)
        play.setContentsMargins(20, 10, 20, 10)
        play.setSpacing(6)

        hint = QLabel('Type a command or describe what you want — Maxim auto-picks the right tool.')
        hint.setStyleSheet("color: #71717a; font-size: 14px;")
        play.addWidget(hint)

        input_row = QHBoxLayout()
        input_row.setSpacing(8)

        self.prompt_input = QLineEdit()
        self.prompt_input.setPlaceholderText('e.g. "scan 192.168.1.0/24" or "sudo nmap -sV target" or "crack this hash"')
        self.prompt_input.returnPressed.connect(self._on_prompt_submit)
        self.prompt_input.installEventFilter(self)
        self._cmd_history = []
        self._history_idx = -1
        self._history_draft = ""
        self.prompt_input.setStyleSheet("""
            QLineEdit {
                background-color: #09090b; border: 2px solid #27272a; border-radius: 12px;
                padding: 14px 20px; font-size: 18px; color: #fafafa;
            }
            QLineEdit:focus { border-color: #3b82f6; background-color: #0c0c0f; }
        """)
        input_row.addWidget(self.prompt_input)

        self.run_btn = QPushButton("Execute")
        self.run_btn.setFixedSize(110, 50)
        self.run_btn.setStyleSheet("""
            QPushButton { background-color: #3b82f6; color: white; border-radius: 12px; font-size: 16px; font-weight: 600; }
            QPushButton:hover { background-color: #60a5fa; }
            QPushButton:disabled { background-color: #18181b; color: #3f3f46; }
        """)
        self.run_btn.clicked.connect(self._on_prompt_submit)
        input_row.addWidget(self.run_btn)

        self.stop_btn = QPushButton("Stop")
        self.stop_btn.setFixedSize(70, 50)
        self.stop_btn.setStyleSheet("""
            QPushButton { background-color: #ef4444; color: white; border-radius: 12px; font-size: 16px; font-weight: 600; }
            QPushButton:hover { background-color: #f87171; }
            QPushButton:disabled { background-color: #18181b; color: #3f3f46; }
        """)
        self.stop_btn.clicked.connect(self._on_stop)
        self.stop_btn.setEnabled(False)
        input_row.addWidget(self.stop_btn)

        play.addLayout(input_row)

        # Progress bar (hidden by default)
        self.progress = QProgressBar()
        self.progress.setRange(0, 0)  # Indeterminate
        self.progress.setFixedHeight(3)
        self.progress.setTextVisible(False)
        self.progress.setStyleSheet("""
            QProgressBar { background: #18181b; border: none; }
            QProgressBar::chunk { background: qlineargradient(x1:0,y1:0,x2:1,y2:0, stop:0 #3b82f6, stop:1 #8b5cf6); }
        """)
        self.progress.hide()
        play.addWidget(self.progress)

        # Running indicator
        self.running_label = QLabel()
        self.running_label.setStyleSheet("color: #3b82f6; font-size: 13px; font-weight: 500;")
        self.running_label.hide()
        play.addWidget(self.running_label)

        # Quick actions
        qbar = QHBoxLayout()
        qbar.setSpacing(6)

        btn_style = """
            QPushButton {
                background: transparent; border: 1px solid #27272a; color: #a1a1aa;
                border-radius: 8px; padding: 6px 14px; font-size: 14px; font-weight: 500;
            }
            QPushButton:hover { border-color: #3b82f6; color: #3b82f6; }
        """

        load_file_btn = QPushButton("Load File")
        load_file_btn.setStyleSheet(btn_style)
        load_file_btn.clicked.connect(self._load_file)
        qbar.addWidget(load_file_btn)

        restore_net_btn = QPushButton("Restore Network")
        restore_net_btn.setStyleSheet("""
            QPushButton {
                background: transparent; border: 1px solid #27272a; color: #ef4444;
                border-radius: 8px; padding: 6px 14px; font-size: 14px; font-weight: 500;
            }
            QPushButton:hover { border-color: #ef4444; color: #f87171; }
        """)
        restore_net_btn.clicked.connect(self._restore_network)
        qbar.addWidget(restore_net_btn)

        add_wl_btn = QPushButton("Add Wordlist")
        add_wl_btn.setStyleSheet(btn_style)
        add_wl_btn.clicked.connect(self._add_word_to_wordlist_btn)
        qbar.addWidget(add_wl_btn)

        clear_btn = QPushButton("Clear")
        clear_btn.setStyleSheet(btn_style)
        clear_btn.clicked.connect(self._clear_terminal)
        qbar.addWidget(clear_btn)

        qbar.addStretch()
        play.addLayout(qbar)

        root.addWidget(prompt_frame)

        # ── Main: Terminal + AI ──
        splitter = QSplitter(Qt.Horizontal)
        splitter.setStyleSheet("QSplitter::handle { background: #18181b; width: 2px; }")

        # Terminal
        term_frame = QWidget()
        tlay = QVBoxLayout(term_frame)
        tlay.setContentsMargins(12, 8, 4, 12)
        tlay.setSpacing(4)

        term_header = QLabel("OUTPUT")
        term_header.setStyleSheet("color: #4ade80; font-size: 12px; font-weight: bold; letter-spacing: 4px;")
        tlay.addWidget(term_header)

        self.terminal = DropTerminal()
        self.terminal.setObjectName("terminal")
        self.terminal.setReadOnly(True)
        self.terminal.file_dropped.connect(self._on_file_dropped)
        self.terminal.setFont(QFont("JetBrains Mono", 13))
        self.terminal.setPlaceholderText("Output will appear here...\n\nDrag & drop .cap, .pcap, .hash, or .txt files here to crack them")
        self.terminal.setStyleSheet("""
            QPlainTextEdit {
                background-color: #000000; color: #4ade80;
                border: 1px solid #18181b; border-radius: 10px; padding: 14px;
                font-family: 'JetBrains Mono', 'Fira Code', 'Cascadia Code', 'Consolas', monospace;
                font-size: 15px;
            }
        """)
        tlay.addWidget(self.terminal)
        splitter.addWidget(term_frame)

        # AI Chat
        ai_frame = QWidget()
        alay = QVBoxLayout(ai_frame)
        alay.setContentsMargins(4, 8, 12, 12)
        alay.setSpacing(4)

        ai_header = QLabel("AI ASSISTANT")
        ai_header.setStyleSheet("color: #60a5fa; font-size: 12px; font-weight: bold; letter-spacing: 4px;")
        alay.addWidget(ai_header)

        self.ai_chat = QTextBrowser()
        self.ai_chat.setOpenExternalLinks(False)
        self.ai_chat.setStyleSheet("""
            QTextBrowser {
                background-color: #000000; border: 1px solid #18181b;
                border-radius: 10px; padding: 14px; font-size: 15px; color: #e4e4e7;
            }
        """)
        alay.addWidget(self.ai_chat)

        ai_row = QHBoxLayout()
        ai_row.setSpacing(6)
        self.ai_input = QLineEdit()
        self.ai_input.setPlaceholderText("Ask AI about pentesting...")
        self.ai_input.setStyleSheet("""
            QLineEdit {
                background-color: #09090b; border: 1px solid #27272a; border-radius: 10px;
                padding: 10px 14px; font-size: 15px; color: #fafafa;
            }
            QLineEdit:focus { border-color: #3b82f6; }
        """)
        self.ai_input.returnPressed.connect(self._on_ai_submit)
        ai_row.addWidget(self.ai_input)

        ai_send = QPushButton("Ask")
        ai_send.setFixedSize(70, 40)
        ai_send.setStyleSheet("""
            QPushButton { background-color: #3b82f6; color: white; border-radius: 10px; font-size: 15px; font-weight: 600; }
            QPushButton:hover { background-color: #60a5fa; }
        """)
        ai_send.clicked.connect(self._on_ai_submit)
        ai_row.addWidget(ai_send)
        alay.addLayout(ai_row)

        splitter.addWidget(ai_frame)
        splitter.setSizes([650, 450])

        root.addWidget(splitter, stretch=1)

        self.statusBar().showMessage("Ready")
        self.statusBar().setStyleSheet("color: #52525b; font-size: 13px; background: #09090b; border-top: 1px solid #18181b;")

    def _build_menu(self):
        menubar = self.menuBar()

        file_menu = menubar.addMenu("File")
        file_menu.addAction("New Session", self._new_session)
        file_menu.addAction("Clear Terminal", self._clear_terminal)
        file_menu.addSeparator()
        file_menu.addAction("Quit", self.close, "Ctrl+Q")

        tools_menu = menubar.addMenu("Tools")
        tools_menu.addAction("Install All Packages", self._install_all_tools)
        tools_menu.addAction("Update System", lambda: self._execute_command("sudo apt-get update && sudo apt-get upgrade -y"))
        tools_menu.addSeparator()
        tools_menu.addAction("Start Tor", lambda: self._execute_command("sudo service tor start"))
        tools_menu.addAction("Start PostgreSQL (MSF)", lambda: self._execute_command("sudo service postgresql start"))

        wordlist_menu = menubar.addMenu("Wordlists")
        wordlist_menu.addAction("Download SecLists (large)", lambda: self._execute_command(
            "sudo apt-get install -y seclists || (cd /usr/share/wordlists && sudo git clone --depth 1 https://github.com/danielmiessler/SecLists.git seclists)"
        ))
        wordlist_menu.addAction("Download CrackStation (huge 15GB)", lambda: self._execute_command(
            "cd /usr/share/wordlists && sudo wget -c https://crackstation.net/files/crackstation.txt.gz && sudo gunzip crackstation.txt.gz"
        ))
        wordlist_menu.addAction("Download Weakpass (2GB)", lambda: self._execute_command(
            "cd /usr/share/wordlists && sudo wget -c https://weakpass.com/wordlist/1851 -O weakpass_3.txt"
        ))
        wordlist_menu.addAction("Download WiFi Wordlists", lambda: self._execute_command(
            "cd /usr/share/wordlists && sudo wget -c https://raw.githubusercontent.com/praetorian-inc/Hob0Rules/master/wordlists/wordlist.txt -O wifi-common.txt"
        ))
        wordlist_menu.addSeparator()
        wordlist_menu.addAction("Unzip rockyou.txt", lambda: self._execute_command(
            "sudo gunzip -k /usr/share/wordlists/rockyou.txt.gz 2>/dev/null; ls -lh /usr/share/wordlists/rockyou.txt"
        ))
        wordlist_menu.addAction("Show installed wordlists", lambda: self._execute_command(
            "echo '=== Wordlists ===' && find /usr/share/wordlists -name '*.txt' -o -name '*.lst' 2>/dev/null | head -50 && echo && du -sh /usr/share/wordlists/* 2>/dev/null"
        ))
        wordlist_menu.addSeparator()
        wordlist_menu.addAction("Add word to rockyou.txt", lambda: self._add_word_to_wordlist("/usr/share/wordlists/rockyou.txt"))
        wordlist_menu.addAction("Add word to custom wordlist...", self._add_word_to_custom_wordlist)

        ai_menu = menubar.addMenu("AI")

        offline_menu = ai_menu.addMenu("Offline (Ollama)")
        offline_menu.addAction("Install Ollama", lambda: self._execute_command("curl -fsSL https://ollama.com/install.sh | sh"))
        offline_menu.addAction("Start Ollama Server", lambda: self._execute_command("ollama serve &"))
        offline_menu.addSeparator()
        for model in ["mistral", "llama3", "phi3", "gemma2", "deepseek-coder", "codellama"]:
            offline_menu.addAction(f"Pull {model}", partial(self._execute_command, f"ollama pull {model}"))

        ai_menu.addSeparator()
        online_menu = ai_menu.addMenu("Online Providers")
        for pid, prov in PROVIDERS.items():
            if prov["type"] == "online":
                online_menu.addAction(f"{prov['name']}", partial(self._quick_switch_provider, pid))

        ai_menu.addSeparator()
        ai_menu.addAction("Set API Key...", self._set_api_key_dialog)
        ai_menu.addAction("Switch to Ollama (Offline)", lambda: self._quick_switch_provider("ollama"))

        help_menu = menubar.addMenu("Help")
        help_menu.addAction("Check for Updates", self._check_updates)
        help_menu.addAction("About", self._show_about)

    # ═══════════════════════════════════════
    #  RUNNING STATE
    # ═══════════════════════════════════════

    def _set_running(self, running, label=""):
        """Set running state — locks input, shows progress, only Stop works."""
        self._running = running
        self.prompt_input.setEnabled(not running)
        self.run_btn.setEnabled(not running)
        self.stop_btn.setEnabled(running)

        if running:
            self.progress.show()
            self.running_label.setText(label or "Working...")
            self.running_label.show()
            self.prompt_input.setStyleSheet("""
                QLineEdit {
                    background-color: #0c0c0f; border: 2px solid #18181b; border-radius: 12px;
                    padding: 14px 20px; font-size: 18px; color: #52525b;
                }
            """)
        else:
            self.progress.hide()
            self.running_label.hide()
            self.prompt_input.setStyleSheet("""
                QLineEdit {
                    background-color: #09090b; border: 2px solid #27272a; border-radius: 12px;
                    padding: 14px 20px; font-size: 18px; color: #fafafa;
                }
                QLineEdit:focus { border-color: #3b82f6; background-color: #0c0c0f; }
            """)
            self.prompt_input.setFocus()

    # ═══════════════════════════════════════
    #  PROMPT HANDLING
    # ═══════════════════════════════════════

    def eventFilter(self, obj, event):
        """Handle up/down arrow keys for command history."""
        if obj == self.prompt_input and event.type() == event.KeyPress:
            key = event.key()
            if key == Qt.Key_Up and self._cmd_history:
                if self._history_idx == -1:
                    self._history_draft = self.prompt_input.text()
                    self._history_idx = len(self._cmd_history) - 1
                elif self._history_idx > 0:
                    self._history_idx -= 1
                self.prompt_input.setText(self._cmd_history[self._history_idx])
                return True
            elif key == Qt.Key_Down:
                if self._history_idx == -1:
                    return True
                if self._history_idx < len(self._cmd_history) - 1:
                    self._history_idx += 1
                    self.prompt_input.setText(self._cmd_history[self._history_idx])
                else:
                    self._history_idx = -1
                    self.prompt_input.setText(self._history_draft)
                return True
        return super().eventFilter(obj, event)

    def _on_prompt_submit(self):
        if self._running:
            return
        query = self.prompt_input.text().strip()
        if not query:
            return
        # Save to history
        if not self._cmd_history or self._cmd_history[-1] != query:
            self._cmd_history.append(query)
        self._history_idx = -1
        self._history_draft = ""
        self.prompt_input.clear()
        q_lower = query.lower().strip()

        # 1. Raw command (starts with a known tool binary)
        raw_prefixes = (
            "sudo ", "nmap ", "airmon-ng", "airodump", "aireplay",
            "aircrack", "wifite", "msfconsole", "sqlmap ", "hydra ",
            "nikto ", "gobuster ", "dirb ", "ffuf ", "john ",
            "hashcat ", "wireshark", "tcpdump ", "ettercap",
            "netcat ", "nc ", "curl ", "wget ", "ping ",
            "traceroute", "whois ", "dig ", "host ", "ip ",
            "ifconfig", "iwconfig", "macchanger", "reaver ",
            "bettercap", "responder", "searchsploit", "msfvenom",
            "enum4linux", "smbclient", "crackmapexec", "gobuster",
            "masscan ", "netdiscover", "tor ", "proxychains",
            "ssh ", "socat ", "chisel ", "cat ", "grep ",
            "ls ", "cd ", "apt ", "apt-get ", "systemctl ",
            "service ", "chmod ", "chown ", "mkdir ", "rm ", "cp ", "mv ",
        )
        if any(q_lower.startswith(p) for p in raw_prefixes):
            self._execute_command(query)
            return

        # 2. Handshake capture workflow
        handshake_match = re.search(r'(?:capture|get|grab)\s+(?:the\s+)?handshake\s+(?:on|from|for|of)\s+(.+)', q_lower)
        if not handshake_match:
            handshake_match = re.search(r'handshake\s+(?:on|from|for|of)\s+(.+)', q_lower)
        if handshake_match:
            essid = handshake_match.group(1).strip().strip('"\'')
            self._capture_handshake(essid)
            return

        # 3. Everything else → AI decides what to do
        if self.ai and self.ai.is_available():
            self._ai_execute(query)
        else:
            # Fallback: try SmartRouter if AI is not available
            route = SmartRouter.route(query)
            if route["direct_command"]:
                self._execute_command(route["direct_command"])
            elif route["tools"]:
                tool = route["tools"][0]
                if tool.get("common_commands"):
                    best_cmd = tool["common_commands"][0]["cmd"]
                    cmd_filled = self._fill_placeholders(best_cmd, query)
                    if cmd_filled:
                        self._execute_command(cmd_filled, as_root=tool.get("needs_root", False))
                else:
                    self._execute_command(f"{tool['name']} --help")
            else:
                self.terminal.appendPlainText(
                    f"\n[!] Don't know how to: {query}\n"
                    f"    Set up AI: AI menu > Set API Key.\n"
                )

    def _ai_execute(self, query):
        self._set_running(True, f"⚡ AI thinking: {query[:50]}...")
        self.terminal.appendPlainText(f"\n⚡ AI analyzing: {query}...\n")

        thread = AIStreamSignal(self.ai, query)

        def on_done(response):
            try:
                self._set_running(False)
                if response.startswith("[Error]") or response.startswith("[AI Error]"):
                    self.terminal.appendPlainText(f"\n{response}\n")
                    return

                # Clean response — remove markdown formatting
                cleaned = response.strip()
                cleaned = re.sub(r'^```\w*\n?', '', cleaned)
                cleaned = re.sub(r'\n?```\s*$', '', cleaned)
                cleaned = cleaned.strip()

                if not cleaned:
                    self.terminal.appendPlainText(f"\n[AI] {response}\n")
                    return

                # If it contains heredoc/EOF/cat>, run the whole thing directly
                if "<<" in cleaned or "EOF" in cleaned or "cat >" in cleaned:
                    self.terminal.appendPlainText(f"⚡ Running command...\n")
                    self._execute_command(cleaned)
                    return

                # Split into lines, clean each
                commands = []
                for line in cleaned.split("\n"):
                    line = line.strip()
                    if not line or line.startswith("#"):
                        continue
                    line = re.sub(r'^[$>]\s*', '', line)
                    line = line.strip('`').strip()
                    if line:
                        commands.append(line)

                if not commands:
                    self.terminal.appendPlainText(f"\n[AI] {response}\n")
                    return

                # Run all commands chained
                cmd = " && ".join(commands)
                self.terminal.appendPlainText(f"⚡ Running: {cmd}\n")
                self._execute_command(cmd)
            except Exception as e:
                self.terminal.appendPlainText(f"\n[Error] {e}\n")
                self._set_running(False)

        thread.finished.connect(on_done)
        thread.start()
        self._ai_thread = thread

    # ═══════════════════════════════════════
    #  WIFI ADAPTER SELECTION
    # ═══════════════════════════════════════

    WIFI_TOOLS = {"airmon-ng", "airodump-ng", "aireplay-ng", "wifite", "wash", "reaver", "airbase-ng"}

    def _detect_wifi_interfaces(self):
        """Detect available wireless interfaces."""
        try:
            result = subprocess.run(
                "iw dev 2>/dev/null | grep Interface | awk '{print $2}'",
                shell=True, capture_output=True, text=True, timeout=5
            )
            ifaces = [i.strip() for i in result.stdout.strip().split('\n') if i.strip()]
            if not ifaces:
                # Fallback: check /sys/class/net
                result2 = subprocess.run(
                    "ls /sys/class/net/ | grep -E '^wl'",
                    shell=True, capture_output=True, text=True, timeout=5
                )
                ifaces = [i.strip() for i in result2.stdout.strip().split('\n') if i.strip()]
            return ifaces
        except Exception:
            return []

    def _select_wifi_adapter(self):
        """Auto-select external WiFi adapter for monitor mode.
        Always picks the external adapter (not wlan0/internal).
        Returns (monitor_iface, keep_iface)."""
        ifaces = self._detect_wifi_interfaces()

        if not ifaces:
            QMessageBox.warning(self, "No WiFi Adapter",
                "No wireless interfaces found.\n\nMake sure an external WiFi adapter is connected.")
            return None, None

        if len(ifaces) == 1:
            return ifaces[0], None

        # Auto-pick external adapter (not wlan0 = internal)
        # External adapters are typically wlan1, wlan2, etc.
        external = [i for i in ifaces if i != "wlan0"]
        internal = [i for i in ifaces if i == "wlan0"]

        if external:
            monitor_iface = external[0]
            keep_iface = internal[0] if internal else None
        else:
            monitor_iface = ifaces[0]
            keep_iface = ifaces[1] if len(ifaces) > 1 else None

        return monitor_iface, keep_iface

    def _is_wifi_command(self, cmd):
        """Check if command involves WiFi tools that need monitor mode."""
        parts = re.split(r'[;&|]+', cmd)
        for part in parts:
            words = part.strip().split()
            if not words:
                continue
            tool = words[0]
            if tool == "sudo" and len(words) > 1:
                tool = words[1]
            if tool in self.WIFI_TOOLS:
                return True
        return False

    def _detect_monitor_name(self, iface):
        """After airmon-ng start, the monitor interface is either
        the same name (wlan1) or with 'mon' appended (wlan1mon).
        Check which one actually exists."""
        try:
            # Check if wlan1mon exists
            code, out, _ = self.runner.run(f"ip link show {iface}mon 2>/dev/null")
            if code == 0 and f"{iface}mon" in out:
                return f"{iface}mon"
        except Exception:
            pass
        # Default: adapter keeps its name in monitor mode
        return iface

    def _replace_wifi_iface(self, cmd, iface, mon_name):
        """Replace wlan0/wlan0mon in command with the selected interfaces."""
        # Replace wlan0mon with the monitor interface (could be wlan1 or wlan1mon)
        cmd = cmd.replace("wlan0mon", mon_name)
        # Replace remaining wlan0 references with monitor interface too
        # (for tools that use the base name, e.g. airmon-ng start wlan0)
        cmd = re.sub(r'\bwlan0\b', mon_name, cmd)
        return cmd

    def _start_monitor_mode(self, iface, keep_iface):
        """Start monitor mode on selected adapter, keep other adapter working.
        Returns the monitor interface name."""
        self.terminal.appendPlainText(f"\n[WiFi] Starting monitor mode on {iface}...\n")
        if keep_iface:
            self.terminal.appendPlainText(f"[WiFi] Keeping {keep_iface} for regular WiFi.\n")

        # Use the process runner (has sudo password) for all commands
        # Step 1: Kill interfering processes
        code, out, _ = self.runner.run(f"sudo airmon-ng check kill")
        if out.strip():
            self.terminal.appendPlainText(out)

        # Step 2: Start monitor mode
        code, out, _ = self.runner.run(f"sudo airmon-ng start {iface}")
        if out.strip():
            self.terminal.appendPlainText(out)

        # Step 3: Detect actual monitor interface name
        # Use iw dev / iwconfig to find which interface is actually in monitor mode
        mon_name = self._detect_monitor_name(iface)

        # Step 4: Restart NetworkManager so the other adapter reconnects
        if keep_iface:
            self.runner.run("sudo systemctl restart NetworkManager")
            self.terminal.appendPlainText(f"[WiFi] NetworkManager restarted — {keep_iface} reconnecting.\n")

        self.terminal.appendPlainText(f"[WiFi] Monitor interface: {mon_name}\n\n")
        return mon_name

    def _restore_network(self):
        """Restore network after monitor mode and reset adapter selection."""
        mon = getattr(self, '_monitor_iface_name', None)
        iface = getattr(self, '_selected_wifi_iface', 'wlan0')
        self._wifi_adapter_selected = False
        self._monitor_iface_name = None
        stop_cmd = f"sudo airmon-ng stop {mon} 2>/dev/null; " if mon else ""
        self._execute_command(
            f"{stop_cmd}"
            f"sudo systemctl restart NetworkManager; "
            f"sudo systemctl restart wpa_supplicant; "
            f"sudo dhclient"
        )

    def _capture_handshake(self, essid):
        """Full handshake capture workflow: scan → find target → capture → save to MAXIMHASH.
        Always uses external adapter (wlan1). No popups."""
        import tempfile

        # Always use wlan1 for monitor mode
        mon = "wlan1"
        out_dir = os.path.expanduser("~/Desktop/MAXIMHASH")
        os.makedirs(out_dir, exist_ok=True)

        self.terminal.appendPlainText(f"\n{'═'*60}")
        self.terminal.appendPlainText(f"  HANDSHAKE CAPTURE: {essid}")
        self.terminal.appendPlainText(f"  Interface: {mon}")
        self.terminal.appendPlainText(f"{'═'*60}\n")

        # Ensure monitor mode on wlan1
        self.terminal.appendPlainText(f"[1/5] Enabling monitor mode on {mon}...\n")
        QApplication.processEvents()

        # Build sudo prefix
        sudo_prefix = "sudo"
        if self.runner._sudo_password:
            pw = self.runner._escape_pw()
            sudo_prefix = f"echo '{pw}' | sudo -S"

        # Kill interfering processes and start monitor mode
        subprocess.run(f"{sudo_prefix} airmon-ng check kill 2>/dev/null",
                      shell=True, capture_output=True, timeout=10)
        subprocess.run(f"{sudo_prefix} airmon-ng start {mon} 2>/dev/null",
                      shell=True, capture_output=True, timeout=10)
        # Restart NetworkManager for wlan0
        subprocess.run(f"{sudo_prefix} systemctl restart NetworkManager 2>/dev/null",
                      shell=True, capture_output=True, timeout=10)

        self.terminal.appendPlainText(f"[2/5] Scanning for '{essid}'... (20 seconds)\n")
        QApplication.processEvents()

        # Scan all networks for 20 seconds
        scan_file = "/tmp/maxim_hscan"
        subprocess.run(f"rm -f {scan_file}-* 2>/dev/null", shell=True)
        try:
            subprocess.run(
                f"{sudo_prefix} timeout 20 airodump-ng -w '{scan_file}' --output-format csv --write-interval 1 {mon} 2>/dev/null",
                shell=True, capture_output=True, timeout=25
            )
        except subprocess.TimeoutExpired:
            pass

        # Parse CSV to find BSSID and channel
        bssid = None
        channel = None
        csv_file = f"{scan_file}-01.csv"
        try:
            with open(csv_file, 'r', errors='replace') as f:
                lines = f.readlines()
                self.terminal.appendPlainText(f"[*] Scan found {len(lines)} lines in CSV\n")
                for line in lines:
                    # Case-insensitive ESSID match
                    if essid.lower() in line.lower():
                        parts = line.strip().split(',')
                        if len(parts) >= 14:
                            candidate_bssid = parts[0].strip()
                            candidate_channel = parts[3].strip()
                            if re.match(r'^([0-9A-Fa-f]{2}:){5}[0-9A-Fa-f]{2}$', candidate_bssid):
                                bssid = candidate_bssid
                                channel = candidate_channel.strip()
                                self.terminal.appendPlainText(f"[*] Match: BSSID={bssid} CH={channel}\n")
                                break
        except FileNotFoundError:
            self.terminal.appendPlainText(f"[!] Scan CSV file not created — airodump-ng may have failed.\n")
            self.terminal.appendPlainText(f"[!] Check that {mon} is in monitor mode: iwconfig {mon}\n")
            return
        except Exception as e:
            self.terminal.appendPlainText(f"[!] Error reading scan: {e}\n")
            return

        # Cleanup scan files
        subprocess.run(f"rm -f {scan_file}-* 2>/dev/null", shell=True)

        if not bssid or not channel:
            self.terminal.appendPlainText(f"\n[!] Could not find network '{essid}'.\n")
            self.terminal.appendPlainText(f"[!] Make sure '{essid}' is in range and broadcasting.\n")
            self.terminal.appendPlainText(f"[!] Try: sudo airodump-ng {mon}  (to see all networks)\n")
            return

        self.terminal.appendPlainText(f"\n[3/5] Found: BSSID={bssid}  Channel={channel}\n")

        # Write capture + deauth script
        safe_essid = essid.replace(' ', '_').replace("'", "").replace('"', '')
        capture_prefix = f"{out_dir}/{safe_essid}"

        script = tempfile.NamedTemporaryFile(mode='w', suffix='.sh', delete=False, prefix='maxim_hs_')
        script.write("#!/bin/bash\n")
        script.write(f"echo ''\n")
        script.write(f"echo '══════════════════════════════════════════'\n")
        script.write(f"echo '  CAPTURING HANDSHAKE: {essid}'\n")
        script.write(f"echo '  BSSID: {bssid}  Channel: {channel}'\n")
        script.write(f"echo '  Output: {out_dir}/'\n")
        script.write(f"echo '══════════════════════════════════════════'\n")
        script.write(f"echo ''\n")
        script.write(f"echo '[*] Starting capture + deauth...'\n")
        script.write(f"echo '[*] Wait for WPA handshake message, then Ctrl+C'\n")
        script.write(f"echo ''\n\n")
        # Deauth in background
        script.write(f"(\n")
        script.write(f"  sleep 5\n")
        script.write(f"  for i in 1 2 3 4 5 6 7 8 9 10; do\n")
        script.write(f"    sudo aireplay-ng --deauth 10 -a {bssid} {mon} 2>/dev/null\n")
        script.write(f"    sleep 8\n")
        script.write(f"  done\n")
        script.write(f") &\n")
        script.write(f"DEAUTH_PID=$!\n\n")
        # Capture
        script.write(f"sudo airodump-ng -c {channel} --bssid {bssid} -w '{capture_prefix}' {mon}\n\n")
        script.write(f"kill $DEAUTH_PID 2>/dev/null\n")
        script.write(f"echo ''\n")
        script.write(f"echo 'Capture files:'\n")
        script.write(f"ls -la {capture_prefix}* 2>/dev/null\n")
        script.write(f"echo ''\necho 'Press Enter to close'\nread\n")
        script.close()
        os.chmod(script.name, 0o755)

        self.terminal.appendPlainText(f"[4/5] Opening capture terminal...\n")
        self.terminal.appendPlainText(f"[5/5] Capture files → {out_dir}/\n\n")

        self.runner.run_in_terminal(f"bash '{script.name}'")

    # ═══════════════════════════════════════
    #  COMMAND EXECUTION
    # ═══════════════════════════════════════

    SUDO_TOOLS = {
        "nmap", "masscan", "netdiscover", "airmon-ng", "airodump-ng",
        "aireplay-ng", "aircrack-ng", "wifite", "reaver", "bettercap",
        "ettercap", "tcpdump", "macchanger", "responder", "arp-scan",
    }

    def _execute_command(self, cmd, as_root=False):
        # WiFi adapter selection — ask which adapter for monitor mode
        if self._is_wifi_command(cmd):
            if not getattr(self, '_wifi_adapter_selected', False):
                iface, keep = self._select_wifi_adapter()
                if iface is None:
                    self.terminal.appendPlainText("\n[!] WiFi operation cancelled.\n")
                    return
                self._selected_wifi_iface = iface
                self._keep_wifi_iface = keep
                self._wifi_adapter_selected = True

                # Start monitor mode and detect actual mon interface name
                mon_name = self._start_monitor_mode(iface, keep)
                self._monitor_iface_name = mon_name

            mon_name = getattr(self, '_monitor_iface_name', f"{self._selected_wifi_iface}mon")
            # Replace interface names in command
            cmd = self._replace_wifi_iface(cmd, self._selected_wifi_iface, mon_name)
            # Remove airmon-ng check kill / airmon-ng start from command — already done
            cmd = re.sub(r'sudo\s+airmon-ng\s+check\s+kill\s*[;&|]*\s*', '', cmd)
            cmd = re.sub(r'sudo\s+airmon-ng\s+start\s+\S+\s*[;&|]*\s*', '', cmd)
            cmd = cmd.strip().strip(';&|').strip()
        # Auto-add sudo
        if not cmd.strip().startswith("sudo ") and not cmd.strip().startswith("echo "):
            first_word = cmd.strip().split()[0] if cmd.strip() else ""
            if first_word in self.SUDO_TOOLS or as_root:
                cmd = f"sudo {cmd}"

        # Reset brute force state for new crack commands
        is_crack = any(t in cmd for t in ["john ", "hashcat ", "aircrack-ng "])
        if is_crack and not getattr(self, '_is_bruteforcing', False):
            self._is_bruteforcing = False

        self._set_running(True, f"Running: {cmd[:60]}...")

        self.terminal.appendPlainText(f"\n{'─'*60}")
        self.terminal.appendPlainText(f" [{datetime.now().strftime('%H:%M:%S')}]  $ {cmd}")
        self.terminal.appendPlainText(f"{'─'*60}\n")
        scrollbar = self.terminal.verticalScrollBar()
        scrollbar.setValue(scrollbar.maximum())

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
        scrollbar = self.terminal.verticalScrollBar()
        scrollbar.setValue(scrollbar.maximum())

    def _on_command_done(self, cmd, exit_code, duration):
        status = "OK" if exit_code == 0 else f"FAILED (exit {exit_code})"
        self.terminal.appendPlainText(f"\n[{status}] {duration:.1f}s\n")
        self._set_running(False)
        self.statusBar().showMessage(f"{status} -- {duration:.1f}s")
        scrollbar = self.terminal.verticalScrollBar()
        scrollbar.setValue(scrollbar.maximum())

        tool_name = cmd.split()[0].split("/")[-1] if cmd else "unknown"
        self.session.log_command(cmd, tool_name, exit_code, duration)
        self.cmd_count_label.setText(f"{len(self.session.commands)} commands")

        # If cracking finished with no password found, offer brute force
        is_crack_cmd = any(t in cmd for t in ["john ", "hashcat ", "aircrack-ng "])
        if is_crack_cmd and not getattr(self, '_is_bruteforcing', False):
            # Check if password was actually cracked in the output
            text = self.terminal.toPlainText()[-1000:]
            found = (
                re.search(r'KEY FOUND!\s*\[', text) or
                re.search(r'\d+ password hash(?:es)? cracked', text) or
                re.search(r'^\?:.+', text, re.MULTILINE)
            )
            if not found:
                self._offer_brute_force(cmd)

    def _offer_brute_force(self, original_cmd):
        """No password found — ask user if they want to brute force."""
        reply = QMessageBox.question(self, "No Password Found",
            "Wordlists didn't crack it.\n\nDo you want to BRUTE FORCE it?\n\n"
            "Stage 1: Digits (0-9) up to 12 chars — 2 min\n"
            "Stage 2: Lowercase (a-z) up to 8 chars — 3 min\n"
            "Stage 3: Letters (a-zA-Z) up to 7 chars — 3 min\n"
            "Stage 4: Alphanumeric up to 6 chars — 5 min\n"
            "Stage 5: ALL printable up to 5 chars — 5 min\n\n"
            "Stops early if password is found.",
            QMessageBox.Yes | QMessageBox.No, QMessageBox.Yes)
        if reply != QMessageBox.Yes:
            return

        # Extract the file path from the original command
        m = re.search(r"'([^']+)'", original_cmd)
        if not m:
            m = re.search(r'\s(\S+\.\S+)', original_cmd)
        if not m:
            self.terminal.appendPlainText("[!] Could not determine file to brute force\n")
            return
        filepath = m.group(1)

        # Detect john format from original command
        fmt_match = re.search(r'--format=(\S+)', original_cmd)
        john_fmt = fmt_match.group(1) if fmt_match else None
        fmt_flag = f"--format={john_fmt} " if john_fmt else ""

        self._is_bruteforcing = True
        self.terminal.appendPlainText("\n\n  BRUTEFORCING NOW...\n\n")

        # John the Ripper staged brute force using --incremental modes
        # John's Incremental mode is its optimized brute force engine.
        # It uses Markov chains to try most likely passwords first.
        #
        # Built-in incremental modes (defined in john.conf):
        #   Digits   — 0-9 only
        #   Lower    — a-z only
        #   Alpha    — a-zA-Z
        #   Alnum    — a-zA-Z0-9
        #   ASCII    — all printable ASCII (95 chars)
        #
        # --max-run-time=N  stops after N seconds (prevents running forever)
        # --max-length=N    limits password length to try
        #
        # After each stage, check if cracked. If yes, stop early.

        check = f"john {fmt_flag}--show '{filepath}' 2>/dev/null | grep -c ':'"

        stages = [
            ("Stage 1: Digits only (0-9), up to 12 chars, 2 min",
             f"john {fmt_flag}--incremental=Digits --max-length=12 --max-run-time=120 '{filepath}'"),
            ("Stage 2: Lowercase (a-z), up to 8 chars, 3 min",
             f"john {fmt_flag}--incremental=Lower --max-length=8 --max-run-time=180 '{filepath}'"),
            ("Stage 3: Letters (a-zA-Z), up to 7 chars, 3 min",
             f"john {fmt_flag}--incremental=Alpha --max-length=7 --max-run-time=180 '{filepath}'"),
            ("Stage 4: Alphanumeric (a-zA-Z0-9), up to 6 chars, 5 min",
             f"john {fmt_flag}--incremental=Alnum --max-length=6 --max-run-time=300 '{filepath}'"),
            ("Stage 5: ALL printable chars, up to 5 chars, 5 min",
             f"john {fmt_flag}--incremental=ASCII --max-length=5 --max-run-time=300 '{filepath}'"),
        ]

        # Write brute force stages to a temp script for clean execution
        import tempfile
        script = tempfile.NamedTemporaryFile(mode='w', suffix='.sh', delete=False, prefix='maxim_brute_')
        script.write("#!/bin/bash\n")
        for label, stage_cmd in stages:
            script.write(f"\necho ''\necho '--- {label} ---'\n")
            script.write(f"{stage_cmd}\n")
            script.write(f"FOUND=$({check})\n")
            script.write(f"if [ \"$FOUND\" -gt 0 ] 2>/dev/null; then\n")
            script.write(f"  echo ''\n  echo 'PASSWORD CRACKED!'\n")
            script.write(f"  john {fmt_flag}--show '{filepath}'\n")
            script.write(f"  exit 0\nfi\n")
        script.write(f"\necho ''\necho '--- Brute Force Complete ---'\n")
        script.write(f"john {fmt_flag}--show '{filepath}'\n")
        script.close()
        import stat
        os.chmod(script.name, os.stat(script.name).st_mode | stat.S_IEXEC)

        self._execute_command(f"bash '{script.name}'")

    def _on_file_dropped(self, filepath):
        """Handle file dropped onto the terminal."""
        self._analyze_file(filepath)

    def _load_file(self):
        """Load a file via file dialog."""
        filepath, _ = QFileDialog.getOpenFileName(
            self, "Load File for Analysis",
            os.path.expanduser("~"),
            "All Supported (*.cap *.pcap *.hc22000 *.hccapx *.txt *.hash *.csv *.xml);;Capture Files (*.cap *.pcap);;Hash Files (*.txt *.hash *.hc22000 *.hccapx);;All Files (*)"
        )
        if not filepath:
            return
        self._analyze_file(filepath)

    # Wordlists in order of priority — tries each until cracked
    WORDLISTS = [
        "/usr/share/wordlists/rockyou.txt",
        "/usr/share/wordlists/seclists/Passwords/Common-Credentials/10-million-password-list-top-1000000.txt",
        "/usr/share/seclists/Passwords/Common-Credentials/10-million-password-list-top-1000000.txt",
        "/usr/share/wordlists/seclists/Passwords/xato-net-10-million-passwords-1000000.txt",
        "/usr/share/seclists/Passwords/xato-net-10-million-passwords-1000000.txt",
        "/usr/share/wordlists/seclists/Passwords/darkweb2017-top10000.txt",
        "/usr/share/seclists/Passwords/darkweb2017-top10000.txt",
        "/usr/share/wordlists/wifite.txt",
        "/usr/share/wordlists/fasttrack.txt",
        "/usr/share/wordlists/metasploit/password.lst",
        "/usr/share/john/password.lst",
    ]

    def _get_wordlists(self):
        """Return all existing wordlists: rockyou first, then extras, then downloaded/custom."""
        existing = []
        # 1. Main wordlist — rockyou.txt
        for wl in self.WORDLISTS:
            if os.path.exists(wl):
                existing.append(wl)
        # 2. Scan for any extra downloaded or custom wordlists
        extra_dirs = [
            "/usr/share/wordlists",
            "/usr/share/seclists/Passwords",
            os.path.expanduser("~/wordlists"),
            os.path.expanduser("~/Desktop/wordlists"),
        ]
        for d in extra_dirs:
            if os.path.isdir(d):
                try:
                    for f in os.listdir(d):
                        fp = os.path.join(d, f)
                        if fp not in existing and os.path.isfile(fp) and f.endswith(('.txt', '.lst')):
                            existing.append(fp)
                except Exception:
                    pass
        return existing if existing else ["/usr/share/wordlists/rockyou.txt"]

    def _build_crack_cmd(self, tool, filepath, hash_format=None):
        """Build crack command: rockyou.txt first, then all other wordlists if no result."""
        wordlists = self._get_wordlists()
        # Ensure rockyou is first
        rockyou = "/usr/share/wordlists/rockyou.txt"
        if rockyou in wordlists:
            wordlists.remove(rockyou)
            wordlists.insert(0, rockyou)

        if tool == "aircrack":
            if len(wordlists) > 1:
                combined = "' -w '".join(wordlists)
                return f"sudo aircrack-ng -w '{combined}' '{filepath}'"
            return f"sudo aircrack-ng -w '{wordlists[0]}' '{filepath}'"

        elif tool == "john":
            # Stage 1: rockyou.txt with rules
            fmt = f"--format={hash_format} " if hash_format else ""
            cmds = [f"john {fmt}--wordlist='{wordlists[0]}' --rules=best64 '{filepath}'"]
            # Stage 2: all other wordlists (if rockyou didn't crack it)
            for wl in wordlists[1:]:
                cmds.append(f"john {fmt}--wordlist='{wl}' '{filepath}'")
            # Show results
            cmds.append(f"john {fmt}--show '{filepath}'")
            return " ; ".join(cmds)

        elif tool == "hashcat":
            cmds = []
            # Stage 1: rockyou.txt with rules
            cmds.append(f"hashcat -m {hash_format} '{filepath}' '{wordlists[0]}' -r /usr/share/hashcat/rules/best64.rule --force 2>/dev/null")
            # Stage 2: all other wordlists
            for wl in wordlists[1:]:
                cmds.append(f"hashcat -m {hash_format} '{filepath}' '{wl}' --force 2>/dev/null")
            cmds.append(f"hashcat -m {hash_format} '{filepath}' --show 2>/dev/null")
            return " ; ".join(cmds)

        return ""

    def _analyze_file(self, filepath):
        """Auto-detect file type and crack/analyze immediately — no popups."""
        self._is_bruteforcing = False
        ext = os.path.splitext(filepath)[1].lower()
        fname = os.path.basename(filepath)

        if ext in ('.cap', '.pcap'):
            # WiFi capture — auto crack with all wordlists
            wl_count = len(self._get_wordlists())
            self.terminal.appendPlainText(f"\n⚡ Cracking WPA from {fname} using {wl_count} wordlists...\n")
            self._execute_command(self._build_crack_cmd("aircrack", filepath))

        elif ext in ('.hc22000', '.hccapx'):
            # Hashcat WiFi format — multi wordlist + rules + brute force
            wl_count = len(self._get_wordlists())
            self.terminal.appendPlainText(f"\n⚡ Cracking {fname} with hashcat ({wl_count} wordlists + rules + brute force)...\n")
            self._execute_command(self._build_crack_cmd("hashcat", filepath, "22000"))

        elif ext in ('.txt', '.hash'):
            # Hash file — auto-detect hash type and crack
            # Read first line to detect type
            self.terminal.appendPlainText(f"\n⚡ Auto-detecting hash type in {fname}...\n")
            try:
                with open(filepath, 'r') as f:
                    first_line = f.readline().strip()
            except Exception:
                first_line = ""

            if not first_line:
                self.terminal.appendPlainText("[!] Empty file\n")
                return

            hash_len = len(first_line.split(':')[0]) if ':' in first_line else len(first_line)

            # Auto-detect by hash length
            wl_count = len(self._get_wordlists())

            if hash_len == 32:
                self.terminal.appendPlainText(f"Detected: MD5 (32 chars) — {wl_count} wordlists + rules\n")
                self._execute_command(self._build_crack_cmd("john", filepath, "Raw-MD5"))
            elif hash_len == 40:
                self.terminal.appendPlainText(f"Detected: SHA1 (40 chars) — {wl_count} wordlists + rules\n")
                self._execute_command(self._build_crack_cmd("john", filepath, "Raw-SHA1"))
            elif hash_len == 64:
                self.terminal.appendPlainText(f"Detected: SHA256 (64 chars) — {wl_count} wordlists + rules\n")
                self._execute_command(self._build_crack_cmd("john", filepath, "Raw-SHA256"))
            elif hash_len == 128:
                self.terminal.appendPlainText(f"Detected: SHA512 (128 chars) — {wl_count} wordlists + rules\n")
                self._execute_command(self._build_crack_cmd("john", filepath, "Raw-SHA512"))
            elif first_line.startswith('$2') or first_line.startswith('$2b$'):
                self.terminal.appendPlainText(f"Detected: bcrypt — {wl_count} wordlists + rules + brute force\n")
                self._execute_command(self._build_crack_cmd("hashcat", filepath, "3200"))
            elif first_line.startswith('$6$'):
                self.terminal.appendPlainText(f"Detected: SHA512crypt — {wl_count} wordlists + rules + brute force\n")
                self._execute_command(self._build_crack_cmd("hashcat", filepath, "1800"))
            elif first_line.startswith('$5$'):
                self.terminal.appendPlainText(f"Detected: SHA256crypt — {wl_count} wordlists + rules + brute force\n")
                self._execute_command(self._build_crack_cmd("hashcat", filepath, "7400"))
            elif first_line.startswith('$1$'):
                self.terminal.appendPlainText(f"Detected: MD5crypt — {wl_count} wordlists + rules + brute force\n")
                self._execute_command(self._build_crack_cmd("hashcat", filepath, "500"))
            else:
                self.terminal.appendPlainText(f"Unknown hash type ({hash_len} chars) — trying all methods\n")
                self._execute_command(self._build_crack_cmd("john", filepath))

        elif ext in ('.csv', '.xml'):
            # Scan results
            self.terminal.appendPlainText(f"\n⚡ Showing {fname}...\n")
            self._execute_command(f"cat '{filepath}' | head -100")

        else:
            # Unknown — let AI decide
            self._ai_execute(f"analyze this file: {filepath}")

    def _on_stop(self):
        self.runner.kill_all()
        self.terminal.appendPlainText("\n[KILLED] Process terminated.\n")
        self._set_running(False)

    def _clear_terminal(self):
        self.terminal.clear()

    def _add_word_to_wordlist_btn(self):
        """Add a new wordlist .txt file to /usr/share/wordlists/."""
        filepath, _ = QFileDialog.getOpenFileName(
            self, "Select Wordlist File to Add",
            os.path.expanduser("~"),
            "Wordlists (*.txt *.lst);;All Files (*)")
        if filepath:
            fname = os.path.basename(filepath)
            self._execute_command(
                f"sudo cp '{filepath}' '/usr/share/wordlists/{fname}' && "
                f"echo 'Added wordlist: /usr/share/wordlists/{fname}' && "
                f"wc -l '/usr/share/wordlists/{fname}'"
            )

    def _add_word_to_wordlist(self, filepath):
        """Add a word/password to a wordlist file."""
        word, ok = QInputDialog.getText(self, "Add Word",
            f"Enter word/password to add to:\n{filepath}")
        if ok and word.strip():
            self._execute_command(
                f"sudo gzip -d '{filepath}.gz' 2>/dev/null; "
                f"echo '{word.strip()}' | sudo tee -a '{filepath}' && "
                f"echo 'Added: {word.strip()}'"
            )

    def _add_word_to_custom_wordlist(self):
        """Add a word to a custom wordlist file chosen by user."""
        filepath, _ = QFileDialog.getOpenFileName(
            self, "Select Wordlist", "/usr/share/wordlists",
            "Wordlists (*.txt *.lst);;All Files (*)")
        if filepath:
            self._add_word_to_wordlist(filepath)

    # ═══════════════════════════════════════
    #  PLACEHOLDERS
    # ═══════════════════════════════════════

    def _extract_target_from_query(self, query):
        ip_match = re.search(r'\b(\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}(?:/\d{1,2})?)\b', query)
        if ip_match:
            return ip_match.group(1)
        domain_match = re.search(r'\b([a-zA-Z0-9][-a-zA-Z0-9]*\.[a-zA-Z]{2,}(?:\.[a-zA-Z]{2,})?)\b', query)
        if domain_match:
            candidate = domain_match.group(1)
            if candidate not in {'example.com', 'wlan0.mon'}:
                return candidate
        return None

    def _fill_placeholders(self, cmd_template, query=""):
        extracted = self._extract_target_from_query(query) if query else None
        defaults = {
            "iface": "wlan0", "target": extracted or "192.168.1.1",
            "port": "4444", "lhost": "0.0.0.0", "lport": "4444",
            "domain": extracted or "example.com",
            "user": "admin", "wordlist": "/usr/share/wordlists/rockyou.txt",
            "hashfile": "hashes.txt", "hash_file": "hashes.txt",
            "query": "apache", "bssid": "FF:FF:FF:FF:FF:FF",
            "min": "8", "max": "12", "charset": "abcdefghijklmnopqrstuvwxyz0123456789",
            "file": "target_file", "image": "/dev/sda1", "dump": "memory.dmp",
            "subnet": "192.168.1.0/24", "url": extracted or "http://192.168.1.1",
            "cap_file": "capture.cap", "channel": "6",
            "module": "exploit/multi/handler", "payload": "linux/x64/meterpreter/reverse_tcp",
            "format": "elf", "id": "1", "pass": "password",
            "mode": "0", "path": "/login", "params": "user=admin&pass=^PASS^",
            "fail_string": "Invalid", "gateway": "192.168.1.1",
            "binary": "target_binary", "command": "nmap -sV 192.168.1.1",
            "name": "session1", "rhost": "127.0.0.1", "rport": "8080",
            "data": "key=value", "server": "192.168.1.1",
        }
        cmd = cmd_template
        for ph, val in defaults.items():
            cmd = cmd.replace(f"{{{ph}}}", val)
        return cmd

    # ═══════════════════════════════════════
    #  AI CHAT
    # ═══════════════════════════════════════

    def _on_ai_submit(self):
        msg = self.ai_input.text().strip()
        if not msg:
            return
        self.ai_input.clear()
        self.ai_input.setEnabled(False)

        safe_msg = html.escape(msg)
        self.ai_chat.append(
            f'<div style="background:#1e3a5f;border-radius:10px;padding:10px;margin:6px 40px 6px 6px;">'
            f'<b style="color:#60a5fa;">You:</b> '
            f'<span style="color:#fafafa;font-size:15px;">{safe_msg}</span></div>'
        )

        if not self.ai or not self.ai.is_available():
            route = SmartRouter.route(msg)
            if route["tools"]:
                parts = []
                for t in route["tools"]:
                    parts.append(f"<b>{t['name']}</b> -- {t['description']}<br>")
                    for cc in t["common_commands"][:3]:
                        parts.append(f"&nbsp;&nbsp;<code>{cc['cmd']}</code><br>")
                reply = "".join(parts)
            elif route["direct_command"]:
                reply = f"Run: <code>{route['direct_command']}</code>"
            else:
                reply = ("No AI available. Set up in AI menu:<br>"
                         "- <b>Offline:</b> <code>ollama serve</code><br>"
                         "- <b>Online:</b> AI > Set API Key")

            self.ai_chat.append(
                f'<div style="background:#18181b;border-radius:10px;padding:10px;margin:6px 6px 6px 40px;">'
                f'<b style="color:#facc15;">Maxim:</b> {reply}</div>'
            )
            self.ai_input.setEnabled(True)
            self.ai_input.setFocus()
            return

        provider_tag = self.ai.provider_name

        # Animated loading indicator
        self._ai_loading_dots = 0
        self._ai_loading_id = "ai-loading-" + str(id(msg))
        self.ai_chat.append(
            f'<div id="{self._ai_loading_id}" style="background:#18181b;border-radius:10px;padding:10px;margin:6px 6px 2px 40px;">'
            f'<span style="color:#3b82f6;">⚡ Thinking</span> '
            f'<span style="color:#52525b;font-size:11px;">via {provider_tag}</span></div>'
        )

        # Pulsing dots animation
        self._ai_loading_timer = QTimer()
        self._ai_loading_base_text = f'<div style="background:#18181b;border-radius:10px;padding:10px;margin:6px 6px 2px 40px;">'
        def update_dots():
            self._ai_loading_dots = (self._ai_loading_dots + 1) % 4
            dots = "." * self._ai_loading_dots + " " * (3 - self._ai_loading_dots)
            # Remove last block and replace with updated dots
            cursor = self.ai_chat.textCursor()
            cursor.movePosition(QTextCursor.End)
            self.ai_chat.setTextCursor(cursor)
        self._ai_loading_timer.timeout.connect(update_dots)
        self._ai_loading_timer.start(400)

        # Stream tokens into chat
        self._ai_stream_buffer = []
        self._ai_streaming_started = False

        self._ai_thread = AIStreamSignal(self.ai, msg)

        def on_token(token):
            if not self._ai_streaming_started:
                self._ai_streaming_started = True
                self._ai_loading_timer.stop()
                # Replace loading message with start of response
                self.ai_chat.append(
                    f'<div style="background:#18181b;border-radius:10px;padding:10px;margin:6px 6px 6px 40px;">'
                    f'<b style="color:#4ade80;">Maxim AI</b> '
                    f'<span style="color:#52525b;font-size:11px;">via {provider_tag}</span><br>'
                    f'<span style="color:#e4e4e7;font-size:14px;">'
                )
            self._ai_stream_buffer.append(token)

        def on_done(full):
            self._ai_loading_timer.stop()
            self.ai_input.setEnabled(True)
            self.ai_input.setFocus()

            if not self._ai_streaming_started:
                # Never got streaming tokens, show full response
                text = html.escape(full).replace("\n", "<br>")
                self.ai_chat.append(
                    f'<div style="background:#18181b;border-radius:10px;padding:10px;margin:6px 6px 6px 40px;">'
                    f'<b style="color:#4ade80;">Maxim AI</b> '
                    f'<span style="color:#52525b;font-size:11px;">via {provider_tag}</span><br>'
                    f'<span style="color:#e4e4e7;font-size:14px;">{text}</span></div>'
                )
            else:
                # Finalize streamed response
                text = html.escape(full).replace("\n", "<br>")
                self.ai_chat.append(
                    f'<div style="background:#18181b;border-radius:10px;padding:10px;margin:6px 6px 6px 40px;">'
                    f'<b style="color:#4ade80;">Maxim AI</b> '
                    f'<span style="color:#52525b;font-size:11px;">via {provider_tag}</span><br>'
                    f'<span style="color:#e4e4e7;font-size:14px;">{text}</span></div>'
                )

        self._ai_thread.token_received.connect(on_token)
        self._ai_thread.finished.connect(on_done)
        self._ai_thread.start()

    # ═══════════════════════════════════════
    #  AI MANAGEMENT
    # ═══════════════════════════════════════

    def _set_api_key_dialog(self):
        providers = [(pid, p["name"]) for pid, p in PROVIDERS.items() if p["type"] == "online"]
        names = [n for _, n in providers]
        choice, ok = QInputDialog.getItem(self, "Select Provider", "Provider:", names, 0, False)
        if not ok:
            return
        pid = providers[names.index(choice)][0]
        prov = PROVIDERS[pid]

        key, ok = QInputDialog.getText(
            self, f"API Key -- {prov['name']}",
            f"Enter API key for {prov['name']}:\nGet one at: {prov.get('key_url', 'N/A')}",
            QLineEdit.Normal, ""
        )
        if ok and key.strip():
            if not self.ai:
                self.ai = AIManager()
            self.ai.set_api_key(pid, key.strip())
            self.ai.switch_provider(pid)
            self._update_status()
            QMessageBox.information(self, "Saved", f"API key saved. Switched to {prov['name']}.")

    def _quick_switch_provider(self, pid):
        if not self.ai:
            self.ai = AIManager()
        self.ai.switch_provider(pid)
        self._update_status()
        prov = PROVIDERS.get(pid, {})
        if prov.get("needs_key") and not get_api_key(pid):
            self._set_api_key_dialog()

    def _update_status(self):
        if not self.ai:
            self.ai_status.setText("AI: Loading...")
            self.ai_status.setStyleSheet("color: #52525b; font-size: 13px; padding: 4px 14px; background: #18181b; border-radius: 12px;")
            return
        status = self.ai.get_status()
        if self.ai.is_available():
            self.ai_status.setText(f"AI: {status}")
            self.ai_status.setStyleSheet("color: #4ade80; font-size: 13px; padding: 4px 14px; background: #052e16; border-radius: 12px;")
        else:
            self.ai_status.setText(f"AI: {status}")
            self.ai_status.setStyleSheet("color: #facc15; font-size: 13px; padding: 4px 14px; background: #1c1917; border-radius: 12px;")

    # ═══════════════════════════════════════
    #  MISC
    # ═══════════════════════════════════════

    def _install_all_tools(self):
        pkgs = get_all_packages()
        self._execute_command(f"sudo apt-get install -y {' '.join(pkgs)}")

    def _new_session(self):
        self.session = Session()
        self.terminal.clear()
        self.cmd_count_label.setText("0 commands")

    def _check_updates(self):
        info = check_for_update()
        if info["available"]:
            reply = QMessageBox.question(
                self, "Update Available",
                f"Maxim v{info['latest']} available (you have v{info['current']}).\n\nUpdate now?",
                QMessageBox.Yes | QMessageBox.No
            )
            if reply == QMessageBox.Yes:
                self._execute_command(f"cd {os.path.dirname(os.path.dirname(os.path.abspath(__file__)))} && git pull origin main")
        else:
            QMessageBox.information(self, "Up to Date", f"Maxim v{info['current']} is the latest.")

    def _show_about(self):
        ver = get_current_version()
        QMessageBox.about(self, "About Maxim",
            f"<h2 style='color:#3b82f6;'>MAXIM v{ver}</h2>"
            "<p>Penetration Testing Command Center</p>"
            "<p>Type what you want. Maxim picks the tool and runs it.</p>"
        )

    def closeEvent(self, event):
        self.runner.kill_all()
        event.accept()
