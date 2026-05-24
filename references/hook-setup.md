# Hook Setup

NSR ships separate adapters for Codex and Claude. Both read JSON on stdin and return structured JSON on stdout.

## Codex

Use:

```bash
python3 /Users/xin/auto-skills/Non-Stop-Run/scripts/codex_hook.py
```

Enable Codex hooks with `--enable hooks` or `[features].hooks = true` in `config.toml`; the old `[features].codex_hooks` flag is deprecated.

For Codex-level long-running objective continuity, NSR replaces generic LLR. Keep only the NSR hook in the Codex hook surface by default:

- Remove Codex-visible `longrun-bridge` skill entries unless you intentionally need to route to an old LongRun backend.
- Remove the Moebius `longrun_hook.py` from global Codex hooks unless a specific Moebius run still needs run-local LongRun auto-injection.
- Using Moebius itself does not require the global Moebius LongRun hook; that hook only provides automatic LongRun context/stop behavior for active Moebius run state.

Supported events:

- `SessionStart`: injects NSR context on startup/resume/clear.
- `UserPromptSubmit`: injects NSR context.
- `Stop`: blocks premature stop while an active loop has a contract-covered next action.
- `PreCompact` / `PostCompact`: records compact checkpoint events.
- `PermissionRequest`: records approval gates without changing the allow/deny decision.
- `PreToolUse` / `PostToolUse`: records tool/file activity for traceability and ownership hints.
- Reference checked on 2026-05-08: local `codex-cli 0.129.0` plus https://github.com/openai/codex/tree/main/codex-rs/hooks/schema/generated.

Print a config/helper snippet:

```bash
python3 /Users/xin/auto-skills/Non-Stop-Run/scripts/install_snippets.py --host codex
```

## Claude Code

Use:

```bash
python3 /Users/xin/auto-skills/Non-Stop-Run/scripts/claude_hook.py
```

Claude settings example:

```json
{
  "hooks": {
    "SessionStart": [
      {
        "matcher": "startup|resume|clear|compact",
        "hooks": [
          {
            "type": "command",
            "command": "python3 /Users/xin/auto-skills/Non-Stop-Run/scripts/claude_hook.py"
          }
        ]
      }
    ],
    "UserPromptSubmit": [
      {
        "matcher": "",
        "hooks": [
          {
            "type": "command",
            "command": "python3 /Users/xin/auto-skills/Non-Stop-Run/scripts/claude_hook.py"
          }
        ]
      }
    ],
    "PermissionRequest": [
      {
        "matcher": "*",
        "hooks": [
          {
            "type": "command",
            "command": "python3 /Users/xin/auto-skills/Non-Stop-Run/scripts/claude_hook.py"
          }
        ]
      }
    ],
    "PreToolUse": [
      {
        "matcher": "*",
        "hooks": [
          {
            "type": "command",
            "command": "python3 /Users/xin/auto-skills/Non-Stop-Run/scripts/claude_hook.py"
          }
        ]
      }
    ],
    "PostToolUse": [
      {
        "matcher": "*",
        "hooks": [
          {
            "type": "command",
            "command": "python3 /Users/xin/auto-skills/Non-Stop-Run/scripts/claude_hook.py"
          }
        ]
      }
    ],
    "PreCompact": [
      {
        "matcher": "",
        "hooks": [
          {
            "type": "command",
            "command": "python3 /Users/xin/auto-skills/Non-Stop-Run/scripts/claude_hook.py"
          }
        ]
      }
    ],
    "PostCompact": [
      {
        "matcher": "",
        "hooks": [
          {
            "type": "command",
            "command": "python3 /Users/xin/auto-skills/Non-Stop-Run/scripts/claude_hook.py"
          }
        ]
      }
    ],
    "Stop": [
      {
        "matcher": "",
        "hooks": [
          {
            "type": "command",
            "command": "python3 /Users/xin/auto-skills/Non-Stop-Run/scripts/claude_hook.py"
          }
        ]
      }
    ]
  }
}
```

Print the same snippet:

```bash
python3 /Users/xin/auto-skills/Non-Stop-Run/scripts/install_snippets.py --host claude
```

Claude hook notes:

- `UserPromptSubmit` supports `hookSpecificOutput.additionalContext`.
- `SessionStart` also supports `hookSpecificOutput.additionalContext`.
- `Stop` supports top-level `decision: "block"` with `reason`.
- `PermissionRequest` is logged only; NSR intentionally does not auto-allow or auto-deny permissions.
- Plain stdout may also be injected for prompt hooks, but NSR uses structured JSON for predictability.
- Reference checked on 2026-05-08: https://code.claude.com/docs/en/hooks

Do not enable both old LLR and NSR stop guards for the same session unless you intentionally want both gates.

Maintenance note: `web agent` (`Role: coordinator`) switched the local Codex hook entry from legacy `long-long-run` to `nsr` on 2026-05-08. The legacy implementation directory and historical sessions were intentionally preserved; only the old Codex skill symlink should be removed during migration.
