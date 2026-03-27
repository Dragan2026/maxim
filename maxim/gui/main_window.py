"""
Maxim Main Window — clean CLI-style pentesting interface.
"""

import os
import re
import html
import webbrowser
import threading
from datetime import datetime
from functools import partial

from PyQt5.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QPlainTextEdit, QLineEdit, QPushButton, QLabel,
    QFrame, QComboBox, QMessageBox, QAction,
    QMenu, QMenuBar, QApplication, QInputDialog, QSplitter,
    QTextBrowser, QProgressBar,
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
        clear_btn = QPushButton("Clear")
        clear_btn.setStyleSheet("""
            QPushButton {
                background: transparent; border: 1px solid #27272a; color: #a1a1aa;
                border-radius: 8px; padding: 6px 14px; font-size: 14px; font-weight: 500;
            }
            QPushButton:hover { border-color: #3b82f6; color: #3b82f6; }
        """)
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

        self.terminal = QPlainTextEdit()
        self.terminal.setObjectName("terminal")
        self.terminal.setReadOnly(True)
        self.terminal.setFont(QFont("JetBrains Mono", 13))
        self.terminal.setPlaceholderText("Output will appear here...")
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

    def _on_prompt_submit(self):
        if self._running:
            return
        query = self.prompt_input.text().strip()
        if not query:
            return
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

        # 2. Everything else → AI decides what to do
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

        enhanced_query = (
            f"The user wants to: {query}\n\n"
            f"Give me the EXACT terminal command(s) to run on Kali Linux. "
            f"Put each command on its own line starting with $ sign. "
            f"Be brief — command first, short explanation after. "
            f"Pick the best tool, don't list alternatives. "
            f"If it's a scan, use nmap by default."
        )

        thread = AIStreamSignal(self.ai, enhanced_query)

        def on_token(token):
            self.terminal.moveCursor(QTextCursor.End)
            self.terminal.insertPlainText(token)
            self.terminal.moveCursor(QTextCursor.End)

        def on_done(response):
            self._set_running(False)
            if response.startswith("[Error]") or response.startswith("[AI Error]"):
                self.terminal.appendPlainText(f"\n{response}\n")
                return

            # Extract and auto-run commands
            commands = []
            for line in response.split("\n"):
                line = line.strip()
                if line.startswith("$ "):
                    commands.append(line[2:])
                elif re.match(r'^(sudo |nmap |airmon|airodump|hydra |sqlmap |nikto |gobuster |dirb |ffuf |masscan |whatweb |wpscan )', line):
                    commands.append(line)

            if commands:
                cmd = commands[0].strip()
                self.terminal.appendPlainText(f"\n\n⚡ Auto-running: {cmd}\n")
                self._execute_command(cmd)

        thread.token_received.connect(on_token)
        thread.finished.connect(on_done)
        thread.start()
        self._ai_thread = thread

    # ═══════════════════════════════════════
    #  COMMAND EXECUTION
    # ═══════════════════════════════════════

    SUDO_TOOLS = {
        "nmap", "masscan", "netdiscover", "airmon-ng", "airodump-ng",
        "aireplay-ng", "aircrack-ng", "wifite", "reaver", "bettercap",
        "ettercap", "tcpdump", "macchanger", "responder", "arp-scan",
    }

    def _execute_command(self, cmd, as_root=False):
        # Auto-add sudo
        if not cmd.strip().startswith("sudo ") and not cmd.strip().startswith("echo "):
            first_word = cmd.strip().split()[0] if cmd.strip() else ""
            if first_word in self.SUDO_TOOLS or as_root:
                cmd = f"sudo {cmd}"

        self._set_running(True, f"Running: {cmd[:60]}...")

        self.terminal.appendPlainText(f"\n{'─'*60}")
        self.terminal.appendPlainText(f" [{datetime.now().strftime('%H:%M:%S')}]  $ {cmd}")
        self.terminal.appendPlainText(f"{'─'*60}\n")

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
        self.terminal.appendPlainText(f"\n[{status}] {duration:.1f}s\n")
        self._set_running(False)
        self.statusBar().showMessage(f"{status} -- {duration:.1f}s")

        tool_name = cmd.split()[0].split("/")[-1] if cmd else "unknown"
        self.session.log_command(cmd, tool_name, exit_code, duration)
        self.cmd_count_label.setText(f"{len(self.session.commands)} commands")

    def _on_stop(self):
        self.runner.kill_all()
        self.terminal.appendPlainText("\n[KILLED] Process terminated.\n")
        self._set_running(False)

    def _clear_terminal(self):
        self.terminal.clear()

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
