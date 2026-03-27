# MAXIM — Penetration Testing Command Center

A desktop GUI for Kali Linux that manages 40+ pentest tools with an AI assistant (offline + online).

## Install on Kali Linux

```bash
git clone https://github.com/Dragan2026/maxim.git
cd maxim
chmod +x install.sh
./install.sh
```

Then run:
```bash
maxim
```

## Features

- **Smart Prompt** — type naturally: "scan network", "monitor mode wlan0", "crack wifi"
- **40+ Tools** — nmap, aircrack-ng, metasploit, sqlmap, hydra, wireshark, etc.
- **7 Workflow Phases** — Recon, Enumeration, Vuln Scan, Exploitation, Post-Exploit, Wireless, Reporting
- **AI Assistant** — offline (Ollama) + online (OpenAI, Claude, Gemini, Groq, OpenRouter)
- **Auto-fallback** — if offline AI can't answer, automatically tries online
- **Online Tools** — Shodan, VirusTotal, CrackStation, GTFOBins, RevShells, etc.
- **Session Logging** — every command tracked
- **Auto-Update** — `./update.sh` or Help > Check for Updates

## Update

```bash
cd maxim
./update.sh
```

## AI Setup

**Offline (no internet):**
```bash
ollama pull mistral
```

**Online (optional):**
Set API keys in the AI tab — supports OpenAI, Claude, Gemini, Groq, OpenRouter.

## Requirements

- Kali Linux (or Debian + Kali repos)
- Python 3.10+
- PyQt5
