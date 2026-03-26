"""
Test Workflows — ensures all phases, steps, and commands are well-formed.
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from maxim.core.workflows import PHASES, ONLINE_RESOURCES, NATURAL_COMMANDS, get_phase

PASS = 0
FAIL = 0


def test_phases_structure():
    print("\n=== Phase Structure ===")
    global PASS, FAIL

    required_keys = ["id", "name", "icon", "color", "description", "steps"]
    for phase in PHASES:
        issues = []
        for key in required_keys:
            if key not in phase:
                issues.append(f"missing '{key}'")
        if not phase.get("steps"):
            issues.append("no steps")

        if issues:
            FAIL += 1
            print(f"  FAIL  {phase.get('name', '???')} -- {', '.join(issues)}")
        else:
            PASS += 1
            print(f"  PASS  {phase['name']} ({len(phase['steps'])} steps)")


def test_steps_structure():
    print("\n=== Step Structure ===")
    global PASS, FAIL

    for phase in PHASES:
        for i, step in enumerate(phase["steps"]):
            issues = []
            if not step.get("name"):
                issues.append("missing name")
            if not step.get("description"):
                issues.append("missing description")
            if not step.get("suggestions"):
                issues.append("no suggestions")
            if "online_tools" not in step:
                issues.append("missing online_tools key")

            if issues:
                FAIL += 1
                print(f"  FAIL  {phase['name']} > Step {i+1}: {step.get('name', '???')} -- {', '.join(issues)}")
            else:
                n_cmds = len(step["suggestions"])
                n_online = len(step.get("online_tools", []))
                PASS += 1
                print(f"  PASS  {phase['name']} > {step['name']} ({n_cmds} cmds, {n_online} online)")


def test_suggestions_format():
    print("\n=== Suggestion Format ===")
    global PASS, FAIL

    total = 0
    bad = 0
    for phase in PHASES:
        for step in phase["steps"]:
            for sug in step["suggestions"]:
                total += 1
                issues = []
                if not sug.get("tool"):
                    issues.append("missing tool")
                if not sug.get("cmd"):
                    issues.append("missing cmd")
                if not sug.get("desc"):
                    issues.append("missing desc")
                if issues:
                    bad += 1
                    FAIL += 1
                    print(f"  FAIL  {phase['name']} > {step['name']} > {sug} -- {', '.join(issues)}")

    good = total - bad
    PASS += 1 if bad == 0 else 0
    print(f"  {'PASS' if bad == 0 else 'FAIL'}  {good}/{total} suggestions well-formed")


def test_online_tools_format():
    print("\n=== Online Tools Format ===")
    global PASS, FAIL

    total = 0
    bad = 0
    for phase in PHASES:
        for step in phase["steps"]:
            for ot in step.get("online_tools", []):
                total += 1
                issues = []
                if not ot.get("name"):
                    issues.append("missing name")
                if not ot.get("url"):
                    issues.append("missing url")
                if not ot.get("desc"):
                    issues.append("missing desc")
                if issues:
                    bad += 1
                    FAIL += 1
                    print(f"  FAIL  online tool: {ot} -- {', '.join(issues)}")

    good = total - bad
    PASS += 1 if bad == 0 else 0
    print(f"  {'PASS' if bad == 0 else 'FAIL'}  {good}/{total} online tools well-formed")


def test_online_resources():
    print("\n=== Online Resources ===")
    global PASS, FAIL

    for r in ONLINE_RESOURCES:
        issues = []
        if not r.get("name"):
            issues.append("missing name")
        if not r.get("url"):
            issues.append("missing url")
        if not r.get("desc"):
            issues.append("missing desc")
        if not r.get("category"):
            issues.append("missing category")

        if issues:
            FAIL += 1
            print(f"  FAIL  {r.get('name', '???')} -- {', '.join(issues)}")
        else:
            PASS += 1
            print(f"  PASS  {r['name']} [{r['category']}]")


def test_natural_commands():
    print("\n=== Natural Commands ===")
    global PASS, FAIL

    for phrase, (tool, cmd, desc) in NATURAL_COMMANDS.items():
        issues = []
        if not tool:
            issues.append("no tool")
        if not cmd:
            issues.append("no command")
        if not desc:
            issues.append("no description")

        if issues:
            FAIL += 1
            print(f"  FAIL  '{phrase}' -- {', '.join(issues)}")
        else:
            PASS += 1
            print(f"  PASS  '{phrase}' -> {tool}")


def test_get_phase():
    print("\n=== get_phase() ===")
    global PASS, FAIL

    for phase in PHASES:
        result = get_phase(phase["id"])
        if result and result["name"] == phase["name"]:
            PASS += 1
            print(f"  PASS  get_phase('{phase['id']}') -> {phase['name']}")
        else:
            FAIL += 1
            print(f"  FAIL  get_phase('{phase['id']}') returned wrong result")

    # Non-existent
    if get_phase("nonexistent") is None:
        PASS += 1
        print(f"  PASS  get_phase('nonexistent') -> None")
    else:
        FAIL += 1
        print(f"  FAIL  get_phase('nonexistent') should return None")


def test_totals():
    print("\n=== Totals ===")
    total_cmds = sum(
        len(s["suggestions"]) for p in PHASES for s in p["steps"]
    )
    total_online = sum(
        len(s.get("online_tools", [])) for p in PHASES for s in p["steps"]
    )
    total_steps = sum(len(p["steps"]) for p in PHASES)
    print(f"  {len(PHASES)} phases, {total_steps} steps, {total_cmds} CLI commands, {total_online} online tools")
    print(f"  {len(NATURAL_COMMANDS)} natural command mappings")
    print(f"  {len(ONLINE_RESOURCES)} online resources")


if __name__ == "__main__":
    print("=" * 60)
    print("  MAXIM — Workflow & Content Test Suite")
    print("=" * 60)

    test_phases_structure()
    test_steps_structure()
    test_suggestions_format()
    test_online_tools_format()
    test_online_resources()
    test_natural_commands()
    test_get_phase()
    test_totals()

    print("\n" + "=" * 60)
    total = PASS + FAIL
    print(f"  Results: {PASS}/{total} passed, {FAIL} failed")
    if FAIL == 0:
        print("  ALL TESTS PASSED")
    print("=" * 60)

    sys.exit(0 if FAIL == 0 else 1)
