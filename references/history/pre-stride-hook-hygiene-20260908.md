---
name: nsr
description: Use when the user invokes /nsr, $nsr, Non-Stop-Run, or asks the agent to keep working until done with explicit brakes.
---

# NSR

NSR is a bounded "keep going" mode. It is not permission to ignore safety,
dirty worktrees, or high-risk choices. It means: define the objective, set
brakes, work in slices, validate, and stop only when done or blocked.

## Activation

When the user invokes `$nsr`, `/nsr`, or asks for Non-Stop-Run behavior:

1. Treat the remaining user text as the objective.
2. State success criteria and the brakes you will use.
3. Enable the local marker when the helper exists:

```bash
python3 "$HOME/.mms/hooks/nsrctl.py" enable "$PWD"
```

4. Continue in bounded implementation slices until one stop condition is met.

## Stop Conditions

Stop and report when any condition is true:

- Success criteria are met and validation passes.
- `LOOP_MAX_STEPS` or the chosen continuation limit is reached.
- `LOOP_MAX_NO_CHANGE` or repeated no-diff/no-progress detection trips.
- The validation command stays red after the retry limit.
- A high-risk or irreversible human decision is required.
- The worktree has unrelated dirty changes that would be unsafe to touch.

## Host Notes

- Claude and Codex can use the MMS Stop-hook wrapper when it is injected.
- OpenCode does not expose the same Stop-hook `decision=block` protocol; use
  NSR there as a manual loop contract.
- Before any agent-created commit, run the commit gate when available:

```bash
python3 "$HOME/.mms/hooks/nsr-commit-gate.py" --repo "$PWD"
```

If the gate blocks, do not commit. Explain the blocked paths and ask if needed.
