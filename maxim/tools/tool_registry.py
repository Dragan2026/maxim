"""
Maxim Tool Registry — defines all known Kali tools, their categories,
install commands, and natural-language keyword mappings.
"""

TOOL_CATEGORIES = {
    "network_scanning": {
        "name": "Network Scanning & Recon",
        "icon": "network-wired",
        "color": "#3498db"
    },
    "wireless": {
        "name": "Wireless Attacks",
        "icon": "wifi",
        "color": "#e74c3c"
    },
    "exploitation": {
        "name": "Exploitation",
        "icon": "crosshairs",
        "color": "#e67e22"
    },
    "web_testing": {
        "name": "Web Application Testing",
        "icon": "globe",
        "color": "#2ecc71"
    },
    "password": {
        "name": "Password Attacks",
        "icon": "key",
        "color": "#9b59b6"
    },
    "forensics": {
        "name": "Forensics & Recovery",
        "icon": "search",
        "color": "#1abc9c"
    },
    "sniffing": {
        "name": "Sniffing & Spoofing",
        "icon": "eye",
        "color": "#f39c12"
    },
    "social_engineering": {
        "name": "Social Engineering",
        "icon": "users",
        "color": "#e74c3c"
    },
    "reverse_engineering": {
        "name": "Reverse Engineering",
        "icon": "microchip",
        "color": "#8e44ad"
    },
    "vuln_analysis": {
        "name": "Vulnerability Analysis",
        "icon": "bug",
        "color": "#d35400"
    },
    "stress_testing": {
        "name": "Stress Testing & DoS",
        "icon": "bolt",
        "color": "#ff4757"
    },
    "system": {
        "name": "System & Utilities",
        "icon": "terminal",
        "color": "#7f8c8d"
    },
}

# Each tool: name, category, package, keywords (for NLP matching),
# common_commands (templates), needs_root, description
TOOLS = [
    # ── Network Scanning ──
    {
        "name": "nmap",
        "category": "network_scanning",
        "package": "nmap",
        "description": "Network exploration and security auditing",
        "needs_root": True,
        "keywords": ["scan", "port", "network", "host", "discover", "ping", "service", "version", "os detection", "traceroute", "subnet", "ip range"],
        "common_commands": [
            {"label": "Quick scan", "cmd": "nmap -sV {target}"},
            {"label": "Full port scan", "cmd": "nmap -p- -sV -sC {target}"},
            {"label": "Ping sweep", "cmd": "nmap -sn {target}/24"},
            {"label": "OS detection", "cmd": "nmap -O -sV {target}"},
            {"label": "Aggressive scan", "cmd": "nmap -A -T4 {target}"},
            {"label": "UDP scan", "cmd": "nmap -sU --top-ports 100 {target}"},
            {"label": "Stealth SYN scan", "cmd": "nmap -sS -T2 {target}"},
            {"label": "Vuln scan", "cmd": "nmap --script vuln {target}"},
            {"label": "Subnet discovery", "cmd": "nmap -sn 192.168.1.0/24"},
        ]
    },
    {
        "name": "masscan",
        "category": "network_scanning",
        "package": "masscan",
        "description": "Fast TCP port scanner (async)",
        "needs_root": True,
        "keywords": ["scan", "port", "fast", "mass", "tcp", "internet scale"],
        "common_commands": [
            {"label": "Top ports scan", "cmd": "masscan {target}/24 --top-ports 100 --rate 1000"},
            {"label": "Full range", "cmd": "masscan {target}/24 -p0-65535 --rate 10000"},
        ]
    },
    {
        "name": "netdiscover",
        "category": "network_scanning",
        "package": "netdiscover",
        "description": "Active/passive ARP reconnaissance",
        "needs_root": True,
        "keywords": ["discover", "arp", "network", "hosts", "local", "lan"],
        "common_commands": [
            {"label": "Auto scan", "cmd": "netdiscover -r 192.168.1.0/24"},
            {"label": "Passive mode", "cmd": "netdiscover -p"},
        ]
    },
    {
        "name": "enum4linux",
        "category": "network_scanning",
        "package": "enum4linux",
        "description": "SMB/Samba enumeration",
        "needs_root": False,
        "keywords": ["smb", "samba", "windows", "shares", "enum", "enumerate", "netbios"],
        "common_commands": [
            {"label": "Full enum", "cmd": "enum4linux -a {target}"},
        ]
    },
    {
        "name": "dnsenum",
        "category": "network_scanning",
        "package": "dnsenum",
        "description": "DNS enumeration",
        "needs_root": False,
        "keywords": ["dns", "domain", "subdomain", "zone transfer", "nameserver"],
        "common_commands": [
            {"label": "DNS enum", "cmd": "dnsenum {domain}"},
        ]
    },
    {
        "name": "whois",
        "category": "network_scanning",
        "package": "whois",
        "description": "Domain/IP WHOIS lookup",
        "needs_root": False,
        "keywords": ["whois", "domain", "registrar", "owner", "lookup"],
        "common_commands": [
            {"label": "WHOIS lookup", "cmd": "whois {domain}"},
        ]
    },
    {
        "name": "theHarvester",
        "category": "network_scanning",
        "package": "theharvester",
        "description": "Email, subdomain, and name harvester",
        "needs_root": False,
        "keywords": ["email", "harvest", "osint", "subdomain", "recon", "gather"],
        "common_commands": [
            {"label": "Harvest emails", "cmd": "theHarvester -d {domain} -b all -l 200"},
        ]
    },

    # ── Wireless ──
    {
        "name": "aircrack-ng",
        "category": "wireless",
        "package": "aircrack-ng",
        "description": "WiFi security auditing suite",
        "needs_root": True,
        "keywords": ["wifi", "wireless", "crack", "wpa", "wep", "handshake", "capture", "aircrack", "deauth", "monitor mode", "wlan", "packet"],
        "common_commands": [
            {"label": "Start monitor mode", "cmd": "airmon-ng start {iface}"},
            {"label": "Stop monitor mode", "cmd": "airmon-ng stop {iface}mon"},
            {"label": "Scan networks", "cmd": "airodump-ng {iface}mon"},
            {"label": "Capture handshake", "cmd": "airodump-ng -c {channel} --bssid {bssid} -w capture {iface}mon"},
            {"label": "Deauth attack", "cmd": "aireplay-ng -0 10 -a {bssid} {iface}mon"},
            {"label": "Crack WPA", "cmd": "aircrack-ng -w {wordlist} capture-01.cap"},
            {"label": "Check interfaces", "cmd": "airmon-ng"},
        ]
    },
    {
        "name": "wifite",
        "category": "wireless",
        "package": "wifite",
        "description": "Automated wireless auditing tool",
        "needs_root": True,
        "keywords": ["wifi", "wireless", "auto", "crack", "wpa", "wps", "wifite", "automated"],
        "common_commands": [
            {"label": "Auto attack", "cmd": "wifite"},
            {"label": "WPA only", "cmd": "wifite --wpa"},
            {"label": "Target BSSID", "cmd": "wifite -b {bssid}"},
        ]
    },
    {
        "name": "fern-wifi-cracker",
        "category": "wireless",
        "package": "fern-wifi-cracker",
        "description": "GUI WiFi security auditing tool",
        "needs_root": True,
        "keywords": ["wifi", "wireless", "fern", "gui", "crack"],
        "common_commands": [
            {"label": "Launch GUI", "cmd": "fern-wifi-cracker"},
        ]
    },
    {
        "name": "reaver",
        "category": "wireless",
        "package": "reaver",
        "description": "WPS brute force attack tool",
        "needs_root": True,
        "keywords": ["wps", "pin", "brute", "reaver", "wifi", "wireless"],
        "common_commands": [
            {"label": "WPS attack", "cmd": "reaver -i {iface}mon -b {bssid} -vv"},
        ]
    },
    {
        "name": "bettercap",
        "category": "wireless",
        "package": "bettercap",
        "description": "Network attack and monitoring framework",
        "needs_root": True,
        "keywords": ["mitm", "arp", "spoof", "sniff", "wifi", "bluetooth", "ble", "bettercap", "caplet"],
        "common_commands": [
            {"label": "Interactive", "cmd": "bettercap"},
            {"label": "WiFi recon", "cmd": "bettercap -iface {iface}mon -caplet wifi-recon"},
            {"label": "ARP spoof", "cmd": "bettercap -iface {iface} -caplet arp.spoof"},
        ]
    },

    # ── Exploitation ──
    {
        "name": "metasploit",
        "category": "exploitation",
        "package": "metasploit-framework",
        "description": "Penetration testing framework",
        "needs_root": True,
        "keywords": ["exploit", "metasploit", "msfconsole", "payload", "reverse shell", "meterpreter", "msf", "vulnerability", "attack", "shell"],
        "common_commands": [
            {"label": "Start console", "cmd": "msfconsole"},
            {"label": "DB init", "cmd": "msfdb init && msfconsole"},
            {"label": "Quick exploit", "cmd": "msfconsole -x 'use {module}; set RHOSTS {target}; run'"},
            {"label": "Generate payload", "cmd": "msfvenom -p {payload} LHOST={lhost} LPORT={lport} -f {format} -o output"},
        ]
    },
    {
        "name": "searchsploit",
        "category": "exploitation",
        "package": "exploitdb",
        "description": "Exploit-DB offline search",
        "needs_root": False,
        "keywords": ["exploit", "search", "vulnerability", "cve", "exploitdb", "poc"],
        "common_commands": [
            {"label": "Search exploit", "cmd": "searchsploit {query}"},
            {"label": "Copy exploit", "cmd": "searchsploit -m {id}"},
        ]
    },
    {
        "name": "sqlmap",
        "category": "exploitation",
        "package": "sqlmap",
        "description": "Automatic SQL injection tool",
        "needs_root": False,
        "keywords": ["sql", "injection", "sqli", "database", "dump", "sqlmap"],
        "common_commands": [
            {"label": "Test URL", "cmd": "sqlmap -u '{url}' --batch"},
            {"label": "Dump DB", "cmd": "sqlmap -u '{url}' --dbs --batch"},
            {"label": "Full auto", "cmd": "sqlmap -u '{url}' --batch --risk 3 --level 5"},
        ]
    },
    {
        "name": "crackmapexec",
        "category": "exploitation",
        "package": "crackmapexec",
        "description": "Post-exploitation / network pentesting",
        "needs_root": False,
        "keywords": ["smb", "rdp", "ssh", "winrm", "lateral", "cme", "crackmapexec", "creds"],
        "common_commands": [
            {"label": "SMB enum", "cmd": "crackmapexec smb {target}/24"},
            {"label": "Spray creds", "cmd": "crackmapexec smb {target} -u {user} -p {pass}"},
        ]
    },

    # ── Web Testing ──
    {
        "name": "burpsuite",
        "category": "web_testing",
        "package": "burpsuite",
        "description": "Web application security testing platform",
        "needs_root": False,
        "keywords": ["web", "proxy", "burp", "intercept", "http", "request", "response"],
        "common_commands": [
            {"label": "Launch Burp", "cmd": "burpsuite"},
        ]
    },
    {
        "name": "nikto",
        "category": "web_testing",
        "package": "nikto",
        "description": "Web server vulnerability scanner",
        "needs_root": False,
        "keywords": ["web", "scan", "server", "vulnerability", "nikto", "http"],
        "common_commands": [
            {"label": "Scan site", "cmd": "nikto -h {target}"},
            {"label": "With SSL", "cmd": "nikto -h {target} -ssl"},
        ]
    },
    {
        "name": "dirb",
        "category": "web_testing",
        "package": "dirb",
        "description": "Web content scanner / directory brute forcer",
        "needs_root": False,
        "keywords": ["directory", "brute", "web", "path", "hidden", "dir", "enum"],
        "common_commands": [
            {"label": "Dir scan", "cmd": "dirb http://{target}"},
            {"label": "Custom wordlist", "cmd": "dirb http://{target} {wordlist}"},
        ]
    },
    {
        "name": "gobuster",
        "category": "web_testing",
        "package": "gobuster",
        "description": "Directory/file & DNS busting tool",
        "needs_root": False,
        "keywords": ["directory", "brute", "web", "path", "gobuster", "fuzz", "vhost"],
        "common_commands": [
            {"label": "Dir mode", "cmd": "gobuster dir -u http://{target} -w /usr/share/wordlists/dirb/common.txt"},
            {"label": "DNS mode", "cmd": "gobuster dns -d {domain} -w /usr/share/wordlists/dirb/common.txt"},
        ]
    },
    {
        "name": "wpscan",
        "category": "web_testing",
        "package": "wpscan",
        "description": "WordPress vulnerability scanner",
        "needs_root": False,
        "keywords": ["wordpress", "wp", "cms", "plugin", "theme", "wpscan"],
        "common_commands": [
            {"label": "Scan WP site", "cmd": "wpscan --url http://{target}"},
            {"label": "Enumerate users", "cmd": "wpscan --url http://{target} -e u"},
        ]
    },
    {
        "name": "whatweb",
        "category": "web_testing",
        "package": "whatweb",
        "description": "Web technology identifier",
        "needs_root": False,
        "keywords": ["web", "tech", "identify", "fingerprint", "cms", "framework"],
        "common_commands": [
            {"label": "Identify tech", "cmd": "whatweb {target}"},
        ]
    },
    {
        "name": "ffuf",
        "category": "web_testing",
        "package": "ffuf",
        "description": "Fast web fuzzer",
        "needs_root": False,
        "keywords": ["fuzz", "web", "brute", "parameter", "ffuf"],
        "common_commands": [
            {"label": "Dir fuzz", "cmd": "ffuf -u http://{target}/FUZZ -w /usr/share/wordlists/dirb/common.txt"},
        ]
    },

    # ── Password Attacks ──
    {
        "name": "john",
        "category": "password",
        "package": "john",
        "description": "John the Ripper password cracker",
        "needs_root": False,
        "keywords": ["password", "crack", "hash", "john", "ripper", "brute", "dictionary"],
        "common_commands": [
            {"label": "Crack hashes", "cmd": "john --wordlist=/usr/share/wordlists/rockyou.txt {hashfile}"},
            {"label": "Show cracked", "cmd": "john --show {hashfile}"},
        ]
    },
    {
        "name": "hashcat",
        "category": "password",
        "package": "hashcat",
        "description": "Advanced password recovery (GPU)",
        "needs_root": False,
        "keywords": ["password", "crack", "hash", "gpu", "hashcat", "brute", "mask"],
        "common_commands": [
            {"label": "Dictionary attack", "cmd": "hashcat -m {mode} {hashfile} /usr/share/wordlists/rockyou.txt"},
            {"label": "Brute force", "cmd": "hashcat -m {mode} -a 3 {hashfile} ?a?a?a?a?a?a"},
        ]
    },
    {
        "name": "hydra",
        "category": "password",
        "package": "hydra",
        "description": "Network login brute forcer",
        "needs_root": False,
        "keywords": ["brute", "login", "ssh", "ftp", "http", "rdp", "hydra", "password", "spray"],
        "common_commands": [
            {"label": "SSH brute", "cmd": "hydra -l {user} -P /usr/share/wordlists/rockyou.txt ssh://{target}"},
            {"label": "HTTP form", "cmd": "hydra -l {user} -P /usr/share/wordlists/rockyou.txt {target} http-post-form '{path}:{params}:{fail_string}'"},
            {"label": "FTP brute", "cmd": "hydra -l {user} -P /usr/share/wordlists/rockyou.txt ftp://{target}"},
        ]
    },
    {
        "name": "medusa",
        "category": "password",
        "package": "medusa",
        "description": "Parallel network login brute forcer",
        "needs_root": False,
        "keywords": ["brute", "login", "parallel", "medusa", "password"],
        "common_commands": [
            {"label": "SSH brute", "cmd": "medusa -h {target} -u {user} -P /usr/share/wordlists/rockyou.txt -M ssh"},
        ]
    },
    {
        "name": "crunch",
        "category": "password",
        "package": "crunch",
        "description": "Wordlist generator",
        "needs_root": False,
        "keywords": ["wordlist", "generate", "custom", "crunch", "password list"],
        "common_commands": [
            {"label": "Generate wordlist", "cmd": "crunch {min} {max} {charset} -o wordlist.txt"},
        ]
    },

    # ── Sniffing & Spoofing ──
    {
        "name": "wireshark",
        "category": "sniffing",
        "package": "wireshark",
        "description": "Network protocol analyzer",
        "needs_root": True,
        "keywords": ["capture", "packet", "sniff", "pcap", "wireshark", "traffic", "analyze"],
        "common_commands": [
            {"label": "Launch GUI", "cmd": "wireshark"},
            {"label": "CLI capture", "cmd": "tshark -i {iface} -w capture.pcap"},
        ]
    },
    {
        "name": "tcpdump",
        "category": "sniffing",
        "package": "tcpdump",
        "description": "Command-line packet analyzer",
        "needs_root": True,
        "keywords": ["capture", "packet", "sniff", "tcpdump", "traffic", "dump"],
        "common_commands": [
            {"label": "Capture all", "cmd": "tcpdump -i {iface} -w capture.pcap"},
            {"label": "Filter host", "cmd": "tcpdump -i {iface} host {target}"},
        ]
    },
    {
        "name": "ettercap",
        "category": "sniffing",
        "package": "ettercap-text-only",
        "description": "Man-in-the-middle attack suite",
        "needs_root": True,
        "keywords": ["mitm", "arp", "spoof", "poison", "ettercap", "intercept"],
        "common_commands": [
            {"label": "ARP poison", "cmd": "ettercap -T -M arp:remote /{gateway}// /{target}//"},
        ]
    },
    {
        "name": "responder",
        "category": "sniffing",
        "package": "responder",
        "description": "LLMNR/NBT-NS/mDNS poisoner",
        "needs_root": True,
        "keywords": ["responder", "llmnr", "ntlm", "hash", "poison", "netbios"],
        "common_commands": [
            {"label": "Start responder", "cmd": "responder -I {iface}"},
        ]
    },
    {
        "name": "macchanger",
        "category": "sniffing",
        "package": "macchanger",
        "description": "MAC address changer",
        "needs_root": True,
        "keywords": ["mac", "address", "change", "spoof", "random", "macchanger"],
        "common_commands": [
            {"label": "Random MAC", "cmd": "macchanger -r {iface}"},
            {"label": "Reset MAC", "cmd": "macchanger -p {iface}"},
        ]
    },

    # ── Social Engineering ──
    {
        "name": "setoolkit",
        "category": "social_engineering",
        "package": "set",
        "description": "Social Engineering Toolkit",
        "needs_root": True,
        "keywords": ["social", "phishing", "clone", "credential", "setoolkit", "se"],
        "common_commands": [
            {"label": "Launch SET", "cmd": "setoolkit"},
        ]
    },
    {
        "name": "beef-xss",
        "category": "social_engineering",
        "package": "beef-xss",
        "description": "Browser Exploitation Framework",
        "needs_root": True,
        "keywords": ["browser", "xss", "hook", "beef", "exploit"],
        "common_commands": [
            {"label": "Start BeEF", "cmd": "beef-xss"},
        ]
    },

    # ── Forensics ──
    {
        "name": "autopsy",
        "category": "forensics",
        "package": "autopsy",
        "description": "Digital forensics platform",
        "needs_root": False,
        "keywords": ["forensic", "disk", "image", "recover", "autopsy", "evidence"],
        "common_commands": [
            {"label": "Launch Autopsy", "cmd": "autopsy"},
        ]
    },
    {
        "name": "binwalk",
        "category": "forensics",
        "package": "binwalk",
        "description": "Firmware analysis / extraction",
        "needs_root": False,
        "keywords": ["firmware", "extract", "binary", "binwalk", "analyze"],
        "common_commands": [
            {"label": "Analyze", "cmd": "binwalk {file}"},
            {"label": "Extract", "cmd": "binwalk -e {file}"},
        ]
    },
    {
        "name": "volatility",
        "category": "forensics",
        "package": "volatility3",
        "description": "Memory forensics framework",
        "needs_root": False,
        "keywords": ["memory", "ram", "dump", "forensic", "volatility", "process"],
        "common_commands": [
            {"label": "Image info", "cmd": "vol3 -f {dump} windows.info"},
            {"label": "Process list", "cmd": "vol3 -f {dump} windows.pslist"},
        ]
    },
    {
        "name": "foremost",
        "category": "forensics",
        "package": "foremost",
        "description": "File carving / recovery",
        "needs_root": False,
        "keywords": ["carve", "recover", "file", "deleted", "foremost", "image"],
        "common_commands": [
            {"label": "Carve files", "cmd": "foremost -i {image} -o output/"},
        ]
    },

    # ── Reverse Engineering ──
    {
        "name": "ghidra",
        "category": "reverse_engineering",
        "package": "ghidra",
        "description": "NSA reverse engineering framework",
        "needs_root": False,
        "keywords": ["reverse", "decompile", "binary", "ghidra", "disassemble", "malware"],
        "common_commands": [
            {"label": "Launch Ghidra", "cmd": "ghidra"},
        ]
    },
    {
        "name": "radare2",
        "category": "reverse_engineering",
        "package": "radare2",
        "description": "Reverse engineering framework (CLI)",
        "needs_root": False,
        "keywords": ["reverse", "debug", "binary", "radare", "r2", "disassemble"],
        "common_commands": [
            {"label": "Analyze binary", "cmd": "r2 -A {binary}"},
        ]
    },

    # ── Vuln Analysis ──
    {
        "name": "openvas",
        "category": "vuln_analysis",
        "package": "gvm",
        "description": "Full vulnerability scanner (Greenbone)",
        "needs_root": True,
        "keywords": ["vulnerability", "scan", "openvas", "gvm", "greenbone", "assessment"],
        "common_commands": [
            {"label": "Start GVM", "cmd": "gvm-start"},
        ]
    },
    {
        "name": "lynis",
        "category": "vuln_analysis",
        "package": "lynis",
        "description": "Security auditing for Unix systems",
        "needs_root": True,
        "keywords": ["audit", "hardening", "lynis", "compliance", "linux"],
        "common_commands": [
            {"label": "System audit", "cmd": "lynis audit system"},
        ]
    },
    {
        "name": "legion",
        "category": "vuln_analysis",
        "package": "legion",
        "description": "Network penetration testing framework",
        "needs_root": True,
        "keywords": ["auto", "scan", "legion", "pentest", "recon"],
        "common_commands": [
            {"label": "Launch Legion", "cmd": "legion"},
        ]
    },

    # ── Stress Testing & DoS ──
    {
        "name": "hping3",
        "category": "stress_testing",
        "package": "hping3",
        "description": "TCP/IP packet assembler and analyzer — SYN/UDP/ICMP floods",
        "needs_root": True,
        "keywords": ["stress", "flood", "dos", "ddos", "syn", "udp", "icmp", "hping", "packet", "attack", "test", "load"],
        "common_commands": [
            {"label": "SYN flood port 80", "cmd": "hping3 -S --flood -V -p 80 {target}"},
            {"label": "SYN flood custom port", "cmd": "hping3 -S --flood -V -p {port} {target}"},
            {"label": "UDP flood", "cmd": "hping3 --udp --flood -p 53 {target}"},
            {"label": "ICMP flood", "cmd": "hping3 --icmp --flood {target}"},
            {"label": "SYN + random source", "cmd": "hping3 -S --flood --rand-source -p 80 {target}"},
            {"label": "Christmas tree attack", "cmd": "hping3 --flood -FSRPAU -p 80 {target}"},
            {"label": "Land attack", "cmd": "hping3 -S -a {target} -p 80 --flood {target}"},
            {"label": "Smurf attack", "cmd": "hping3 --icmp --flood -a {target} {subnet}"},
            {"label": "SYN scan (port range)", "cmd": "hping3 -S {target} -p 1-1000 --scan"},
            {"label": "Data payload flood", "cmd": "hping3 -S --flood -d 1200 -p 80 {target}"},
        ]
    },
    {
        "name": "slowloris",
        "category": "stress_testing",
        "package": "slowloris",
        "description": "Low-bandwidth HTTP DoS — keeps connections open to exhaust server",
        "needs_root": False,
        "keywords": ["slowloris", "http", "dos", "slow", "connections", "web", "apache", "stress", "flood", "exhaust"],
        "common_commands": [
            {"label": "HTTP slowloris (500 sockets)", "cmd": "slowloris {target} -p 80 -s 500"},
            {"label": "HTTPS slowloris", "cmd": "slowloris {target} -p 443 -s 500 --https"},
            {"label": "Custom port + sockets", "cmd": "slowloris {target} -p {port} -s 1000"},
            {"label": "Stealth (slow rate)", "cmd": "slowloris {target} -p 80 -s 200 --sleeptime 10"},
        ]
    },
    {
        "name": "ufonet",
        "category": "stress_testing",
        "package": "ufonet",
        "description": "DDoS botnet tool — uses open redirects as amplifiers",
        "needs_root": False,
        "keywords": ["ufonet", "ddos", "botnet", "amplify", "redirect", "dos", "distributed", "attack", "stress"],
        "common_commands": [
            {"label": "Attack target", "cmd": "ufonet -a {target} -r 500 --threads 200"},
            {"label": "Search zombies", "cmd": "ufonet -s '{target}' --sa"},
            {"label": "Download zombies", "cmd": "ufonet --download-zombies"},
            {"label": "Attack with all methods", "cmd": "ufonet -a {target} -r 1000 --threads 500 --db"},
        ]
    },
    {
        "name": "goldeneye",
        "category": "stress_testing",
        "package": "goldeneye",
        "description": "HTTP DoS tool — keep-alive + cache bypass flood",
        "needs_root": False,
        "keywords": ["goldeneye", "http", "dos", "flood", "stress", "web", "keepalive", "test"],
        "common_commands": [
            {"label": "HTTP flood", "cmd": "goldeneye http://{target} -w 50 -s 500"},
            {"label": "Custom workers", "cmd": "goldeneye http://{target} -w 100 -s 1000 -m random"},
        ]
    },
    {
        "name": "xerxes",
        "category": "stress_testing",
        "package": "xerxes",
        "description": "Powerful DoS tool for stress testing web servers",
        "needs_root": False,
        "keywords": ["xerxes", "dos", "flood", "stress", "web", "server", "test"],
        "common_commands": [
            {"label": "Attack target", "cmd": "xerxes {target} 80"},
            {"label": "Custom port", "cmd": "xerxes {target} {port}"},
        ]
    },
    {
        "name": "thc-ssl-dos",
        "category": "stress_testing",
        "package": "thc-ssl-dos",
        "description": "SSL/TLS renegotiation DoS — exploits SSL handshake cost",
        "needs_root": False,
        "keywords": ["ssl", "tls", "dos", "renegotiation", "https", "stress", "thc", "handshake"],
        "common_commands": [
            {"label": "SSL DoS", "cmd": "thc-ssl-dos {target} 443 --accept"},
            {"label": "Custom port", "cmd": "thc-ssl-dos {target} {port} --accept"},
        ]
    },

    # ── System / Utilities ──
    {
        "name": "tor",
        "category": "system",
        "package": "tor",
        "description": "Anonymity network",
        "needs_root": True,
        "keywords": ["anonymous", "tor", "onion", "proxy", "hidden"],
        "common_commands": [
            {"label": "Start Tor", "cmd": "service tor start"},
            {"label": "Check status", "cmd": "service tor status"},
        ]
    },
    {
        "name": "proxychains",
        "category": "system",
        "package": "proxychains4",
        "description": "Force TCP through proxy (Tor/SOCKS)",
        "needs_root": False,
        "keywords": ["proxy", "chain", "tor", "tunnel", "anonymous", "proxychains"],
        "common_commands": [
            {"label": "Via Tor", "cmd": "proxychains4 {command}"},
        ]
    },
    {
        "name": "tmux",
        "category": "system",
        "package": "tmux",
        "description": "Terminal multiplexer",
        "needs_root": False,
        "keywords": ["terminal", "session", "tmux", "split", "multiplex"],
        "common_commands": [
            {"label": "New session", "cmd": "tmux new -s {name}"},
            {"label": "List sessions", "cmd": "tmux ls"},
        ]
    },
    {
        "name": "netcat",
        "category": "system",
        "package": "ncat",
        "description": "TCP/UDP networking utility",
        "needs_root": False,
        "keywords": ["nc", "netcat", "listener", "reverse", "shell", "connect", "port"],
        "common_commands": [
            {"label": "Listener", "cmd": "nc -lvnp {port}"},
            {"label": "Connect", "cmd": "nc {target} {port}"},
            {"label": "Reverse shell", "cmd": "nc -lvnp {port}"},
        ]
    },
    {
        "name": "socat",
        "category": "system",
        "package": "socat",
        "description": "Multipurpose relay (advanced netcat)",
        "needs_root": False,
        "keywords": ["relay", "tunnel", "socat", "redirect", "port forward"],
        "common_commands": [
            {"label": "TCP listener", "cmd": "socat TCP-LISTEN:{port},reuseaddr,fork EXEC:/bin/bash"},
        ]
    },
    {
        "name": "ssh",
        "category": "system",
        "package": "openssh-client",
        "description": "Secure Shell client",
        "needs_root": False,
        "keywords": ["ssh", "remote", "connect", "tunnel", "port forward", "key"],
        "common_commands": [
            {"label": "Connect", "cmd": "ssh {user}@{target}"},
            {"label": "Tunnel", "cmd": "ssh -L {lport}:{rhost}:{rport} {user}@{target}"},
            {"label": "SOCKS proxy", "cmd": "ssh -D 1080 {user}@{target}"},
        ]
    },
    {
        "name": "curl",
        "category": "system",
        "package": "curl",
        "description": "HTTP client / data transfer",
        "needs_root": False,
        "keywords": ["http", "request", "download", "api", "curl", "get", "post"],
        "common_commands": [
            {"label": "GET request", "cmd": "curl -v {url}"},
            {"label": "POST data", "cmd": "curl -X POST -d '{data}' {url}"},
        ]
    },
    {
        "name": "impacket",
        "category": "exploitation",
        "package": "python3-impacket",
        "description": "Network protocol Python tools (SMB, NTLM, Kerberos)",
        "needs_root": False,
        "keywords": ["smb", "ntlm", "kerberos", "impacket", "psexec", "wmiexec", "secretsdump", "pass the hash"],
        "common_commands": [
            {"label": "PSExec", "cmd": "impacket-psexec {domain}/{user}:{pass}@{target}"},
            {"label": "SecretsDump", "cmd": "impacket-secretsdump {domain}/{user}:{pass}@{target}"},
            {"label": "SMBClient", "cmd": "impacket-smbclient {domain}/{user}:{pass}@{target}"},
        ]
    },
    {
        "name": "chisel",
        "category": "system",
        "package": "chisel",
        "description": "TCP/UDP tunnel over HTTP",
        "needs_root": False,
        "keywords": ["tunnel", "pivot", "chisel", "port forward", "http tunnel"],
        "common_commands": [
            {"label": "Server", "cmd": "chisel server --reverse -p 8080"},
            {"label": "Client", "cmd": "chisel client {server}:8080 R:{rport}:127.0.0.1:{lport}"},
        ]
    },
]


def find_tools_by_keywords(query: str, top_n: int = 5) -> list:
    """Score and rank tools by keyword match against a user query."""
    query_lower = query.lower()
    words = query_lower.split()
    scored = []
    for tool in TOOLS:
        score = 0
        # exact tool name match
        if tool["name"] in query_lower:
            score += 100
        # keyword matches
        for kw in tool["keywords"]:
            for w in words:
                if w in kw or kw in query_lower:
                    score += 10
        # category name match
        cat = TOOL_CATEGORIES.get(tool["category"], {})
        if cat.get("name", "").lower() in query_lower:
            score += 15
        if score > 0:
            scored.append((score, tool))
    scored.sort(key=lambda x: -x[0])
    return [t for _, t in scored[:top_n]]


def get_tools_by_category(category: str) -> list:
    return [t for t in TOOLS if t["category"] == category]


def get_tool_by_name(name: str):
    for t in TOOLS:
        if t["name"] == name:
            return t
    return None


def get_all_packages() -> list:
    """Return list of all apt package names for bulk install."""
    return list(set(t["package"] for t in TOOLS))
