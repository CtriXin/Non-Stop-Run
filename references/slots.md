# NSR Slots

NSR slots are domain profiles, not separate runtimes.

The runtime owns:

- state, events, milestones, validation records, recovery, hooks, and commit gates

The slot owns:

- candidate selection, domain-specific hard gates, evidence rules, and stop thresholds

## Registered Slots

`bugloop` is registered for critical bug hunts.

- aliases: `bugloop`, `nightly-fix`, `nightly debug`, `nightly bug hunt`
- owner skill: `/Users/xin/auto-skills/shared-skills/bugloop/SKILL.md`
- target phase: `nightly-fix`
- default max iterations: `12`
- run log hint: `.ai/critical-debug/YYYY-MM-DD-nightly.md`

`audit` is registered for review-gate and audit work.

- aliases: `audit`, `code-audit`, `review-gate`, `audit gate`, `safety audit`, `multi-review`
- owner skill: `/Users/xin/auto-skills/shared-skills/multi-review/SKILL.md`
- target phase: `audit-gate`
- default execution mode: `companion`
- default commit policy: `manual`
- default max iterations: `8`
- run log hint: `.ai/reviews/log/gate-<milestone>.json`

Use:

```bash
python3 /Users/xin/auto-skills/Non-Stop-Run/scripts/controller.py start \
  --project-root /path/to/repo \
  --slot nightly-fix \
  --objective "Run a critical bug hunt" \
  --owner-agent "web agent" \
  --role "coordinator"
```

```bash
python3 /Users/xin/auto-skills/Non-Stop-Run/scripts/controller.py start \
  --project-root /path/to/repo \
  --slot audit \
  --objective "Audit the requested milestone" \
  --owner-agent "web agent" \
  --role "coordinator"
```

## Naming

Use `nightly-fix`, not `nighty_fix`.

`nightly-fix` is an alias for the `bugloop` slot. Do not create a third skill for it.

`audit` routes to the `multi-review` skill rules. Do not create a second runtime for review-gate state.

## Completion Gate Pairing

Slots choose domain behavior. Completion gates enforce closure.

Use `--completion-gate audit` when a normal NSR objective, such as `p100-p110`,
must not close until independent review evidence exists. Use `--slot audit` when
the whole objective is the audit itself. The `audit` slot automatically requires
the audit completion gate.

## Slot Boundary

Slots may set default target phase, done condition, iteration cap, and safety notes. They must not duplicate `.nsr` state or create a second stop guard.

If a profile needs long-term memory, export only milestone-grade summaries into Brainkeeper. Do not store raw tool calls, full diffs, or unvalidated candidate theories as long-term memory.

Maintenance note: added by `web agent` (`Role: coordinator`) on 2026-05-08 when `bugloop` became a NSR profile slot.
