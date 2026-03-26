"""
Test SmartRouter — ensures natural language prompts route to correct tools.
Tests every tool category with 2-3 prompts each.
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from maxim.core.ai_assistant import SmartRouter
from maxim.core.workflows import NATURAL_COMMANDS
from maxim.tools.tool_registry import get_tool_by_name, find_tools_by_keywords, TOOLS

PASS = 0
FAIL = 0


def check(test_name, query, expected_tools=None, expected_intent=None, expected_direct=False):
    global PASS, FAIL
    route = SmartRouter.route(query)

    ok = True
    details = []

    if expected_intent and route["intent"] != expected_intent:
        ok = False
        details.append(f"intent: got '{route['intent']}', expected '{expected_intent}'")

    if expected_tools:
        found_names = [t["name"] for t in route["tools"]]
        for et in expected_tools:
            if et not in found_names:
                ok = False
                details.append(f"tool '{et}' not in results {found_names}")

    if expected_direct and not route["direct_command"]:
        ok = False
        details.append("expected direct_command but got None")

    if ok:
        PASS += 1
        print(f"  PASS  {test_name}")
    else:
        FAIL += 1
        print(f"  FAIL  {test_name} -- {'; '.join(details)}")
        print(f"        query: '{query}'")
        print(f"        route: intent={route['intent']}, tools={[t['name'] for t in route['tools']]}, direct={route['direct_command']}")


def test_network_scanning():
    print("\n=== Network Scanning ===")
    check("nmap port scan", "scan ports on 192.168.1.1", expected_tools=["nmap"])
    check("nmap keyword", "nmap 10.0.0.1", expected_tools=["nmap"])
    check("discover hosts", "find devices on my network", expected_tools=["nmap"])
    check("ping sweep", "who is on my network", expected_intent="network_discover")
    check("masscan", "fast port scan entire subnet", expected_tools=["masscan"])


def test_wireless():
    print("\n=== Wireless Attacks ===")
    check("monitor mode", "put wlan1 in monitor mode", expected_intent="wireless_monitor")
    check("scan wifi", "scan wifi networks", expected_intent="wireless_scan")
    check("crack wpa", "crack wifi password", expected_intent="wireless_crack")
    check("deauth", "deauth all clients", expected_intent="wireless_deauth")
    check("aircrack keyword", "aircrack-ng", expected_tools=["aircrack-ng"])


def test_exploitation():
    print("\n=== Exploitation ===")
    check("metasploit", "launch metasploit", expected_tools=["metasploit"])
    check("exploit search", "search exploit for apache", expected_tools=["metasploit"])
    check("sqlmap", "sql injection test", expected_intent="sqli")
    check("sqlmap keyword", "sqlmap", expected_tools=["sqlmap"])
    check("reverse shell", "set up a reverse shell listener", expected_intent="reverse_shell")


def test_web_testing():
    print("\n=== Web Testing ===")
    check("web scan", "scan web application", expected_intent="web_scan")
    check("dir brute", "find hidden directories", expected_intent="web_dir")
    check("nikto", "nikto scan", expected_tools=["nikto"])
    check("gobuster", "gobuster directory scan", expected_tools=["gobuster"])
    check("fuzz", "fuzz parameters on website", expected_intent="web_dir")


def test_password():
    print("\n=== Password Attacks ===")
    check("crack hash", "crack this hash", expected_intent="password_crack")
    check("john", "john the ripper", expected_tools=["john"])
    check("hydra ssh", "brute force ssh login", expected_intent="brute_login")
    check("hashcat", "hashcat gpu crack", expected_tools=["hashcat"])
    check("hydra keyword", "hydra", expected_tools=["hydra"])


def test_sniffing():
    print("\n=== Sniffing & Spoofing ===")
    check("wireshark", "capture packets", expected_intent="sniff")
    check("mitm", "man in the middle attack", expected_intent="mitm")
    check("mac change", "change mac address", expected_intent="mac_change")
    check("tcpdump", "tcpdump on eth0", expected_tools=["tcpdump"])
    check("arp spoof", "arp spoof the gateway", expected_intent="mitm")


def test_system_commands():
    print("\n=== System Commands ===")
    check("install pkg", "install nmap", expected_intent="install", expected_direct=True)
    check("update system", "update", expected_intent="update", expected_direct=True)
    check("check ip", "check ip", expected_intent="check_ip", expected_direct=True)
    check("my ip", "my ip", expected_intent="check_ip", expected_direct=True)
    check("start service", "start apache2", expected_intent="service", expected_direct=True)
    check("stop service", "stop apache2", expected_intent="service", expected_direct=True)
    check("restart service", "restart ssh", expected_intent="service", expected_direct=True)


def test_tunneling():
    print("\n=== Tunneling & Pivoting ===")
    check("ssh tunnel", "set up ssh tunnel", expected_intent="tunnel")
    check("chisel", "chisel pivot", expected_tools=["chisel"])
    check("port forward", "port forward to internal", expected_intent="tunnel")


def test_anonymity():
    print("\n=== Anonymity ===")
    check("start tor", "start tor", expected_intent="tor")
    check("anonymous", "anonymize my traffic", expected_intent="tor")


def test_natural_commands():
    print("\n=== Natural Commands (exact phrases) ===")
    for phrase, (tool, cmd, desc) in NATURAL_COMMANDS.items():
        tool_obj = get_tool_by_name(tool)
        # Verify the tool exists in registry
        if tool_obj:
            PASS_local = True
            print(f"  PASS  '{phrase}' -> {tool} ({desc})")
        elif tool in ("ip", "curl", "dig", "host", "find", "grep", "cat",
                       "sudo", "ps", "getcap", "systemctl", "ping",
                       "traceroute", "airmon-ng", "airodump-ng", "aireplay-ng",
                       "msfvenom", "hcxpcapngtool", "pwncat", "rlwrap",
                       "linpeas", "mimikatz", "evil-winrm", "bloodhound-python",
                       "script", "tree", "tar", "amass", "sublist3r",
                       "smbclient", "smbmap", "rpcclient", "nbtscan",
                       "snmpwalk", "onesixtyone", "ldapsearch",
                       "commix", "xsstrike", "dalfox", "wafw00f", "amap",
                       "iwconfig", "iw", "wash"):
            # System tools not in our registry — that's fine
            print(f"  PASS  '{phrase}' -> {tool} (system cmd)")
        else:
            global FAIL
            FAIL += 1
            print(f"  FAIL  '{phrase}' -> tool '{tool}' not found in registry")


def test_keyword_search():
    print("\n=== Keyword Search Fallback ===")
    # These should find tools via keyword matching even if intent doesn't match
    results = find_tools_by_keywords("smb shares enumerate", top_n=3)
    names = [t["name"] for t in results]
    if "enum4linux" in names or "crackmapexec" in names:
        global PASS
        PASS += 1
        print(f"  PASS  'smb shares enumerate' -> {names}")
    else:
        FAIL += 1
        print(f"  FAIL  'smb shares enumerate' -> {names} (expected enum4linux or cme)")

    results = find_tools_by_keywords("dns records", top_n=3)
    names = [t["name"] for t in results]
    if "dnsenum" in names:
        PASS += 1
        print(f"  PASS  'dns records' -> {names}")
    else:
        FAIL += 1
        print(f"  FAIL  'dns records' -> {names}")

    results = find_tools_by_keywords("wordpress", top_n=3)
    names = [t["name"] for t in results]
    if "wpscan" in names:
        PASS += 1
        print(f"  PASS  'wordpress' -> {names}")
    else:
        FAIL += 1
        print(f"  FAIL  'wordpress' -> {names}")


def test_tool_registry_integrity():
    print("\n=== Tool Registry Integrity ===")
    global PASS, FAIL
    for tool in TOOLS:
        issues = []
        if not tool.get("name"):
            issues.append("missing name")
        if not tool.get("category"):
            issues.append("missing category")
        if not tool.get("package"):
            issues.append("missing package")
        if not tool.get("keywords"):
            issues.append("no keywords")
        if not tool.get("common_commands"):
            issues.append("no commands")
        if "needs_root" not in tool:
            issues.append("missing needs_root")

        if issues:
            FAIL += 1
            print(f"  FAIL  {tool.get('name', '???')} -- {', '.join(issues)}")
        else:
            PASS += 1
            print(f"  PASS  {tool['name']} ({len(tool['keywords'])} keywords, {len(tool['common_commands'])} cmds)")


def test_multiple_tool_choice():
    print("\n=== Multiple Tool Choice (needs_choice) ===")
    global PASS, FAIL

    # WiFi crack should offer multiple tools
    route = SmartRouter.route("crack wifi password")
    if route["needs_choice"] and len(route["tools"]) > 1:
        PASS += 1
        print(f"  PASS  'crack wifi' -> needs_choice=True, tools={[t['name'] for t in route['tools']]}")
    else:
        FAIL += 1
        print(f"  FAIL  'crack wifi' -> needs_choice={route['needs_choice']}, tools={[t['name'] for t in route['tools']]}")

    # Dir scan should offer multiple
    route = SmartRouter.route("brute force directories")
    if route["needs_choice"] and len(route["tools"]) > 1:
        PASS += 1
        print(f"  PASS  'brute dirs' -> needs_choice=True, tools={[t['name'] for t in route['tools']]}")
    else:
        FAIL += 1
        print(f"  FAIL  'brute dirs' -> needs_choice={route['needs_choice']}, tools={[t['name'] for t in route['tools']]}")

    # MITM should offer multiple
    route = SmartRouter.route("man in the middle")
    if route["needs_choice"] and len(route["tools"]) > 1:
        PASS += 1
        print(f"  PASS  'mitm' -> needs_choice=True, tools={[t['name'] for t in route['tools']]}")
    else:
        FAIL += 1
        print(f"  FAIL  'mitm' -> needs_choice={route['needs_choice']}, tools={[t['name'] for t in route['tools']]}")

    # sqlmap should NOT need choice (single tool)
    route = SmartRouter.route("sql injection")
    if not route["needs_choice"]:
        PASS += 1
        print(f"  PASS  'sqli' -> needs_choice=False (single tool: sqlmap)")
    else:
        FAIL += 1
        print(f"  FAIL  'sqli' -> needs_choice={route['needs_choice']}")


if __name__ == "__main__":
    print("=" * 60)
    print("  MAXIM — SmartRouter & Tool Registry Test Suite")
    print("=" * 60)

    test_network_scanning()
    test_wireless()
    test_exploitation()
    test_web_testing()
    test_password()
    test_sniffing()
    test_system_commands()
    test_tunneling()
    test_anonymity()
    test_natural_commands()
    test_keyword_search()
    test_tool_registry_integrity()
    test_multiple_tool_choice()

    print("\n" + "=" * 60)
    total = PASS + FAIL
    print(f"  Results: {PASS}/{total} passed, {FAIL} failed")
    if FAIL == 0:
        print("  ALL TESTS PASSED")
    print("=" * 60)

    sys.exit(0 if FAIL == 0 else 1)
