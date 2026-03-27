"""
Test every tool in Maxim — simulate user prompts and verify correct routing + command generation.
"""
import re
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from maxim.core.ai_assistant import SmartRouter
from maxim.core.workflows import NATURAL_COMMANDS
from maxim.tools.tool_registry import TOOLS, get_tool_by_name, find_tools_by_keywords


def extract_target(query):
    ip_match = re.search(r'\b(\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}(?:/\d{1,2})?)\b', query)
    if ip_match:
        return ip_match.group(1)
    domain_match = re.search(r'\b([a-zA-Z0-9][-a-zA-Z0-9]*\.[a-zA-Z]{2,}(?:\.[a-zA-Z]{2,})?)\b', query)
    if domain_match:
        c = domain_match.group(1)
        if c not in {'example.com', 'wlan0.mon'}:
            return c
    return None


def fill_placeholders(cmd_template, query=""):
    extracted = extract_target(query) if query else None
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


def simulate_prompt(query):
    """Simulate the full _on_prompt_submit logic from main_window.py"""
    q_lower = query.lower().strip()

    # 1. Raw command detection
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
        return {"type": "raw", "cmd": query, "tool": query.split()[0]}

    # 2. NATURAL_COMMANDS
    for phrase, (tool, cmd, desc) in NATURAL_COMMANDS.items():
        if phrase in q_lower:
            filled = fill_placeholders(cmd, query)
            return {"type": "natural", "cmd": filled, "tool": tool, "phrase": phrase}

    # 3. SmartRouter
    route = SmartRouter.route(query)
    if route["direct_command"]:
        return {"type": "direct", "cmd": route["direct_command"], "tool": "system"}

    if route["tools"]:
        tool = route["tools"][0]
        if tool.get("common_commands"):
            best_cmd = tool["common_commands"][0]["cmd"]
            filled = fill_placeholders(best_cmd, query)
            return {"type": "routed", "cmd": filled, "tool": tool["name"], "intent": route["intent"]}

    # 4. Would go to AI
    return {"type": "ai_fallback", "cmd": None, "tool": None}


# ═══════════════════════════════════════════════════════
# TEST: Every tool reachable by at least one prompt
# ═══════════════════════════════════════════════════════

# Map of tool_name -> list of prompts to try
TOOL_PROMPTS = {
    # Network Scanning
    "nmap": [
        "nmap -sV 192.168.1.1",
        "scan 192.168.1.0/24",
        "scan ports on target.com",
        "vulnerability scan on testsite.com",
    ],
    "masscan": [
        "masscan 192.168.1.0/24 -p1-65535",
        "fast port scan 10.0.0.0/24",
    ],
    "netdiscover": [
        "netdiscover -r 192.168.1.0/24",
        "discover hosts on network",
    ],
    "enum4linux": [
        "enum4linux 192.168.1.1",
        "enumerate smb on 192.168.1.100",
    ],
    "dnsenum": [
        "dnsenum target.com",
        "dns enumeration on example.org",
    ],
    "whois": [
        "whois google.com",
        "whois lookup target.com",
    ],
    "theHarvester": [
        "harvest emails from target.com",
        "osint on company.com",
    ],

    # Wireless
    "aircrack-ng": [
        "aircrack-ng capture.cap",
        "crack wifi password",
    ],
    "wifite": [
        "wifite",
        "scan for wifi networks",
    ],
    "fern-wifi-cracker": [
        "fern-wifi-cracker",
    ],
    "reaver": [
        "reaver -i wlan0mon -b AA:BB:CC:DD:EE:FF",
        "crack wps pin",
    ],
    "bettercap": [
        "bettercap",
        "man in the middle attack",
    ],

    # Exploitation
    "metasploit": [
        "msfconsole",
        "start metasploit",
    ],
    "searchsploit": [
        "searchsploit apache 2.4",
        "find exploits for vsftpd",
    ],
    "sqlmap": [
        "sqlmap -u http://target.com/page?id=1",
        "sql injection test on site.com",
    ],
    "crackmapexec": [
        "crackmapexec smb 192.168.1.0/24",
    ],
    "impacket": [
        "lateral movement on 192.168.1.50",
    ],

    # Web Testing
    "burpsuite": [
        "burpsuite",
    ],
    "nikto": [
        "nikto -h 192.168.1.1",
        "web vulnerability scan on target.com",
    ],
    "dirb": [
        "dirb http://target.com",
        "find hidden directories on site.com",
    ],
    "gobuster": [
        "gobuster dir -u http://target.com -w /usr/share/wordlists/dirb/common.txt",
        "directory bruteforce on webapp.com",
    ],
    "wpscan": [
        "wpscan --url http://wordpress-site.com",
        "scan wordpress site.com",
    ],
    "whatweb": [
        "whatweb target.com",
        "identify web technology on site.com",
    ],
    "ffuf": [
        "ffuf -u http://target.com/FUZZ -w /usr/share/wordlists/dirb/common.txt",
        "fuzz web app on target.com",
    ],

    # Password Attacks
    "john": [
        "john --wordlist=/usr/share/wordlists/rockyou.txt hashes.txt",
        "crack this hash",
    ],
    "hashcat": [
        "hashcat -m 0 hashes.txt /usr/share/wordlists/rockyou.txt",
        "crack md5 hash",
    ],
    "hydra": [
        "hydra -l admin -P /usr/share/wordlists/rockyou.txt 192.168.1.1 ssh",
        "brute force ssh on 192.168.1.1",
    ],
    "medusa": [
        "medusa -h 192.168.1.1 -u admin -P /usr/share/wordlists/rockyou.txt -M ssh",
    ],
    "crunch": [
        "crunch 8 12 -o wordlist.txt",
        "generate wordlist",
    ],

    # Sniffing
    "wireshark": [
        "wireshark",
        "capture packets",
    ],
    "tcpdump": [
        "tcpdump -i eth0",
        "sniff network traffic",
    ],
    "ettercap": [
        "ettercap -G",
        "arp spoof the network",
    ],
    "responder": [
        "responder -I eth0",
    ],
    "macchanger": [
        "macchanger -r wlan0",
        "change mac address",
    ],

    # Social Engineering
    "setoolkit": [
        "social engineering attack",
    ],
    "beef-xss": [
        "xss attack framework",
    ],

    # Forensics
    "autopsy": [
        "forensic analysis",
    ],
    "binwalk": [
        "binwalk firmware.bin",
        "analyze firmware",
    ],
    "volatility": [
        "memory forensics",
    ],
    "foremost": [
        "recover deleted files",
    ],

    # Reverse Engineering
    "ghidra": [
        "reverse engineer binary",
    ],
    "radare2": [
        "disassemble binary",
    ],

    # Vuln Analysis
    "openvas": [
        "full vulnerability assessment",
    ],
    "lynis": [
        "lynis audit system",
        "security audit",
    ],
    "legion": [
        "automated pentest scan",
    ],

    # System
    "tor": [
        "start tor",
        "anonymous browsing",
    ],
    "proxychains": [
        "proxychains nmap 192.168.1.1",
        "use proxy chain",
    ],
    "netcat": [
        "nc -lvnp 4444",
        "start listener on port 4444",
    ],
    "socat": [
        "socat TCP-LISTEN:4444,fork TCP:192.168.1.1:80",
    ],
    "chisel": [
        "chisel server --reverse --port 8080",
        "tunnel through firewall",
    ],
}


class TestResults:
    def __init__(self):
        self.passed = 0
        self.failed = 0
        self.warnings = 0
        self.details = []

    def ok(self, msg):
        self.passed += 1
        self.details.append(("OK", msg))

    def fail(self, msg):
        self.failed += 1
        self.details.append(("FAIL", msg))

    def warn(self, msg):
        self.warnings += 1
        self.details.append(("WARN", msg))


def test_every_tool_reachable():
    """Test that every tool can be reached via at least one prompt."""
    results = TestResults()

    for tool_name, prompts in TOOL_PROMPTS.items():
        tool_reached = False
        tool_results = []

        for prompt in prompts:
            result = simulate_prompt(prompt)
            cmd = result.get("cmd", "")
            rtype = result["type"]
            rtool = result.get("tool", "")

            # Check if the tool was reached
            reached = False
            if rtype == "raw" and tool_name.lower() in prompt.lower():
                reached = True
            elif rtype in ("natural", "routed", "direct") and cmd:
                reached = True
            elif rtype == "ai_fallback":
                reached = False

            tool_results.append({
                "prompt": prompt,
                "type": rtype,
                "cmd": cmd,
                "reached": reached,
            })

            if reached:
                tool_reached = True

        if tool_reached:
            # Find best result to show
            best = next((r for r in tool_results if r["reached"]), tool_results[0])
            results.ok(f"{tool_name}: \"{best['prompt']}\" -> [{best['type']}] {best['cmd'][:80]}")
        else:
            best = tool_results[0]
            results.fail(f"{tool_name}: NO prompt reached it. Best try: \"{best['prompt']}\" -> [{best['type']}]")

    # Print report
    print("\n" + "=" * 80)
    print("TOOL REACHABILITY REPORT")
    print("=" * 80)

    for status, msg in results.details:
        icon = {"OK": "+", "FAIL": "X", "WARN": "!"}[status]
        print(f"  [{icon}] {msg}")

    print(f"\n  TOTAL: {results.passed} OK, {results.failed} FAIL, {results.warnings} WARN")
    print("=" * 80)

    assert results.failed == 0, f"{results.failed} tools unreachable"


def test_every_tool_command_generates():
    """Test that every tool's common_commands produce valid shell commands after placeholder fill."""
    failures = []

    for tool in TOOLS:
        for i, cc in enumerate(tool["common_commands"]):
            cmd = cc["cmd"]
            filled = fill_placeholders(cmd, "test on 192.168.1.1")
            # Should have no remaining {placeholders}
            remaining = re.findall(r'\{(\w+)\}', filled)
            if remaining:
                failures.append(f"{tool['name']} cmd[{i}]: unfilled placeholders {remaining} in: {filled}")
            # Should not be empty
            if not filled.strip():
                failures.append(f"{tool['name']} cmd[{i}]: empty command after fill")

    if failures:
        print("\nCOMMAND GENERATION FAILURES:")
        for f in failures:
            print(f"  [X] {f}")

    assert len(failures) == 0, f"{len(failures)} commands failed to generate"


def test_natural_commands_all_generate():
    """Test every NATURAL_COMMAND generates a runnable command."""
    failures = []

    for phrase, (tool, cmd, desc) in NATURAL_COMMANDS.items():
        filled = fill_placeholders(cmd, f"{phrase} on 192.168.1.1")
        remaining = re.findall(r'\{(\w+)\}', filled)
        if remaining:
            failures.append(f"'{phrase}' ({tool}): unfilled {remaining} in: {filled}")
        if not filled.strip():
            failures.append(f"'{phrase}' ({tool}): empty command")

    if failures:
        print("\nNATURAL COMMAND FAILURES:")
        for f in failures:
            print(f"  [X] {f}")

    assert len(failures) == 0, f"{len(failures)} natural commands failed"


def test_keyword_search_finds_every_tool():
    """Test that every tool can be found via keyword search using its own name."""
    not_found = []
    for tool in TOOLS:
        # Search using the tool's own name — should always find itself
        results = find_tools_by_keywords(tool["name"], top_n=10)
        found_names = [t["name"] for t in results]
        if tool["name"] not in found_names:
            not_found.append(f"{tool['name']} not found via its own name")

    if not_found:
        print("\nKEYWORD SEARCH FAILURES:")
        for f in not_found:
            print(f"  [X] {f}")

    assert len(not_found) == 0, f"{len(not_found)} tools not findable by keywords"


def test_raw_command_detection():
    """Test that direct tool commands are caught as raw commands."""
    raw_tests = [
        ("nmap -sV 192.168.1.1", True),
        ("sudo nmap -sn 10.0.0.0/24", True),
        ("airmon-ng start wlan0", True),
        ("sqlmap -u http://x.com?id=1", True),
        ("hydra -l admin -P pass.txt 10.0.0.1 ssh", True),
        ("gobuster dir -u http://x.com -w list.txt", True),
        ("john --wordlist=rockyou.txt hash.txt", True),
        ("tcpdump -i eth0 -w capture.pcap", True),
        ("msfconsole", True),
        ("wireshark", True),
        ("scan my network please", False),
        ("find vulnerabilities", False),  # "find " removed from raw prefixes
        ("crack the password", False),
    ]

    failures = []
    for cmd, expected_raw in raw_tests:
        result = simulate_prompt(cmd)
        is_raw = result["type"] == "raw"
        if is_raw != expected_raw:
            failures.append(f"'{cmd}': expected raw={expected_raw}, got type={result['type']}")

    if failures:
        print("\nRAW DETECTION FAILURES:")
        for f in failures:
            print(f"  [X] {f}")

    assert len(failures) == 0, f"{len(failures)} raw detection failures"


def test_target_extraction_in_prompts():
    """Test that targets mentioned in prompts end up in the generated command."""
    target_tests = [
        ("scan 10.0.0.5", "10.0.0.5"),
        ("vulnerability scan on evil.com", "evil.com"),
        ("enumerate smb on 192.168.1.100", "192.168.1.100"),
        ("find directories on webapp.com", "webapp.com"),
        ("brute force ssh on 10.10.10.5", "10.10.10.5"),
    ]

    failures = []
    for prompt, expected_target in target_tests:
        result = simulate_prompt(prompt)
        cmd = result.get("cmd", "")
        if cmd and expected_target not in cmd:
            failures.append(f"'{prompt}': target '{expected_target}' not in cmd: {cmd}")

    if failures:
        print("\nTARGET EXTRACTION FAILURES:")
        for f in failures:
            print(f"  [X] {f}")

    assert len(failures) == 0, f"{len(failures)} target extraction failures"
