#!/bin/bash
# ============================================================
#  MAXIM Installer — Kali Linux Penetration Testing Suite
# ============================================================

set -e

RED='\033[0;31m'
GREEN='\033[0;32m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
YELLOW='\033[1;33m'
BOLD='\033[1m'
NC='\033[0m'

echo -e "${BLUE}${BOLD}"
echo "  ███╗   ███╗ █████╗ ██╗  ██╗██╗███╗   ███╗"
echo "  ████╗ ████║██╔══██╗╚██╗██╔╝██║████╗ ████║"
echo "  ██╔████╔██║███████║ ╚███╔╝ ██║██╔████╔██║"
echo "  ██║╚██╔╝██║██╔══██║ ██╔██╗ ██║██║╚██╔╝██║"
echo "  ██║ ╚═╝ ██║██║  ██║██╔╝ ██╗██║██║ ╚═╝ ██║"
echo "  ╚═╝     ╚═╝╚═╝  ╚═╝╚═╝  ╚═╝╚═╝╚═╝     ╚═╝"
echo -e "${NC}"
echo -e "${CYAN}  Penetration Testing Command Center — v1.0${NC}"
echo ""

MAXIM_DIR="$(cd "$(dirname "$0")" && pwd)"

# ── Step 1: System dependencies ──
echo -e "${GREEN}[1/6]${NC} Installing system dependencies..."
sudo apt-get update -qq
sudo apt-get install -y -qq \
    python3 python3-pip python3-venv python3-pyqt5 \
    fonts-inter \
    curl wget git 2>/dev/null

# Install JetBrains Mono for terminal
if ! fc-list | grep -qi "JetBrains"; then
    echo -e "  Installing JetBrains Mono font..."
    mkdir -p ~/.local/share/fonts
    curl -sL "https://github.com/JetBrains/JetBrainsMono/releases/download/v2.304/JetBrainsMono-2.304.zip" -o /tmp/jbm.zip
    unzip -qo /tmp/jbm.zip -d /tmp/jbm 2>/dev/null
    cp /tmp/jbm/fonts/ttf/*.ttf ~/.local/share/fonts/ 2>/dev/null || true
    fc-cache -f 2>/dev/null || true
    rm -rf /tmp/jbm /tmp/jbm.zip
fi

# ── Step 2: Python venv ──
echo -e "${GREEN}[2/6]${NC} Setting up Python environment..."
if [ ! -d "$MAXIM_DIR/venv" ]; then
    python3 -m venv "$MAXIM_DIR/venv" --system-site-packages
fi
source "$MAXIM_DIR/venv/bin/activate"
pip install --quiet --upgrade pip

# ── Step 3: Install Maxim ──
echo -e "${GREEN}[3/6]${NC} Installing Maxim..."
cd "$MAXIM_DIR"
pip install --quiet -e .

# ── Step 4: Install Ollama ──
echo -e "${GREEN}[4/6]${NC} Installing Ollama (offline AI)..."
if ! command -v ollama &> /dev/null; then
    curl -fsSL https://ollama.com/install.sh | sh
    sudo systemctl enable ollama 2>/dev/null || true
    sudo systemctl start ollama 2>/dev/null || true
    sleep 2
    echo -e "${CYAN}  Pulling Mistral model...${NC}"
    ollama pull mistral || echo -e "${YELLOW}  Model pull failed — do it later from the app${NC}"
else
    echo -e "  Ollama already installed"
fi

# ── Step 5: Install pentest tools ──
echo -e "${GREEN}[5/6]${NC} Installing essential pentest tools..."
ESSENTIAL_TOOLS=(
    nmap masscan netdiscover
    aircrack-ng wifite reaver bettercap
    metasploit-framework exploitdb
    sqlmap nikto gobuster dirb ffuf whatweb wpscan
    john hashcat hydra medusa crunch
    wireshark tcpdump ettercap-text-only responder macchanger
    set beef-xss
    binwalk foremost
    tor proxychains4 ncat socat
    enum4linux theharvester dnsenum whois
    lynis tmux
)

echo -e "  Installing ${#ESSENTIAL_TOOLS[@]} packages..."
sudo apt-get install -y -qq ${ESSENTIAL_TOOLS[@]} 2>/dev/null || {
    echo -e "${YELLOW}  Some packages failed — installing individually...${NC}"
    for pkg in "${ESSENTIAL_TOOLS[@]}"; do
        sudo apt-get install -y -qq "$pkg" 2>/dev/null || \
            echo -e "  ${RED}[!] Failed: $pkg${NC}"
    done
}

# ── Step 6: Create launchers ──
echo -e "${GREEN}[6/6]${NC} Creating launchers..."

# Desktop entry
mkdir -p ~/.local/share/applications
cat > ~/.local/share/applications/maxim.desktop << EOF
[Desktop Entry]
Name=Maxim
Comment=Penetration Testing Command Center
Exec=bash -c 'cd $MAXIM_DIR && source venv/bin/activate && python3 -m maxim.main'
Icon=utilities-terminal
Terminal=false
Type=Application
Categories=System;Security;
Keywords=pentest;kali;security;
EOF

# CLI launcher
sudo tee /usr/local/bin/maxim > /dev/null << EOF
#!/bin/bash
cd "$MAXIM_DIR"
source venv/bin/activate 2>/dev/null || true
exec python3 -m maxim.main "\$@"
EOF
sudo chmod +x /usr/local/bin/maxim

# Update script
cat > "$MAXIM_DIR/update.sh" << 'EOF'
#!/bin/bash
echo "Updating Maxim..."
cd "$(dirname "$0")"
git pull origin main
source venv/bin/activate 2>/dev/null
pip install -e . --quiet
echo "Done! Restart Maxim to apply."
EOF
chmod +x "$MAXIM_DIR/update.sh"

echo ""
echo -e "${GREEN}${BOLD}  Installation complete!${NC}"
echo ""
echo -e "  ${BOLD}Launch:${NC}"
echo -e "    ${CYAN}maxim${NC}              (from any terminal)"
echo -e "    ${CYAN}Applications menu${NC}  (look for Maxim)"
echo ""
echo -e "  ${BOLD}Update:${NC}"
echo -e "    ${CYAN}./update.sh${NC}        (or Help > Check for Updates in the app)"
echo ""
echo -e "  ${BOLD}AI:${NC}"
echo -e "    Ollama: $(command -v ollama &>/dev/null && echo -e "${GREEN}installed${NC}" || echo -e "${RED}not found${NC}")"
echo -e "    Models: $(ollama list 2>/dev/null | tail -n +2 | awk '{print $1}' | tr '\n' ', ' || echo "none")"
echo -e "    ${CYAN}Online AI: set API keys in app (AI tab > API Key button)${NC}"
echo ""
