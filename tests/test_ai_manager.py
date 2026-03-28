"""
Test AI Manager — provider switching, config, fallback logic.
"""

import sys
import os
import json
import tempfile
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from maxim.core.ai_assistant import (
    AIManager, OnlineAI, PROVIDERS, load_config, save_config,
    get_api_key, set_api_key, CONFIG_FILE
)

PASS = 0
FAIL = 0


def check(name, condition, detail=""):
    global PASS, FAIL
    if condition:
        PASS += 1
        print(f"  PASS  {name}")
    else:
        FAIL += 1
        print(f"  FAIL  {name}" + (f" -- {detail}" if detail else ""))


def test_providers_defined():
    print("\n=== Provider Definitions ===")
    required = ["ollama", "openai", "anthropic", "gemini", "groq", "openrouter"]
    for pid in required:
        p = PROVIDERS.get(pid)
        check(f"Provider '{pid}' exists", p is not None)
        if p:
            check(f"  has name", bool(p.get("name")))
            check(f"  has models", bool(p.get("models")))
            check(f"  has description", bool(p.get("description")))
            if p["type"] == "online":
                check(f"  has url", bool(p.get("url")))
                check(f"  has key_env", bool(p.get("key_env")))
                check(f"  has key_url", bool(p.get("key_url")))


def test_ai_manager_init():
    print("\n=== AIManager Initialization ===")
    mgr = AIManager()
    check("Active provider is valid", mgr.active_provider in PROVIDERS)
    check("Has ollama instance", mgr.ollama is not None)
    check("get_status returns string", isinstance(mgr.get_status(), str))
    check("get_models returns list", isinstance(mgr.get_models(), list))


def test_provider_switching():
    print("\n=== Provider Switching ===")
    mgr = AIManager()

    mgr.switch_provider("openai", "gpt-4o")
    check("Switch to openai", mgr.active_provider == "openai")
    check("Online mode", mgr.is_online_mode)
    check("Online instance created", mgr.online is not None)
    check("Model set", mgr.online.model == "gpt-4o")

    mgr.switch_provider("anthropic", "claude-sonnet-4-6")
    check("Switch to anthropic", mgr.active_provider == "anthropic")
    check("Anthropic model", mgr.online.model == "claude-sonnet-4-6")

    mgr.switch_provider("ollama")
    check("Switch back to ollama", mgr.active_provider == "ollama")
    check("Not online mode", not mgr.is_online_mode)


def test_online_ai_no_key():
    print("\n=== OnlineAI Without Key ===")
    ai = OnlineAI("openai")
    ai.api_key = ""
    check("Not available without key", not ai.is_available())
    result = ai.chat("test")
    check("Error message without key", "[Error]" in result)


def test_online_ai_with_key():
    print("\n=== OnlineAI With Key (mock) ===")
    ai = OnlineAI("openai")
    ai.api_key = "sk-test-fake-key"
    check("Available with key", ai.is_available())
    check("Has models", len(ai.get_models()) > 0)


def test_config_persistence():
    print("\n=== Config Persistence ===")
    # Save a test key
    set_api_key("test_provider", "test_key_12345")
    key = get_api_key("test_provider")
    check("Key saved and retrieved", key == "test_key_12345")

    # Clean up
    config = load_config()
    config.get("keys", {}).pop("test_provider", None)
    save_config(config)


def test_model_lists():
    print("\n=== Model Lists ===")
    for pid, prov in PROVIDERS.items():
        models = prov.get("models", [])
        check(f"{prov['name']} has models ({len(models)})", len(models) > 0)


def test_provider_name():
    print("\n=== Provider Names ===")
    mgr = AIManager()
    check("Ollama name", "Ollama" in mgr.provider_name)
    mgr.switch_provider("openai")
    check("OpenAI name", "OpenAI" in mgr.provider_name)
    mgr.switch_provider("anthropic")
    check("Claude name", "Claude" in mgr.provider_name)


def test_clear_context():
    print("\n=== Clear Context ===")
    mgr = AIManager()
    # Ensure ollama is initialized for this test
    if mgr.ollama is None:
        mgr.switch_provider("ollama")
    mgr.ollama.conversation.append({"role": "user", "content": "test"})
    mgr.clear_context()
    check("Ollama context cleared", len(mgr.ollama.conversation) == 0)


if __name__ == "__main__":
    print("=" * 60)
    print("  MAXIM — AI Manager Test Suite")
    print("=" * 60)

    test_providers_defined()
    test_ai_manager_init()
    test_provider_switching()
    test_online_ai_no_key()
    test_online_ai_with_key()
    test_config_persistence()
    test_model_lists()
    test_provider_name()
    test_clear_context()

    print("\n" + "=" * 60)
    total = PASS + FAIL
    print(f"  Results: {PASS}/{total} passed, {FAIL} failed")
    if FAIL == 0:
        print("  ALL TESTS PASSED")
    print("=" * 60)

    sys.exit(0 if FAIL == 0 else 1)
