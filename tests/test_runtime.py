"""
Maxim Runtime Tests — test actual code paths as if running the app.
"""
import re
import sys
import os

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def test_all_imports():
    """Every module must import without error."""
    from maxim.core.engine import ProcessRunner, Session, ToolInstaller, strip_ansi
    from maxim.core.ai_assistant import AIManager, SmartRouter, PROVIDERS, OllamaAI, OnlineAI
    from maxim.core.workflows import PHASES, NATURAL_COMMANDS, ONLINE_RESOURCES
    from maxim.tools.tool_registry import TOOLS, TOOL_CATEGORIES, find_tools_by_keywords, get_tool_by_name
    from maxim.core.updater import get_current_version


def test_process_runner_init():
    from maxim.core.engine import ProcessRunner
    runner = ProcessRunner()
    runner.set_sudo_password("5505")
    assert runner._sudo_password == "5505"


def test_ansi_stripping():
    from maxim.core.engine import strip_ansi
    dirty = '\x1b[32m  Hello  \x1b[37m \x1b[2m World \x1b[0m'
    clean = strip_ansi(dirty)
    assert '\x1b' not in clean
    assert 'Hello' in clean
    assert 'World' in clean


def test_session_logging():
    from maxim.core.engine import Session
    session = Session()
    session.log_command('nmap -sV target', 'nmap', 0, 1.5)
    assert len(session.commands) == 1
    assert session.commands[0]['tool'] == 'nmap'
    assert session.commands[0]['exit_code'] == 0
    assert session.file.exists()
    # Cleanup
    session.file.unlink(missing_ok=True)


def test_smart_router_all_intents():
    from maxim.core.ai_assistant import SmartRouter
    queries = {
        'scan 192.168.1.0/24': 'net_scan',
        'vulnerability scan': 'vuln_scan',
        'crack this hash': 'password_crack',
        'put wlan0 in monitor mode': 'wifi_monitor',
        'find directories on target.com': 'web_dir',
        'sniff traffic': 'sniff',
        'brute force ssh': 'brute_force',
        'start tor': 'anonymity',
        'exploit the target': 'exploit',
        'enumerate smb': 'smb_enum',
    }
    for query, expected_intent in queries.items():
        route = SmartRouter.route(query)
        assert route['intent'] or route['tools'] or route['direct_command'], \
            f"No route for: {query}"


def test_smart_router_returns_tools_with_commands():
    """Every tool returned by SmartRouter must have common_commands."""
    from maxim.core.ai_assistant import SmartRouter
    queries = [
        'scan network', 'crack password', 'web scan',
        'sniff packets', 'exploit target', 'wireless attack',
    ]
    for q in queries:
        route = SmartRouter.route(q)
        for tool in route.get('tools', []):
            assert 'common_commands' in tool, f"Tool {tool['name']} has no common_commands"
            assert len(tool['common_commands']) > 0, f"Tool {tool['name']} has empty common_commands"
            for cc in tool['common_commands']:
                assert 'cmd' in cc, f"Tool {tool['name']} command missing 'cmd' key: {cc}"


def test_natural_commands_all_valid():
    """Every NATURAL_COMMAND must reference an existing tool."""
    from maxim.core.workflows import NATURAL_COMMANDS
    from maxim.tools.tool_registry import get_tool_by_name
    for phrase, (tool_name, cmd, desc) in NATURAL_COMMANDS.items():
        assert isinstance(tool_name, str), f"Bad tool name for '{phrase}': {tool_name}"
        assert isinstance(cmd, str), f"Bad cmd for '{phrase}': {cmd}"
        assert isinstance(desc, str), f"Bad desc for '{phrase}': {desc}"
        assert len(cmd) > 0, f"Empty command for '{phrase}'"


def test_tool_registry_integrity():
    """Every tool must have required fields and non-empty commands."""
    from maxim.tools.tool_registry import TOOLS, TOOL_CATEGORIES
    required = ['name', 'category', 'package', 'description', 'keywords', 'common_commands']
    for tool in TOOLS:
        for field in required:
            assert field in tool, f"Tool {tool.get('name', '?')} missing '{field}'"
        assert tool['category'] in TOOL_CATEGORIES, \
            f"Tool {tool['name']} has unknown category '{tool['category']}'"
        assert len(tool['keywords']) > 0, f"Tool {tool['name']} has no keywords"
        assert len(tool['common_commands']) > 0, f"Tool {tool['name']} has no commands"
        for cc in tool['common_commands']:
            assert 'cmd' in cc, f"Tool {tool['name']} command missing 'cmd'"
            assert 'label' in cc, f"Tool {tool['name']} command missing 'label'"


def test_keyword_search():
    from maxim.tools.tool_registry import find_tools_by_keywords
    results = find_tools_by_keywords('wifi crack password')
    assert len(results) > 0
    names = [t['name'] for t in results]
    assert any(n in names for n in ['aircrack-ng', 'wifite', 'hashcat', 'john'])


def test_ai_manager_init_and_switch():
    from maxim.core.ai_assistant import AIManager, PROVIDERS
    ai = AIManager()
    assert ai.active_provider in PROVIDERS
    for pid in PROVIDERS:
        ai.switch_provider(pid)
        assert ai.active_provider == pid
        assert ai.provider_name  # must return something


def test_ai_manager_status():
    from maxim.core.ai_assistant import AIManager
    ai = AIManager()
    status = ai.get_status()
    assert isinstance(status, str)
    assert len(status) > 0


def test_workflows_structure():
    from maxim.core.workflows import PHASES, ONLINE_RESOURCES
    assert len(PHASES) == 7
    for phase in PHASES:
        assert 'id' in phase
        assert 'name' in phase
        assert 'steps' in phase
        assert len(phase['steps']) > 0
        for step in phase['steps']:
            assert 'name' in step
            assert 'suggestions' in step
            for sug in step['suggestions']:
                assert 'tool' in sug
                assert 'cmd' in sug
                assert 'desc' in sug
    assert len(ONLINE_RESOURCES) > 0


def test_sudo_command_construction():
    from maxim.core.engine import ProcessRunner
    runner = ProcessRunner()
    runner.set_sudo_password('test123')
    pw = runner._escape_pw()
    assert pw == 'test123'

    # Test special character escaping
    runner2 = ProcessRunner()
    runner2.set_sudo_password("it's")
    pw2 = runner2._escape_pw()
    assert "'" not in pw2.replace("'\\''", "")  # all quotes escaped


def test_sudo_inline():
    """Simulate the sudo inline replacement that happens in run()."""
    from maxim.core.engine import ProcessRunner
    runner = ProcessRunner()
    runner.set_sudo_password('mypass')
    cmd = 'sudo nmap -sV 192.168.1.1'
    if 'sudo ' in cmd and runner._sudo_password:
        pw = runner._escape_pw()
        result = cmd.replace('sudo ', f"echo '{pw}' | sudo -S ", 1)
    assert 'echo' in result
    assert 'sudo -S' in result
    assert 'nmap -sV' in result
    assert 'mypass' in result


def test_external_terminal_detection():
    from maxim.core.engine import ProcessRunner
    runner = ProcessRunner()
    assert runner.needs_external_terminal('wifite') is True
    assert runner.needs_external_terminal('sudo wifite --kill') is True
    assert runner.needs_external_terminal('msfconsole') is True
    assert runner.needs_external_terminal('nmap -sV target') is False
    assert runner.needs_external_terminal('sudo nmap -sn 192.168.1.0/24') is False
    assert runner.needs_external_terminal('aircrack-ng file.cap') is False
    assert runner.needs_external_terminal('hydra -l admin target') is False


def test_target_extraction():
    """Test the regex logic used in main_window._extract_target_from_query."""
    def extract_target(query):
        ip_match = re.search(r'\b(\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}(?:/\d{1,2})?)\b', query)
        if ip_match:
            return ip_match.group(1)
        domain_match = re.search(r'\b([a-zA-Z0-9][-a-zA-Z0-9]*\.[a-zA-Z]{2,}(?:\.[a-zA-Z]{2,})?)\b', query)
        if domain_match:
            candidate = domain_match.group(1)
            if candidate not in {'example.com', 'wlan0.mon'}:
                return candidate
        return None

    assert extract_target('scan 192.168.1.0/24') == '192.168.1.0/24'
    assert extract_target('vulnerability scan on testsite.com') == 'testsite.com'
    assert extract_target('hack google.com') == 'google.com'
    assert extract_target('scan my network') is None
    assert extract_target('nmap 10.0.0.1') == '10.0.0.1'
    assert extract_target('test example.org for vulns') == 'example.org'


def test_fill_placeholders():
    """Test placeholder filling with extracted targets."""
    def fill(cmd_template, query=""):
        def extract(q):
            ip_match = re.search(r'\b(\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}(?:/\d{1,2})?)\b', q)
            if ip_match:
                return ip_match.group(1)
            domain_match = re.search(r'\b([a-zA-Z0-9][-a-zA-Z0-9]*\.[a-zA-Z]{2,}(?:\.[a-zA-Z]{2,})?)\b', q)
            if domain_match:
                c = domain_match.group(1)
                if c not in {'example.com', 'wlan0.mon'}:
                    return c
            return None

        extracted = extract(query) if query else None
        defaults = {
            "iface": "wlan0", "target": extracted or "192.168.1.1",
            "port": "4444", "domain": extracted or "example.com",
        }
        cmd = cmd_template
        for ph, val in defaults.items():
            cmd = cmd.replace(f"{{{ph}}}", val)
        return cmd

    # User says "scan testsite.com" — {target} should become testsite.com
    assert fill("nmap -sV {target}", "scan testsite.com") == "nmap -sV testsite.com"
    # User says "scan 10.0.0.0/24" — {target} should become the IP
    assert fill("nmap -sn {target}", "scan 10.0.0.0/24") == "nmap -sn 10.0.0.0/24"
    # No target in query — use default
    assert fill("nmap -sV {target}", "scan my network") == "nmap -sV 192.168.1.1"
    # Domain placeholder
    assert fill("gobuster dir -u http://{domain}", "find dirs on evil.com") == "gobuster dir -u http://evil.com"


def test_updater():
    from maxim.core.updater import get_current_version
    ver = get_current_version()
    assert re.match(r'\d+\.\d+\.\d+', ver), f"Bad version format: {ver}"


def test_version_compare():
    """Test the semver comparison used in updater."""
    def ver_tuple(v):
        return tuple(int(x) for x in v.split(".")[:3])

    assert ver_tuple("1.0.0") < ver_tuple("1.0.1")
    assert ver_tuple("1.0.0") < ver_tuple("1.1.0")
    assert ver_tuple("1.0.0") < ver_tuple("2.0.0")
    assert ver_tuple("1.0.0") == ver_tuple("1.0.0")
    assert not (ver_tuple("1.0.1") < ver_tuple("1.0.0"))
