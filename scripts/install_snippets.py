#!/usr/bin/env python3
import argparse
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parent
CLAUDE_HOOK = ROOT / "claude_hook.py"
CODEX_HOOK = ROOT / "codex_hook.py"
CODEX_EVENTS = {
    "SessionStart": "Loading Looop context",
    "UserPromptSubmit": "Loading Looop context",
    "PermissionRequest": "Recording Looop permission gate",
    "PreToolUse": "Recording Looop tool activity",
    "PostToolUse": "Recording Looop tool activity",
    "PreCompact": "Recording Looop compact checkpoint",
    "PostCompact": "Recording Looop compact checkpoint",
    "Stop": "Checking Looop stop guard",
}
CODEX_MATCHERS = {
    "SessionStart": "startup|resume|clear",
    "PermissionRequest": "*",
    "PreToolUse": "*",
    "PostToolUse": "*",
}
CLAUDE_MATCHERS = {
    "SessionStart": "startup|resume|clear|compact",
    "PermissionRequest": "*",
    "PreToolUse": "*",
    "PostToolUse": "*",
}


def claude_snippet() -> dict:
    command = f"python3 {CLAUDE_HOOK}"
    hook = {"type": "command", "command": command}
    events = [
        "SessionStart",
        "UserPromptSubmit",
        "PermissionRequest",
        "PreToolUse",
        "PostToolUse",
        "PreCompact",
        "PostCompact",
        "Stop",
    ]
    hooks = {}
    for event_name in events:
        hooks[event_name] = [
            {
                "matcher": CLAUDE_MATCHERS.get(event_name, ""),
                "hooks": [hook],
            }
        ]
    return {"hooks": hooks}


def codex_snippet() -> dict:
    command = f"python3 {CODEX_HOOK}"
    hooks = {}
    for event_name, status_message in CODEX_EVENTS.items():
        entry = {
            "hooks": [
                {
                    "type": "command",
                    "command": command,
                    "timeout": 10,
                    "statusMessage": status_message,
                }
            ]
        }
        if event_name in CODEX_MATCHERS:
            entry["matcher"] = CODEX_MATCHERS[event_name]
        hooks[event_name] = [entry]
    return {
        "note": "Enable Codex hooks with --enable hooks or [features].hooks = true. Do not also load old LongRun hooks unless intentionally running that backend.",
        "features": {"hooks": True},
        "command": command,
        "events": list(CODEX_EVENTS),
        "hooks": hooks,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Print Looop hook config snippets.")
    parser.add_argument("--host", choices=["claude", "codex", "all"], default="all")
    args = parser.parse_args()

    data = {}
    if args.host in {"claude", "all"}:
        data["claude"] = claude_snippet()
    if args.host in {"codex", "all"}:
        data["codex"] = codex_snippet()
    print(json.dumps(data, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
