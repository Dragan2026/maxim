"""
Maxim Core Engine — handles subprocess execution, logging, session management.
"""

import subprocess
import os
import json
import time
import signal
import threading
from datetime import datetime
from pathlib import Path

DATA_DIR = Path.home() / ".maxim"
LOG_DIR = DATA_DIR / "logs"
SESSIONS_DIR = DATA_DIR / "sessions"


def ensure_dirs():
    DATA_DIR.mkdir(exist_ok=True)
    LOG_DIR.mkdir(exist_ok=True)
    SESSIONS_DIR.mkdir(exist_ok=True)


ensure_dirs()


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

    def run(self, cmd: str, as_root: bool = False, callback=None, env=None):
        """
        Run a command. Returns (exit_code, output).
        callback(line) is called for each output line in real time.
        """
        if as_root and os.geteuid() != 0:
            cmd = f"sudo {cmd}"

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
                output_lines.append(line)
                if callback:
                    callback(line)

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
