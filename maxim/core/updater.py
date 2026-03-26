"""
Maxim Auto-Updater — checks GitHub for new releases and updates in-place.
"""

import json
import os
import subprocess
import urllib.request
import urllib.error
from pathlib import Path

GITHUB_REPO = "stoev/maxim"
GITHUB_API = f"https://api.github.com/repos/{GITHUB_REPO}/releases/latest"
VERSION_FILE = Path(__file__).parent.parent / "VERSION"
INSTALL_DIR = Path(__file__).parent.parent.parent  # maxim/ root


def get_current_version() -> str:
    try:
        if VERSION_FILE.exists():
            return VERSION_FILE.read_text().strip()
    except Exception:
        pass
    return "1.0.0"


def set_version(version: str):
    VERSION_FILE.write_text(version)


def check_for_update() -> dict:
    """
    Check GitHub for latest release.
    Returns: {"available": bool, "current": str, "latest": str, "url": str, "notes": str}
    """
    current = get_current_version()
    try:
        req = urllib.request.Request(
            GITHUB_API,
            headers={"Accept": "application/vnd.github.v3+json", "User-Agent": "Maxim-Updater"}
        )
        with urllib.request.urlopen(req, timeout=10) as resp:
            data = json.loads(resp.read())
            latest = data.get("tag_name", "v0.0.0").lstrip("v")
            notes = data.get("body", "")
            tarball = data.get("tarball_url", "")

            # Simple semver compare
            def ver_tuple(v):
                return tuple(int(x) for x in v.split(".")[:3])

            available = ver_tuple(latest) > ver_tuple(current)
            return {
                "available": available,
                "current": current,
                "latest": latest,
                "url": tarball,
                "notes": notes,
            }
    except Exception as e:
        return {
            "available": False,
            "current": current,
            "latest": current,
            "url": "",
            "notes": f"Update check failed: {e}",
        }


def perform_update(callback=None) -> tuple:
    """
    Update Maxim from GitHub.
    Returns (success: bool, message: str)
    """
    info = check_for_update()
    if not info["available"]:
        return False, "Already up to date"

    try:
        if callback:
            callback(f"Downloading Maxim v{info['latest']}...")

        # Use git pull if it's a git repo, otherwise download tarball
        if (INSTALL_DIR / ".git").exists():
            proc = subprocess.run(
                "git pull origin main",
                shell=True, cwd=str(INSTALL_DIR),
                capture_output=True, text=True
            )
            if proc.returncode != 0:
                return False, f"Git pull failed: {proc.stderr}"
        else:
            # Download and extract
            import tempfile
            import tarfile
            import shutil

            tmp = tempfile.mktemp(suffix=".tar.gz")
            urllib.request.urlretrieve(info["url"], tmp)

            if callback:
                callback("Extracting...")

            with tarfile.open(tmp, "r:gz") as tar:
                # Get the top-level directory name
                top_dir = tar.getnames()[0].split("/")[0]
                tar.extractall(path=tempfile.gettempdir())

            extracted = Path(tempfile.gettempdir()) / top_dir

            # Copy new files over
            for item in extracted.rglob("*"):
                if item.is_file():
                    rel = item.relative_to(extracted)
                    dest = INSTALL_DIR / rel
                    dest.parent.mkdir(parents=True, exist_ok=True)
                    shutil.copy2(str(item), str(dest))

            # Cleanup
            os.unlink(tmp)
            shutil.rmtree(str(extracted), ignore_errors=True)

        set_version(info["latest"])

        if callback:
            callback(f"Updated to v{info['latest']}! Restart Maxim to apply.")

        return True, f"Updated to v{info['latest']}"

    except Exception as e:
        return False, f"Update failed: {e}"
