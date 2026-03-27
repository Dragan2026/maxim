"""
Maxim Online Knowledge Base — fetches exact commands from online sources.
Sources:
  - cheat.sh — command cheat sheets + natural language search
  - TLDR pages — concise command examples
  - GTFOBins — privilege escalation techniques
"""

import urllib.request
import urllib.error
import urllib.parse
import re


def query_cheatsh(query: str, timeout: int = 5) -> str:
    """Query cheat.sh for command help. Returns plain text."""
    try:
        # Clean query for URL
        q = urllib.parse.quote(query.strip())
        url = f"https://cheat.sh/{q}?T"
        req = urllib.request.Request(url, headers={
            "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36",
            "Accept": "text/plain",
        })
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            text = resp.read().decode("utf-8", errors="replace")
            # Remove ANSI codes if any leaked through
            text = re.sub(r'\x1b\[[0-9;]*[a-zA-Z]', '', text)
            return text.strip()
    except Exception:
        return ""


def search_cheatsh(query: str, timeout: int = 5) -> str:
    """Search cheat.sh with natural language query."""
    try:
        words = query.strip().replace(" ", "+")
        url = f"https://cheat.sh/~{words}?T"
        req = urllib.request.Request(url, headers={
            "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36",
            "Accept": "text/plain",
        })
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            text = resp.read().decode("utf-8", errors="replace")
            text = re.sub(r'\x1b\[[0-9;]*[a-zA-Z]', '', text)
            return text.strip()[:2000]  # Limit size
    except Exception:
        return ""


def query_tldr(tool: str, timeout: int = 5) -> str:
    """Fetch TLDR page for a tool from GitHub."""
    tool = tool.strip().lower()
    # Try common/ first, then linux/
    for section in ["common", "linux"]:
        try:
            url = f"https://raw.githubusercontent.com/tldr-pages/tldr/main/pages/{section}/{tool}.md"
            req = urllib.request.Request(url, headers={
                "User-Agent": "Mozilla/5.0",
            })
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                text = resp.read().decode("utf-8", errors="replace")
                # Extract command examples from markdown
                commands = []
                for line in text.split("\n"):
                    line = line.strip()
                    if line.startswith("`") and line.endswith("`"):
                        commands.append(line.strip("`"))
                    elif line.startswith("- ") or line.startswith("> "):
                        commands.append(line)
                return "\n".join(commands) if commands else text[:1500]
        except Exception:
            continue
    return ""


def query_gtfobins(binary: str, timeout: int = 5) -> str:
    """Fetch GTFOBins entry for privilege escalation."""
    try:
        binary = binary.strip().lower()
        url = f"https://raw.githubusercontent.com/GTFOBins/GTFOBins.github.io/master/_gtfobins/{binary}.md"
        req = urllib.request.Request(url, headers={
            "User-Agent": "Mozilla/5.0",
        })
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            text = resp.read().decode("utf-8", errors="replace")
            return text[:2000]
    except Exception:
        return ""


def lookup_command(query: str) -> str:
    """
    Smart lookup — tries multiple sources to find the right command.
    Returns helpful text or empty string.
    """
    q = query.lower().strip()

    # If it's a single tool name, get its cheat sheet
    words = q.split()
    if len(words) == 1:
        result = query_cheatsh(words[0])
        if result:
            return result
        result = query_tldr(words[0])
        if result:
            return result
        return ""

    # If asking about a specific tool + task
    known_tools = [
        "nmap", "sqlmap", "hydra", "nikto", "gobuster", "dirb", "ffuf",
        "aircrack-ng", "airodump-ng", "aireplay-ng", "airmon-ng", "wifite",
        "john", "hashcat", "metasploit", "msfvenom", "msfconsole",
        "burpsuite", "wireshark", "tcpdump", "ettercap", "bettercap",
        "crackmapexec", "enum4linux", "smbclient", "netdiscover",
        "responder", "macchanger", "reaver", "whatweb", "wpscan",
    ]
    for tool in known_tools:
        if tool in q:
            result = query_cheatsh(tool)
            if result:
                return result
            break

    # Natural language search
    result = search_cheatsh(query)
    if result:
        return result

    return ""
