"""
Maxim Core Engine — handles subprocess execution, logging, session management.
"""

import subprocess
import os
import re
import json
import time
import signal
import shutil
import threading
from datetime import datetime
from pathlib import Path

DATA_DIR = Path.home() / ".maxim"
LOG_DIR = DATA_DIR / "logs"
SESSIONS_DIR = DATA_DIR / "sessions"

# ANSI escape code regex
ANSI_RE = re.compile(r'\x1b\[[0-9;]*[a-zA-Z]|\x1b\[\?[0-9;]*[a-zA-Z]|\x1b\(B')

# Tools that MUST run in a real terminal (interactive/TUI tools)
TERMINAL_TOOLS = {
    "wifite", "msfconsole", "bettercap", "ettercap", "wireshark",
    "burpsuite", "zenmap", "maltego", "armitage",
}


def strip_ansi(text):
    """Remove ANSI escape codes from text."""
    return ANSI_RE.sub('', text)


def ensure_dirs():
    DATA_DIR.mkdir(exist_ok=True)
    LOG_DIR.mkdir(exist_ok=True)
    SESSIONS_DIR.mkdir(exist_ok=True)


ensure_dirs()


def _find_terminal():
    """Find available terminal emulator."""
    for term in ["qterminal", "xfce4-terminal", "gnome-terminal", "konsole", "xterm"]:
        if shutil.which(term):
            return term
    return "xterm"


class Session:
    """Tracks a single Maxim usage session."""

    def __init__(self):
        self.id = datetime.now().strftime("%Y%m%d_%H%M%S")
        self.started = datetime.now().isoformat()
        self.commands = []
        self.file = SESSIONS_DIR / f"session_{self.id}.json"

    def log_command(self, cmd: str, tool: str, exit_code: int, duration: float,
                    output_snippet: str = ""):
        entry = {
            "timestamp": datetime.now().isoformat(),
            "tool": tool,
            "command": cmd,
            "exit_code": exit_code,
            "duration_s": round(duration, 2),
            "output_snippet": output_snippet[:500],
        }
        self.commands.append(entry)
        self._save()

    def _save(self):
        data = {
            "session_id": self.id,
            "started": self.started,
            "commands": self.commands,
        }
        self.file.write_text(json.dumps(data, indent=2))

    @staticmethod
    def list_sessions():
        files = sorted(SESSIONS_DIR.glob("session_*.json"), reverse=True)
        sessions = []
        for f in files[:50]:
            try:
                d = json.loads(f.read_text())
                sessions.append(d)
            except Exception:
                pass
        return sessions


class ProcessRunner:
    """Runs commands as subprocesses with real-time output streaming."""

    def __init__(self):
        self.active_processes = {}  # pid -> Popen
        self.lock = threading.Lock()
        self._sudo_password = None

    def set_sudo_password(self, password):
        self._sudo_password = password

    def needs_external_terminal(self, cmd):
        """Check if command needs a real terminal (interactive/TUI tools)."""
        first_word = cmd.strip().split()[0].split("/")[-1]
        # Strip sudo prefix
        words = cmd.strip().split()
        tool = words[0]
        if tool == "sudo" and len(words) > 1:
            tool = words[1]
            if tool == "-S" and len(words) > 2:
                tool = words[2]
        return tool in TERMINAL_TOOLS

    def run_in_terminal(self, cmd):
        """Launch command in an external terminal window."""
        term = _find_terminal()
        sudo_pw = self._sudo_password

        # Wrap command: pipe sudo password if needed
        if sudo_pw and "sudo " in cmd:
            # Use echo to pipe password, then keep terminal open
            wrapped = f"echo '{sudo_pw}' | sudo -S {cmd.replace('sudo ', '', 1)}; echo; echo '[Done] Press Enter to close'; read"
        else:
            wrapped = f"{cmd}; echo; echo '[Done] Press Enter to close'; read"

        if term == "gnome-terminal":
            launch = f'{term} -- bash -c "{wrapped}"'
        elif term in ("qterminal", "xfce4-terminal", "konsole"):
            launch = f'{term} -e bash -c "{wrapped}"'
        else:
            launch = f'xterm -e bash -c "{wrapped}"'

        subprocess.Popen(launch, shell=True, preexec_fn=os.setsid)

    def run(self, cmd: str, as_root: bool = False, callback=None, env=None):
        """
        Run a command. Returns (exit_code, output, duration).
        callback(line) is called for each output line in real time.
        """
        if as_root and os.geteuid() != 0:
            cmd = f"sudo {cmd}"

        # Check if this needs an external terminal
        if self.needs_external_terminal(cmd):
            self.run_in_terminal(cmd)
            if callback:
                callback(f"[Opened in external terminal]\n")
            return 0, "[Opened in external terminal]\n", 0.0

        # Auto-supply sudo password via -S if cmd uses sudo
        sudo_password = self._sudo_password
        needs_sudo_pipe = "sudo " in cmd and sudo_password

        if needs_sudo_pipe:
            # Pipe password via echo instead of replacing sudo
            cmd = f"echo '{sudo_password}' | sudo -S {cmd.replace('sudo ', '', 1)}"

        merged_env = os.environ.copy()
        if env:
            merged_env.update(env)

        start = time.time()
        output_lines = []

        try:
            proc = subprocess.Popen(
                cmd, shell=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                env=merged_env,
                preexec_fn=os.setsid,
                bufsize=1,
                universal_newlines=True,
            )
            with self.lock:
                self.active_processes[proc.pid] = proc

            for line in iter(proc.stdout.readline, ""):
                clean = strip_ansi(line)
                output_lines.append(clean)
                if callback:
                    callback(clean)

            proc.wait()
            exit_code = proc.returncode
        except Exception as e:
            output_lines.append(f"[ERROR] {e}\n")
            exit_code = -1
        finally:
            with self.lock:
                self.active_processes.pop(proc.pid, None)

        duration = time.time() - start
        output = "".join(output_lines)
        return exit_code, output, duration

    def kill(self, pid: int):
        with self.lock:
            proc = self.active_processes.get(pid)
            if proc:
                try:
                    os.killpg(os.getpgid(proc.pid), signal.SIGTERM)
                except Exception:
                    proc.kill()

    def kill_all(self):
        with self.lock:
            for pid, proc in list(self.active_processes.items()):
                try:
                    os.killpg(os.getpgid(proc.pid), signal.SIGTERM)
                except Exception:
                    try:
                        proc.kill()
                    except Exception:
                        pass
            self.active_processes.clear()


class ToolInstaller:
    """Checks and installs Kali tool packages."""

    @staticmethod
    def is_installed(tool_name: str) -> bool:
        result = subprocess.run(
            f"which {tool_name}", shell=True,
            capture_output=True, text=True
        )
        return result.returncode == 0

    @staticmethod
    def install_package(package: str, callback=None) -> tuple:
        cmd = f"sudo apt-get install -y {package}"
        proc = subprocess.Popen(
            cmd, shell=True,
            stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
            universal_newlines=True
        )
        output = []
        for line in iter(proc.stdout.readline, ""):
            output.append(line)
            if callback:
                callback(line)
        proc.wait()
        return proc.returncode, "".join(output)

    @staticmethod
    def bulk_install(packages: list, callback=None) -> tuple:
        pkg_str = " ".join(packages)
        cmd = f"sudo apt-get install -y {pkg_str}"
        proc = subprocess.Popen(
            cmd, shell=True,
            stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
            universal_newlines=True
        )
        output = []
        for line in iter(proc.stdout.readline, ""):
            output.append(line)
            if callback:
                callback(line)
        proc.wait()
        return proc.returncode, "".join(output)

    @staticmethod
    def update_repos(callback=None) -> tuple:
        cmd = "sudo apt-get update"
        proc = subprocess.Popen(
            cmd, shell=True,
            stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
            universal_newlines=True
        )
        output = []
        for line in iter(proc.stdout.readline, ""):
            output.append(line)
            if callback:
                callback(line)
        proc.wait()
        return proc.returncode, "".join(output)
