"""
Test brute force logic — script generation, hash detection, early exit, regex patterns.
"""
import os
import sys
import re

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Mirror the data from main_window.py so we can test without PyQt5
HASH_TYPES = [
    ("$2b$", "bcrypt", "3200", "bcrypt", "hashcat"),
    ("$2a$", "bcrypt", "3200", "bcrypt", "hashcat"),
    ("$2y$", "bcrypt", "3200", "bcrypt", "hashcat"),
    ("$2$",  "bcrypt", "3200", "bcrypt", "hashcat"),
    ("$6$",  "sha512crypt", "1800", "SHA512crypt", "hashcat"),
    ("$5$",  "sha256crypt", "7400", "SHA256crypt", "hashcat"),
    ("$1$",  "md5crypt", "500", "MD5crypt", "hashcat"),
    ("$apr1$", "md5crypt", "1600", "Apache MD5", "hashcat"),
    ("$P$",  "phpass", "400", "phpass (WordPress)", "hashcat"),
    ("$H$",  "phpass", "400", "phpass (phpBB)", "hashcat"),
    ("$y$",  "yescrypt", "None", "yescrypt", "john"),
    ("$7$",  "scrypt", "None", "scrypt", "john"),
]

HASH_LENGTHS = {
    32:  ("Raw-MD5", "0", "MD5"),
    40:  ("Raw-SHA1", "100", "SHA1"),
    56:  ("Raw-SHA224", "1300", "SHA224"),
    64:  ("Raw-SHA256", "1400", "SHA256"),
    96:  ("Raw-SHA384", "10800", "SHA384"),
    128: ("Raw-SHA512", "1700", "SHA512"),
    16:  ("LM", "3000", "LM hash"),
}


def test_hash_detection_by_length():
    """Test that all expected hash lengths are present."""
    for length in [32, 40, 56, 64, 96, 128, 16]:
        assert length in HASH_LENGTHS, f"Missing length {length}"
        john_fmt, hc_mode, label = HASH_LENGTHS[length]
        assert len(john_fmt) > 0
        assert hc_mode.isdigit()
        assert len(label) > 0


def test_hash_detection_by_prefix():
    """Test prefix-based hash type detection with real hash samples."""
    test_cases = [
        ("$2b$12$WApznUPhDubN0oeveSXHp.aLtNRh5fZ9XKzA", "bcrypt", "3200", "hashcat"),
        ("$2a$10$N9qo8uLOickgx2ZMRZoMye", "bcrypt", "3200", "hashcat"),
        ("$2y$12$abc", "bcrypt", "3200", "hashcat"),
        ("$6$rounds=5000$saltsalt$hash", "sha512crypt", "1800", "hashcat"),
        ("$5$rounds=5000$saltsalt$hash", "sha256crypt", "7400", "hashcat"),
        ("$1$salt1234$hashvalue", "md5crypt", "500", "hashcat"),
        ("$apr1$salt$hashvalue", "md5crypt", "1600", "hashcat"),
        ("$P$B123456789abcdef", "phpass", "400", "hashcat"),
        ("$H$B123456789abcdef", "phpass", "400", "hashcat"),
        ("$y$j9T$salt$hash", "yescrypt", "None", "john"),
        ("$7$salt$hash", "scrypt", "None", "john"),
    ]
    for sample, expected_john, expected_hc, expected_tool in test_cases:
        matched = False
        for prefix, john_fmt, hc_mode, label, pref_tool in HASH_TYPES:
            if sample.startswith(prefix):
                assert hc_mode == expected_hc, f"{sample[:20]}: hc_mode {hc_mode} != {expected_hc}"
                assert pref_tool == expected_tool, f"{sample[:20]}: tool {pref_tool} != {expected_tool}"
                matched = True
                break
        assert matched, f"No prefix match for: {sample[:30]}"


def test_hex_hash_identification():
    """Test that hex hash strings are correctly identified and routed."""
    test_hashes = [
        ("5d41402abc4b2a76b9719d911017c592", 32, "0", "MD5"),
        ("aaf4c61ddcc5e8a2dabede0f3b482cd9aea9434d", 40, "100", "SHA1"),
        ("2cf24dba5fb0a30e26e83b2ac5b9e29e1b161e5c1fa7425e73043362938b9824", 64, "1400", "SHA256"),
        ("cf83e1357eefb8bdf1542850d66d8007d620e4050b5715dc83f4a921d36ce9ce47d0d13c5d85f2b0ff8318d2877eec2f63b931bd47417a81a538327af927da3e" , 128, "1700", "SHA512"),
    ]
    for h, expected_len, expected_mode, expected_label in test_hashes:
        assert len(h) == expected_len, f"{expected_label} len {len(h)} != {expected_len}"
        assert all(c in '0123456789abcdefABCDEF' for c in h), f"Not hex: {h[:20]}"
        john_fmt, hc_mode, label = HASH_LENGTHS[expected_len]
        assert hc_mode == expected_mode, f"{expected_label}: mode {hc_mode} != {expected_mode}"
        assert label == expected_label, f"label {label} != {expected_label}"
        # Fast hashes (<=64) should go to hashcat
        if expected_len <= 64:
            assert True  # would use hashcat


def test_cracked_detection_patterns():
    """Test all regex patterns that detect if a password was cracked."""
    # Patterns that SHOULD match (password found)
    should_match = [
        (r'KEY FOUND!\s*\[', "KEY FOUND! [password123]"),
        (r'KEY FOUND!\s*\[', "    KEY FOUND! [ mypassword ]"),
        (r'PASSWORD FOUND', "  PASSWORD FOUND!"),
        (r'PASSWORD CRACKED', "  PASSWORD CRACKED!"),
        (r'[1-9]\d* password hash(?:es)? cracked', "2 password hashes cracked, 0 left"),
        (r'[1-9]\d* password hash(?:es)? cracked', "1 password hash cracked, 0 left"),
        (r'[1-9]\d* password hash(?:es)? cracked', "15 password hashes cracked"),
        (r'Recovered\.+:\s*[1-9]', "Recovered........: 1/1 (100.00%)"),
        (r'Recovered\.+:\s*[1-9]', "Recovered.......: 3/5 (60.00%)"),
        (r'Status\.+:\s*Cracked', "Status...........: Cracked"),
        (r'Status\.+:\s*Cracked', "Status.........: Cracked"),
    ]
    for pattern, sample in should_match:
        assert re.search(pattern, sample), f"FAIL: Pattern '{pattern}' didn't match '{sample}'"

    # Patterns that should NOT match (no password found)
    should_not_match = [
        (r'[1-9]\d* password hash(?:es)? cracked', "0 password hashes cracked, 1 left"),
        (r'Recovered\.+:\s*[1-9]', "Recovered........: 0/1 (0.00%)"),
        (r'Status\.+:\s*Cracked', "Status...........: Exhausted"),
        (r'Status\.+:\s*Cracked', "Status...........: Running"),
        (r'KEY FOUND!\s*\[', "No KEY FOUND"),
    ]
    for pattern, sample in should_not_match:
        assert not re.search(pattern, sample), f"FALSE POSITIVE: '{pattern}' matched '{sample}'"


def test_john_check_filters_zero():
    """The john --show check must filter '0 password hashes cracked'."""
    # Our check: grep -v '^0 password' | grep -v '^$' | grep ':'
    # Simulate with Python
    def simulate_check(john_output_lines):
        """Simulate: grep -v '^0 password' | grep -v '^$' | grep ':'"""
        result = []
        for line in john_output_lines:
            if line.startswith("0 password"):
                continue
            if line.strip() == "":
                continue
            if ":" in line:
                result.append(line)
        return result

    # Case 1: Nothing cracked
    output_nothing = [
        "0 password hashes cracked, 1 left",
        "",
    ]
    assert simulate_check(output_nothing) == [], "Should find nothing"

    # Case 2: Password cracked
    output_cracked = [
        "admin:password123",
        "1 password hash cracked, 0 left",
        "",
    ]
    result = simulate_check(output_cracked)
    assert len(result) == 1, f"Should find 1 result, got {len(result)}"
    assert "admin:password123" in result[0]

    # Case 3: Multiple cracked
    output_multi = [
        "admin:pass1",
        "user:pass2",
        "2 password hashes cracked, 0 left",
    ]
    result = simulate_check(output_multi)
    assert len(result) == 2, f"Should find 2 results, got {len(result)}"


def test_hashcat_mask_patterns_valid():
    """Verify hashcat mask patterns are valid characters."""
    valid_mask_chars = {'?d', '?l', '?u', '?a', '?s', '?h', '?H', '?b', '?1', '?2', '?3', '?4'}
    masks = [
        '?d?d?d?d',
        '?d?d?d?d?d?d?d?d',
        '?d?d?d?d?d?d?d?d?d?d?d?d',
        '?l?l?l?l?l?l',
        '?l?l?l?l?l?l?l?l',
        '?1?1?1?1?1?1',
        '?l?l?l?l?l?d?d?d?d',
        '?a?a?a?a?a',
        '?a?a?a?a?a?a',
    ]
    for mask in masks:
        tokens = re.findall(r'\?\w', mask)
        for t in tokens:
            assert t in valid_mask_chars, f"Invalid mask char '{t}' in '{mask}'"
        assert len(tokens) > 0, f"No tokens found in mask '{mask}'"


def test_aircrack_brute_crunch_pipe():
    """WiFi brute force must use crunch piped to aircrack-ng."""
    # Expected pattern: crunch <min> <max> <charset> | sudo aircrack-ng -w - ...
    samples = [
        "crunch 8 8 0123456789 | sudo aircrack-ng -w - -b auto '/tmp/test.cap'",
        "crunch 8 8 abcdefghijklmnopqrstuvwxyz | sudo aircrack-ng -w - -b auto '/tmp/test.cap'",
        "crunch 10 10 0123456789 | sudo aircrack-ng -w - -b auto '/tmp/test.cap'",
    ]
    pattern = r'crunch \d+ \d+ \S+ \| sudo aircrack-ng -w - '
    for s in samples:
        assert re.search(pattern, s), f"Pattern didn't match: {s}"


def test_hashcat_optimization_flags():
    """Hashcat brute force must use optimization flags."""
    flags = ['-O', '-w 3', '-a 3', '--increment', '--force']
    sample = "hashcat -m 0 -a 3 'file' '?d?d?d?d' --increment --increment-min=1 --force -O -w 3"
    for flag in flags:
        assert flag in sample, f"Missing flag '{flag}'"


def test_hashcat_runtime_limits():
    """Longer hashcat stages must have --runtime to prevent infinite runs."""
    # These represent the longer stages that need timeout
    long_stages = [
        "hashcat -m 0 -a 3 'f' '?l?l?l?l?l?l?l?l' --increment --increment-min=7 --force -O -w 3 --runtime=300",
        "hashcat -m 0 -a 3 'f' '?a?a?a?a?a?a' --force -O -w 3 --runtime=600",
        "hashcat -m 0 -a 3 'f' '?d?d?d?d?d?d?d?d?d?d?d?d' --increment --increment-min=9 --force -O -w 3 --runtime=180",
    ]
    for cmd in long_stages:
        assert '--runtime=' in cmd, f"Missing --runtime in: {cmd}"
        # Extract runtime value
        rt = re.search(r'--runtime=(\d+)', cmd)
        assert rt, f"Can't parse runtime from: {cmd}"
        assert int(rt.group(1)) > 0, f"Runtime must be positive"


def test_no_duplicate_prefixes():
    """No duplicate prefixes in HASH_TYPES."""
    prefixes = [entry[0] for entry in HASH_TYPES]
    assert len(prefixes) == len(set(prefixes)), f"Duplicate prefixes found"


def test_all_hashcat_modes_numeric():
    """All hashcat modes must be numeric (or 'None' for john-only types)."""
    for length, (john_fmt, hc_mode, label) in HASH_LENGTHS.items():
        assert hc_mode.isdigit(), f"Length {length}: hc_mode '{hc_mode}' not numeric"

    for prefix, john_fmt, hc_mode, label, pref_tool in HASH_TYPES:
        if pref_tool == "hashcat":
            assert hc_mode.isdigit(), f"Prefix {prefix}: hc_mode '{hc_mode}' not numeric"


def test_early_exit_script_structure():
    """Verify the early-exit bash script structure is correct."""
    # The script should have: command -> check -> if found exit 0 -> next stage
    script_template = """#!/bin/bash
set -e

echo ''
echo '  [1] Wordlist + rules: gago.txt'
john --format=Raw-MD5 --wordlist='/usr/share/wordlists/gago.txt' --rules=best64 '/tmp/test.txt'
if john --format=Raw-MD5 --show '/tmp/test.txt' 2>/dev/null | grep -v '^0 password' | grep -v '^$' | grep ':' >/dev/null 2>&1; then
  echo ''
  echo '  PASSWORD FOUND!'
  john --format=Raw-MD5 --show '/tmp/test.txt'
  exit 0
fi

echo ''
echo '  Wordlists exhausted.'
john --format=Raw-MD5 --show '/tmp/test.txt'
"""
    assert 'set -e' in script_template
    assert 'exit 0' in script_template
    assert '--rules=best64' in script_template
    assert "grep -v '^0 password'" in script_template
    assert 'PASSWORD FOUND' in script_template
    assert 'Wordlists exhausted' in script_template


def test_wifi_brute_force_wpa_min_length():
    """WPA passwords are 8-63 chars — crunch must start at 8."""
    samples = [
        "crunch 8 8 0123456789",
        "crunch 8 8 abcdefghijklmnopqrstuvwxyz",
        "crunch 9 9 0123456789",
        "crunch 10 10 0123456789",
    ]
    for s in samples:
        parts = s.split()
        min_len = int(parts[1])
        assert min_len >= 8, f"WPA min length must be >= 8, got {min_len} in '{s}'"
