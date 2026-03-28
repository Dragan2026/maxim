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

ANSI_RE = re.compile(r'\x1b\[[0-9;]*[a-zA-Z]|\x1b\[\?[0-9;]*[a-zA-Z]|\x1b\(B')

# Tools that MUST run in a real terminal (interactive/TUI tools)
TERMINAL_TOOLS = {
    "wifite", "msfconsole", "bettercap", "ettercap", "wireshark",
    "burpsuite", "zenmap", "maltego", "armitage",
    "airodump-ng", "aireplay-ng", "wash", "reaver",
}


def strip_ansi(text):
    return ANSI_RE.sub('', text)


def ensure_dirs():
    DATA_DIR.mkdir(exist_ok=True)
    LOG_DIR.mkdir(exist_ok=True)
    SESSIONS_DIR.mkdir(exist_ok=True)


ensure_dirs()


def _find_terminal():
    for term in ["qterminal", "xfce4-terminal", "gnome-terminal", "konsole", "xterm"]:
        if shutil.which(term):
            return term
    return "xterm"


class Session:
    def __init__(self):
        self.id = datetime.now().strftime("%Y%m%d_%H%M%S")
        self.started = datetime.now().isoformat()
        self.commands = []
        self.file = SESSIONS_DIR / f"session_{self.id}.json"

    def log_command(self, cmd, tool, exit_code, duration, output_snippet=""):
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
                sessions.append(json.loads(f.read_text()))
            except Exception:
                pass
        return sessions


class ProcessRunner:
    def __init__(self):
        self.active_processes = {}
        self.lock = threading.Lock()
        self._sudo_password = None
        self._sudo_cached = False

    def set_sudo_password(self, password):
        self._sudo_password = password
        self._cache_sudo()

    def _escape_pw(self):
        """Escape password for safe use in shell single quotes."""
        return self._sudo_password.replace("'", "'\\''") if self._sudo_password else ""

    def _refresh_sudo(self):
        """Refresh sudo cache before opening external terminal."""
        self._cache_sudo()

    def _cache_sudo(self):
        """Cache sudo credentials so all future sudo commands work without stdin pipe."""
        if not self._sudo_password:
            return False
        try:
            pw = self._escape_pw()
            result = subprocess.run(
                f"echo '{pw}' | sudo -S -v",
                shell=True, capture_output=True, text=True, timeout=5
            )
            self._sudo_cached = (result.returncode == 0)
            return self._sudo_cached
        except Exception:
            return False

    def needs_external_terminal(self, cmd):
        """Check if ANY tool in the command (including chained ones) needs a terminal."""
        # Split by && and ; to check all commands in chain
        parts = re.split(r'&&|;', cmd)
        for part in parts:
            words = part.strip().split()
            if not words:
                continue
            tool = words[0]
            if tool == "sudo" and len(words) > 1:
                tool = words[1]
            if tool in TERMINAL_TOOLS:
                return True
        return False

    def run_in_terminal(self, cmd):
        try:
            term = _find_terminal()
            self._refresh_sudo()

            # Inject sudo password if needed
            if "sudo " in cmd and self._sudo_password:
                pw = self._escape_pw()
                cmd = f"echo '{pw}' | sudo -S -v 2>/dev/null; {cmd}"

            # Write command to temp script to avoid escaping issues
            import tempfile
            script = tempfile.NamedTemporaryFile(mode='w', suffix='.sh', delete=False, prefix='maxim_')
            script.write("#!/bin/bash\n")
            script.write(cmd + "\n")
            script.write('echo\necho "[Done] Press Enter to close"\nread\n')
            script.close()
            os.chmod(script.name, 0o755)

            if term == "gnome-terminal":
                launch = f'{term} -- bash {script.name}'
            elif term in ("qterminal", "xfce4-terminal", "konsole"):
                launch = f'{term} -e bash {script.name}'
            else:
                launch = f'xterm -e bash {script.name}'

            subprocess.Popen(launch, shell=True, preexec_fn=os.setsid)
        except Exception as e:
            print(f"[Error opening terminal] {e}")

    def run(self, cmd, as_root=False, callback=None, env=None):
        if as_root and os.geteuid() != 0:
            cmd = f"sudo {cmd}"

        # If interactive tool, open in real terminal
        if self.needs_external_terminal(cmd):
            self.run_in_terminal(cmd)
            if callback:
                callback("[Opened in external terminal]\n")
            return 0, "[Opened in external terminal]\n", 0.0

        # Inline sudo password into the shell command (replace ALL sudo occurrences)
        if "sudo " in cmd and self._sudo_password:
            pw = self._escape_pw()
            cmd = cmd.replace("sudo ", f"echo '{pw}' | sudo -S ")

        merged_env = os.environ.copy()
        if env:
            merged_env.update(env)

        start = time.time()
        output_lines = []
        proc = None

        try:
            popen_kwargs = dict(
                shell=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                env=merged_env,
                bufsize=1,
                universal_newlines=True,
            )
            if hasattr(os, 'setsid'):
                popen_kwargs['preexec_fn'] = os.setsid

            proc = subprocess.Popen(cmd, **popen_kwargs)
            with self.lock:
                self.active_processes[proc.pid] = proc

            for line in iter(proc.stdout.readline, ""):
                clean = strip_ansi(line)
                # Filter out sudo password prompt
                if clean.strip().startswith("[sudo] password for"):
                    continue
                # Handle \r carriage returns (hashcat/john progress lines)
                # Split on \r and only keep the last segment (the overwritten line)
                if '\r' in clean:
                    parts = clean.split('\r')
                    # Last non-empty part is what would be visible on a real terminal
                    for part in parts:
                        part = part.strip()
                        if part:
                            output_lines.append(part + "\n")
                            if callback:
                                callback(part + "\n")
                    continue
                output_lines.append(clean)
                if callback:
                    callback(clean)

            proc.wait()
            exit_code = proc.returncode
        except Exception as e:
            output_lines.append(f"[ERROR] {e}\n")
            exit_code = -1
        finally:
            if proc is not None:
                with self.lock:
                    self.active_processes.pop(proc.pid, None)

        duration = time.time() - start
        output = "".join(output_lines)
        return exit_code, output, duration

    def _kill_proc(self, proc):
        try:
            if hasattr(os, 'killpg') and hasattr(os, 'getpgid'):
                os.killpg(os.getpgid(proc.pid), signal.SIGTERM)
            else:
                proc.terminate()
        except Exception:
            try:
                proc.kill()
            except Exception:
                pass

    def kill(self, pid):
        with self.lock:
            proc = self.active_processes.get(pid)
            if proc:
                self._kill_proc(proc)

    def kill_all(self):
        with self.lock:
            for pid, proc in list(self.active_processes.items()):
                self._kill_proc(proc)
            self.active_processes.clear()


class ToolInstaller:
    @staticmethod
    def is_installed(tool_name):
        result = subprocess.run(
            f"which {tool_name}", shell=True,
            capture_output=True, text=True
        )
        return result.returncode == 0

    @staticmethod
    def install_package(package, callback=None):
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
    def bulk_install(packages, callback=None):
        cmd = f"sudo apt-get install -y {' '.join(packages)}"
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
