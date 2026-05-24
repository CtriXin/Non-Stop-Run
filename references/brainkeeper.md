# NSR Brainkeeper Bridge

Brainkeeper is a checkpoint bridge, not a NSR profile slot.

NSR owns the active run:

- goal, slice, event, milestone, validation, debugger result, recovery, and commit gate

Brainkeeper owns long-term recovery:

- compact checkpoint threads written through `brain_checkpoint`

## Export

Use:

```bash
python3 /Users/xin/auto-skills/Non-Stop-Run/scripts/controller.py brainkeeper-export \
  --project-root /path/to/repo \
  --write \
  --reason "Phase shipped"
```

The command writes:

```text
<nsr-session>/brainkeeper-checkpoint.json
```

The JSON shape is ready for the Brainkeeper MCP tool:

```json
{
  "tool": "brain_checkpoint",
  "arguments": {
    "repo": "/path/to/repo",
    "task": "current objective",
    "status": "one sentence status",
    "branch": "current-branch",
    "cli": "codex",
    "decisions": [],
    "changes": [],
    "findings": [],
    "next": []
  }
}
```

## Write Policy

Do not automatically call Brainkeeper for every NSR event.

Good export moments:

- milestone completed
- `PreCompact` before context compression
- `exit-summary`
- user asks for checkpoint / distill
- a long run hands off to another agent

Bad export moments:

- every tool call
- raw diff snapshots
- speculative bug candidates
- failed validation noise
- unscoped learning that may conflict across projects

## Boundary

Use `brainkeeper-export` to prepare the payload. The host agent may then call `brainkeeper.brain_checkpoint` when the MCP tool is available.

If the MCP tool is unavailable, keep the exported JSON file as a durable local checkpoint and mention the fallback path.

Maintenance note: added by `web agent` (`Role: coordinator`) on 2026-05-08.
