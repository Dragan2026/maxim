"""
Maxim AI Assistant — Supports both offline (Ollama) and online AI providers.
Providers: Ollama (local), OpenAI, Anthropic Claude, Google Gemini, Groq
"""

import json
import subprocess
import urllib.request
import urllib.error
import os
from pathlib import Path
from maxim.tools.tool_registry import (
    find_tools_by_keywords, get_tool_by_name, TOOLS, TOOL_CATEGORIES
)

OLLAMA_URL = "http://127.0.0.1:11434"
DEFAULT_MODEL = "mistral"

# Config file for API keys
CONFIG_FILE = Path.home() / ".maxim" / "ai_config.json"

SYSTEM_PROMPT = """You are Maxim AI, an expert penetration testing assistant built into the Maxim security toolkit on Kali Linux.

Your capabilities:
- Suggest the right Kali Linux tools for any security task
- Explain command outputs and scan results
- Build multi-step attack workflows
- Help with networking, WiFi, exploitation, web testing, forensics, password cracking
- Execute system commands when asked

Rules:
- Always specify exact commands with correct syntax
- Warn about legal implications when relevant
- If multiple tools can do the job, list them and ask which the user prefers
- Format commands in code blocks
- Be concise and actionable
- When suggesting monitor mode, always remind to check interface name with `airmon-ng` first
- For any scan, suggest saving output to a file
- This is for AUTHORIZED penetration testing only

You have access to these tool categories: """ + ", ".join(
    cat["name"] for cat in TOOL_CATEGORIES.values()
)

# ═══════════════════════════════════════════════════
#  PROVIDER DEFINITIONS
# ═══════════════════════════════════════════════════

PROVIDERS = {
    "ollama": {
        "name": "Ollama (Offline)",
        "type": "local",
        "needs_key": False,
        "url": "http://127.0.0.1:11434",
        "models": ["mistral", "llama3", "phi3", "gemma2", "codellama", "deepseek-coder"],
        "description": "Local LLM — fully offline, no internet needed",
    },
    "openai": {
        "name": "OpenAI",
        "type": "online",
        "needs_key": True,
        "url": "https://api.openai.com/v1/chat/completions",
        "models": ["gpt-4o", "gpt-4o-mini", "gpt-4-turbo", "gpt-3.5-turbo", "o1-mini"],
        "description": "OpenAI GPT models — powerful general-purpose AI",
        "key_env": "OPENAI_API_KEY",
        "key_url": "https://platform.openai.com/api-keys",
    },
    "anthropic": {
        "name": "Anthropic Claude",
        "type": "online",
        "needs_key": True,
        "url": "https://api.anthropic.com/v1/messages",
        "models": ["claude-sonnet-4-6", "claude-haiku-4-5-20251001", "claude-opus-4-6"],
        "description": "Anthropic Claude — excellent reasoning & code",
        "key_env": "ANTHROPIC_API_KEY",
        "key_url": "https://console.anthropic.com/settings/keys",
    },
    "gemini": {
        "name": "Google Gemini",
        "type": "online",
        "needs_key": True,
        "url": "https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent",
        "models": ["gemini-2.0-flash", "gemini-2.5-pro", "gemini-2.5-flash"],
        "description": "Google Gemini — fast and capable",
        "key_env": "GEMINI_API_KEY",
        "key_url": "https://aistudio.google.com/apikey",
    },
    "groq": {
        "name": "Groq",
        "type": "online",
        "needs_key": True,
        "url": "https://api.groq.com/openai/v1/chat/completions",
        "models": ["llama-3.3-70b-versatile", "llama-3.1-8b-instant", "mixtral-8x7b-32768", "gemma2-9b-it"],
        "description": "Groq — ultra-fast inference (free tier available)",
        "key_env": "GROQ_API_KEY",
        "key_url": "https://console.groq.com/keys",
    },
    "openrouter": {
        "name": "OpenRouter",
        "type": "online",
        "needs_key": True,
        "url": "https://openrouter.ai/api/v1/chat/completions",
        "models": ["anthropic/claude-sonnet-4-6", "openai/gpt-4o", "google/gemini-2.0-flash-exp:free",
                    "meta-llama/llama-3.3-70b-instruct:free", "mistralai/mistral-large"],
        "description": "OpenRouter — access many models with one key (has free models)",
        "key_env": "OPENROUTER_API_KEY",
        "key_url": "https://openrouter.ai/keys",
    },
}


# ═══════════════════════════════════════════════════
#  CONFIG MANAGEMENT
# ═══════════════════════════════════════════════════

def load_config() -> dict:
    """Load saved API keys and preferences."""
    try:
        if CONFIG_FILE.exists():
            return json.loads(CONFIG_FILE.read_text())
    except Exception:
        pass
    return {"provider": "ollama", "model": "mistral", "keys": {}}


def save_config(config: dict):
    """Save API keys and preferences."""
    CONFIG_FILE.parent.mkdir(exist_ok=True)
    CONFIG_FILE.write_text(json.dumps(config, indent=2))


def get_api_key(provider_id: str) -> str:
    """Get API key from config or environment."""
    config = load_config()
    # Check config file first
    key = config.get("keys", {}).get(provider_id, "")
    if key:
        return key
    # Fall back to environment variable
    prov = PROVIDERS.get(provider_id, {})
    env_var = prov.get("key_env", "")
    if env_var:
        return os.environ.get(env_var, "")
    return ""


def set_api_key(provider_id: str, key: str):
    """Save API key to config."""
    config = load_config()
    if "keys" not in config:
        config["keys"] = {}
    config["keys"][provider_id] = key
    save_config(config)


# ═══════════════════════════════════════════════════
#  OLLAMA (LOCAL / OFFLINE)
# ═══════════════════════════════════════════════════

class OllamaAI:
    """Interface to local Ollama LLM."""

    def __init__(self, model: str = DEFAULT_MODEL):
        self.model = model
        self.conversation = []
        self.available = False
        self._check_availability()

    def _check_availability(self):
        try:
            req = urllib.request.Request(f"{OLLAMA_URL}/api/tags")
            with urllib.request.urlopen(req, timeout=3) as resp:
                data = json.loads(resp.read())
                models = [m["name"].split(":")[0] for m in data.get("models", [])]
                self.available = True
                if self.model not in models and models:
                    self.model = models[0]
        except Exception:
            self.available = False

    def is_available(self) -> bool:
        return self.available

    def get_installed_models(self) -> list:
        try:
            req = urllib.request.Request(f"{OLLAMA_URL}/api/tags")
            with urllib.request.urlopen(req, timeout=3) as resp:
                data = json.loads(resp.read())
                return [m["name"] for m in data.get("models", [])]
        except Exception:
            return []

    def pull_model(self, model: str, callback=None):
        proc = subprocess.Popen(
            f"ollama pull {model}", shell=True,
            stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
            universal_newlines=True
        )
        for line in iter(proc.stdout.readline, ""):
            if callback:
                callback(line.strip())
        proc.wait()
        self._check_availability()
        return proc.returncode == 0

    def chat(self, user_message: str, stream_callback=None) -> str:
        self.conversation.append({"role": "user", "content": user_message})
        messages = [{"role": "system", "content": SYSTEM_PROMPT}] + \
                   self.conversation[-20:]

        payload = json.dumps({
            "model": self.model,
            "messages": messages,
            "stream": stream_callback is not None,
        }).encode()

        req = urllib.request.Request(
            f"{OLLAMA_URL}/api/chat",
            data=payload,
            headers={"Content-Type": "application/json"},
            method="POST"
        )

        try:
            with urllib.request.urlopen(req, timeout=120) as resp:
                if stream_callback:
                    full_response = []
                    for line in resp:
                        try:
                            chunk = json.loads(line)
                            token = chunk.get("message", {}).get("content", "")
                            if token:
                                full_response.append(token)
                                stream_callback(token)
                        except json.JSONDecodeError:
                            pass
                    assistant_msg = "".join(full_response)
                else:
                    data = json.loads(resp.read())
                    assistant_msg = data.get("message", {}).get("content", "")

            self.conversation.append({"role": "assistant", "content": assistant_msg})
            return assistant_msg
        except Exception as e:
            return f"[AI Error] {e}"

    def clear_context(self):
        self.conversation.clear()


# ═══════════════════════════════════════════════════
#  ONLINE AI PROVIDERS
# ═══════════════════════════════════════════════════

class OnlineAI:
    """Unified interface for online AI providers (OpenAI, Claude, Gemini, Groq, OpenRouter)."""

    def __init__(self, provider_id: str = "openai", model: str = None):
        self.provider_id = provider_id
        self.provider = PROVIDERS.get(provider_id, PROVIDERS["openai"])
        self.model = model or self.provider["models"][0]
        self.conversation = []
        self.api_key = get_api_key(provider_id)

    def is_available(self) -> bool:
        return bool(self.api_key)

    def set_key(self, key: str):
        self.api_key = key
        set_api_key(self.provider_id, key)

    def get_models(self) -> list:
        return self.provider.get("models", [])

    def chat(self, user_message: str, stream_callback=None) -> str:
        if not self.api_key:
            return f"[Error] No API key set for {self.provider['name']}. Go to Settings to add your key."

        self.conversation.append({"role": "user", "content": user_message})

        try:
            if self.provider_id == "anthropic":
                return self._chat_anthropic(stream_callback)
            elif self.provider_id == "gemini":
                return self._chat_gemini(stream_callback)
            else:
                # OpenAI-compatible: openai, groq, openrouter
                return self._chat_openai_compat(stream_callback)
        except Exception as e:
            return f"[AI Error] {e}"

    def _chat_openai_compat(self, stream_callback=None) -> str:
        """OpenAI-compatible API (works for OpenAI, Groq, OpenRouter)."""
        messages = [{"role": "system", "content": SYSTEM_PROMPT}] + \
                   self.conversation[-20:]

        payload = json.dumps({
            "model": self.model,
            "messages": messages,
            "stream": False,  # streaming via urllib is complex, use non-streaming
            "max_tokens": 4096,
        }).encode()

        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.api_key}",
        }
        # OpenRouter needs extra headers
        if self.provider_id == "openrouter":
            headers["HTTP-Referer"] = "https://maxim.local"
            headers["X-Title"] = "Maxim Pentest Suite"

        req = urllib.request.Request(
            self.provider["url"],
            data=payload,
            headers=headers,
            method="POST"
        )

        with urllib.request.urlopen(req, timeout=120) as resp:
            data = json.loads(resp.read())
            assistant_msg = data["choices"][0]["message"]["content"]

        self.conversation.append({"role": "assistant", "content": assistant_msg})
        if stream_callback:
            stream_callback(assistant_msg)
        return assistant_msg

    def _chat_anthropic(self, stream_callback=None) -> str:
        """Anthropic Claude API."""
        # Claude uses a different message format — system is separate
        messages = self.conversation[-20:]

        payload = json.dumps({
            "model": self.model,
            "max_tokens": 4096,
            "system": SYSTEM_PROMPT,
            "messages": messages,
        }).encode()

        req = urllib.request.Request(
            self.provider["url"],
            data=payload,
            headers={
                "Content-Type": "application/json",
                "x-api-key": self.api_key,
                "anthropic-version": "2023-06-01",
            },
            method="POST"
        )

        with urllib.request.urlopen(req, timeout=120) as resp:
            data = json.loads(resp.read())
            # Claude returns content as array of blocks
            content_blocks = data.get("content", [])
            assistant_msg = ""
            for block in content_blocks:
                if block.get("type") == "text":
                    assistant_msg += block.get("text", "")

        self.conversation.append({"role": "assistant", "content": assistant_msg})
        if stream_callback:
            stream_callback(assistant_msg)
        return assistant_msg

    def _chat_gemini(self, stream_callback=None) -> str:
        """Google Gemini API."""
        # Convert conversation to Gemini format
        contents = []
        # System instruction as first user message
        contents.append({
            "role": "user",
            "parts": [{"text": SYSTEM_PROMPT + "\n\nAcknowledge you understand and respond to my questions."}]
        })
        contents.append({
            "role": "model",
            "parts": [{"text": "Understood. I'm Maxim AI, ready to assist with penetration testing on Kali Linux. What do you need?"}]
        })

        for msg in self.conversation[-20:]:
            role = "user" if msg["role"] == "user" else "model"
            contents.append({
                "role": role,
                "parts": [{"text": msg["content"]}]
            })

        payload = json.dumps({
            "contents": contents,
            "generationConfig": {
                "maxOutputTokens": 4096,
                "temperature": 0.7,
            }
        }).encode()

        url = self.provider["url"].replace("{model}", self.model) + f"?key={self.api_key}"

        req = urllib.request.Request(
            url,
            data=payload,
            headers={"Content-Type": "application/json"},
            method="POST"
        )

        with urllib.request.urlopen(req, timeout=120) as resp:
            data = json.loads(resp.read())
            candidates = data.get("candidates", [])
            if candidates:
                parts = candidates[0].get("content", {}).get("parts", [])
                assistant_msg = "".join(p.get("text", "") for p in parts)
            else:
                assistant_msg = "[No response from Gemini]"

        self.conversation.append({"role": "assistant", "content": assistant_msg})
        if stream_callback:
            stream_callback(assistant_msg)
        return assistant_msg

    def clear_context(self):
        self.conversation.clear()


# ═══════════════════════════════════════════════════
#  UNIFIED AI MANAGER
# ═══════════════════════════════════════════════════

class AIManager:
    """
    Manages switching between offline (Ollama) and online AI providers.
    Single interface for the GUI to use.
    """

    def __init__(self):
        self.config = load_config()
        self.ollama = OllamaAI(self.config.get("model", "mistral"))
        self.online = None
        self.active_provider = self.config.get("provider", "ollama")

        # Initialize online provider if configured
        if self.active_provider != "ollama":
            self.online = OnlineAI(
                self.active_provider,
                self.config.get("model")
            )

    @property
    def provider_name(self) -> str:
        prov = PROVIDERS.get(self.active_provider, {})
        return prov.get("name", self.active_provider)

    @property
    def is_online_mode(self) -> bool:
        return self.active_provider != "ollama"

    def is_available(self) -> bool:
        """Active provider available, OR any fallback available."""
        if self.active_provider == "ollama":
            if self.ollama.is_available():
                return True
        elif self.online and self.online.is_available():
            return True
        # Check fallbacks
        return self.is_any_available()

    def get_status(self) -> str:
        if self.active_provider == "ollama":
            if self.ollama.is_available():
                return f"Ollama: Online ({self.ollama.model})"
            return "Ollama: Offline"
        if self.online and self.online.is_available():
            return f"{self.provider_name}: {self.online.model}"
        return f"{self.provider_name}: No API key"

    def switch_provider(self, provider_id: str, model: str = None):
        """Switch to a different AI provider."""
        self.active_provider = provider_id
        if provider_id == "ollama":
            self.ollama._check_availability()
            if model:
                self.ollama.model = model
        else:
            self.online = OnlineAI(provider_id, model)

        # Save preference
        self.config["provider"] = provider_id
        if model:
            self.config["model"] = model
        save_config(self.config)

    def set_api_key(self, provider_id: str, key: str):
        set_api_key(provider_id, key)
        if self.active_provider == provider_id and self.online:
            self.online.api_key = key

    def get_models(self) -> list:
        if self.active_provider == "ollama":
            installed = self.ollama.get_installed_models()
            return installed if installed else PROVIDERS["ollama"]["models"]
        return PROVIDERS.get(self.active_provider, {}).get("models", [])

    def is_any_available(self) -> bool:
        """Check if ANY provider (active or fallback) is available."""
        if self.ollama.is_available():
            return True
        # Check all configured online providers
        for pid in PROVIDERS:
            if pid != "ollama" and get_api_key(pid):
                return True
        return False

    def _get_fallback_provider(self):
        """Find a fallback online provider with a key configured."""
        for pid in ["groq", "openrouter", "openai", "anthropic", "gemini"]:
            key = get_api_key(pid)
            if key:
                return OnlineAI(pid)
        return None

    def chat(self, user_message: str, stream_callback=None) -> str:
        """
        Send message to active AI. If it fails or is unavailable,
        automatically fall back: Ollama -> online, or online -> Ollama.
        """
        # Try active provider first
        if self.active_provider == "ollama" and self.ollama.is_available():
            result = self.ollama.chat(user_message, stream_callback)
            if not result.startswith("[AI Error]"):
                return result
            # Ollama failed — try online fallback
            fallback = self._get_fallback_provider()
            if fallback:
                if stream_callback:
                    stream_callback("\n[Falling back to online AI...]\n")
                return fallback.chat(user_message, stream_callback)
            return result

        if self.active_provider != "ollama" and self.online and self.online.is_available():
            try:
                return self.online.chat(user_message, stream_callback)
            except Exception as e:
                # Online failed — try Ollama fallback
                if self.ollama.is_available():
                    if stream_callback:
                        stream_callback("\n[Online AI failed, falling back to Ollama...]\n")
                    return self.ollama.chat(user_message, stream_callback)
                return f"[AI Error] {e}"

        # Neither active provider works — try any available
        if self.ollama.is_available():
            return self.ollama.chat(user_message, stream_callback)

        fallback = self._get_fallback_provider()
        if fallback:
            return fallback.chat(user_message, stream_callback)

        return "[Error] No AI provider available. Set up Ollama (offline) or add an API key (online) in the AI tab."

    def clear_context(self):
        self.ollama.clear_context()
        if self.online:
            self.online.clear_context()

    def set_model(self, model: str):
        if self.active_provider == "ollama":
            self.ollama.model = model
        elif self.online:
            self.online.model = model
        self.config["model"] = model
        save_config(self.config)


# ═══════════════════════════════════════════════════
#  SMART ROUTER (unchanged — works without any AI)
# ═══════════════════════════════════════════════════

class SmartRouter:
    """
    Routes natural language prompts to the right Kali tool(s).
    Works WITHOUT the LLM — pure keyword/intent matching.
    """

    INTENT_MAP = [
        (["monitor mode", "monitor", "mon0", "wlan"], "wireless_monitor",
         "Put wireless interface in monitor mode"),
        (["scan network", "scan wifi", "wifi scan", "wireless scan", "scan ap"],
         "wireless_scan", "Scan for wireless networks"),
        (["deauth", "disconnect", "kick"], "wireless_deauth",
         "Deauthentication attack"),
        (["crack wpa", "crack wifi", "handshake", "crack password wifi"],
         "wireless_crack", "Crack WiFi password"),
        (["scan port", "port scan", "open port", "nmap"], "network_scan",
         "Network/port scanning"),
        (["scan network", "discover host", "find device", "find host", "network discover", "who is on"],
         "network_discover", "Discover hosts on network"),
        (["scan vuln", "vulnerability scan", "vuln"], "vuln_scan",
         "Vulnerability scanning"),
        (["scan web", "web vuln", "website scan", "web app"], "web_scan",
         "Web application scanning"),
        (["directory", "dir scan", "brute dir", "hidden page", "hidden dir", "hidden directories", "fuzz", "find directories"],
         "web_dir", "Directory/path enumeration"),
        (["sql inject", "sqli", "sqlmap"], "sqli",
         "SQL injection testing"),
        (["exploit", "metasploit", "msfconsole", "pwn"], "exploit",
         "Exploitation framework"),
        (["reverse shell", "shell", "listener", "bind"], "reverse_shell",
         "Set up reverse/bind shell"),
        (["payload", "msfvenom", "generate"], "payload",
         "Generate payload"),
        (["crack hash", "hash", "john", "hashcat", "crack password"],
         "password_crack", "Crack password hashes"),
        (["brute force", "brute login", "hydra", "spray"], "brute_login",
         "Brute force login"),
        (["sniff", "capture packet", "pcap", "wireshark", "tcpdump"],
         "sniff", "Packet capture/sniffing"),
        (["mitm", "man in the middle", "arp spoof", "intercept"],
         "mitm", "Man-in-the-middle attack"),
        (["change mac", "mac spoof", "macchanger", "random mac"],
         "mac_change", "Change MAC address"),
        (["install", "apt install", "apt-get"], "install",
         "Install a package"),
        (["update", "apt update", "upgrade"], "update",
         "Update system packages"),
        (["start tor", "anonymize", "anonymous"], "tor",
         "Start Tor anonymization"),
        (["tunnel", "pivot", "port forward", "chisel", "ssh tunnel"],
         "tunnel", "Set up tunneling/pivoting"),
        (["check ip", "my ip", "ifconfig", "ip addr"], "check_ip",
         "Check network interfaces/IP"),
        (["service", "start service", "stop service", "restart"],
         "service", "Manage system services"),
    ]

    ACTION_TOOLS = {
        "wireless_monitor": ["aircrack-ng"],
        "wireless_scan": ["aircrack-ng", "wifite", "bettercap"],
        "wireless_deauth": ["aircrack-ng", "bettercap"],
        "wireless_crack": ["aircrack-ng", "wifite", "fern-wifi-cracker"],
        "network_scan": ["nmap", "masscan"],
        "network_discover": ["nmap", "netdiscover"],
        "vuln_scan": ["nmap", "openvas", "nikto", "lynis"],
        "web_scan": ["nikto", "burpsuite", "whatweb"],
        "web_dir": ["gobuster", "dirb", "ffuf"],
        "sqli": ["sqlmap"],
        "exploit": ["metasploit", "searchsploit"],
        "reverse_shell": ["netcat", "socat", "metasploit"],
        "payload": ["metasploit"],
        "password_crack": ["john", "hashcat"],
        "brute_login": ["hydra", "medusa", "crackmapexec"],
        "sniff": ["wireshark", "tcpdump"],
        "mitm": ["ettercap", "bettercap", "responder"],
        "mac_change": ["macchanger"],
        "install": [],
        "update": [],
        "tor": ["tor", "proxychains"],
        "tunnel": ["chisel", "ssh", "socat"],
        "check_ip": [],
        "service": [],
    }

    @classmethod
    def route(cls, query: str) -> dict:
        q = query.lower().strip()

        if q.startswith("install "):
            pkg = query.split("install ", 1)[1].strip()
            return {
                "intent": "install",
                "description": f"Install package: {pkg}",
                "tools": [],
                "needs_choice": False,
                "direct_command": f"sudo apt-get install -y {pkg}",
            }

        if q in ("update", "apt update", "update system"):
            return {
                "intent": "update",
                "description": "Update package repositories",
                "tools": [],
                "needs_choice": False,
                "direct_command": "sudo apt-get update && sudo apt-get upgrade -y",
            }

        if q.startswith(("ifconfig", "ip a", "ip addr", "check ip", "my ip")):
            return {
                "intent": "check_ip",
                "description": "Check network interfaces",
                "tools": [],
                "needs_choice": False,
                "direct_command": "ip -c addr show",
            }

        if q.startswith(("start ", "stop ", "restart ", "status ")):
            parts = q.split()
            action = parts[0]
            svc = parts[1] if len(parts) > 1 else ""
            # Don't catch "start tor" — let intent matching handle known tools
            if svc not in ("tor", "metasploit", "msfconsole", "burpsuite", "wireshark"):
                return {
                    "intent": "service",
                    "description": f"{action.title()} service: {svc}",
                    "tools": [],
                    "needs_choice": False,
                    "direct_command": f"sudo systemctl {action} {svc}",
                }

        best_match = None
        best_score = 0
        for keywords, action, desc in cls.INTENT_MAP:
            score = sum(1 for kw in keywords if kw in q)
            if score > best_score:
                best_score = score
                best_match = (action, desc)

        if best_match and best_score > 0:
            action, desc = best_match
            tool_names = cls.ACTION_TOOLS.get(action, [])
            tools = [get_tool_by_name(n) for n in tool_names if get_tool_by_name(n)]
            return {
                "intent": action,
                "description": desc,
                "tools": tools,
                "needs_choice": len(tools) > 1,
                "direct_command": None,
            }

        matched = find_tools_by_keywords(query, top_n=3)
        if matched:
            return {
                "intent": "general",
                "description": f"Tools matching: {query}",
                "tools": matched,
                "needs_choice": len(matched) > 1,
                "direct_command": None,
            }

        return {
            "intent": "unknown",
            "description": "No matching tool found",
            "tools": [],
            "needs_choice": False,
            "direct_command": None,
        }
