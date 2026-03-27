#!/usr/bin/env python3
"""Test Groq API connectivity."""
import json
import urllib.request
import urllib.error
import sys

# Read key from config or command line
key = sys.argv[1] if len(sys.argv) > 1 else None
if not key:
    try:
        import os
        cfg = json.loads(open(os.path.expanduser("~/.maxim/ai_config.json")).read())
        key = cfg.get("keys", {}).get("groq", "")
    except:
        pass
if not key:
    # Try built-in
    from maxim.core.ai_assistant import BUILTIN_GROQ_KEY
    key = BUILTIN_GROQ_KEY

if not key:
    print("No Groq API key found. Pass it as argument: python3 test_groq.py YOUR_KEY")
    sys.exit(1)

print(f"Using key: {key[:10]}...{key[-4:]}")
print("Calling Groq API...")

payload = json.dumps({
    "model": "llama-3.1-8b-instant",
    "messages": [{"role": "user", "content": "say hello"}],
}).encode()

req = urllib.request.Request(
    "https://api.groq.com/openai/v1/chat/completions",
    data=payload,
    headers={
        "Content-Type": "application/json",
        "Authorization": f"Bearer {key}",
        "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36",
        "Accept": "application/json",
    },
    method="POST"
)

try:
    with urllib.request.urlopen(req, timeout=30) as resp:
        data = json.loads(resp.read())
        msg = data["choices"][0]["message"]["content"]
        print(f"SUCCESS! AI says: {msg}")
except urllib.error.HTTPError as e:
    body = e.read().decode("utf-8", errors="replace")
    print(f"HTTP ERROR {e.code}: {body[:500]}")
except Exception as e:
    print(f"ERROR: {e}")
