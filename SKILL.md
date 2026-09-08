---
name: nsr
description: Continue a bounded execution task when the user explicitly invokes /nsr, $nsr, or Non-Stop-Run. Work in the current task and model with clear success criteria, progress checks, and stop conditions; no marker, hook installation, or extra commit gate is required.
---

# NSR

NSR is an explicitly requested continuation style within the current task. Reuse its brief, workspace, model, evidence, and existing authorization. It does not create a second controller, memory record, task state, or model role.

## Continue useful work

1. Use the remaining request as the objective, preserving the current task’s scope and accepted decisions.
2. State or reuse concrete success criteria, a bounded time/step budget, and meaningful validation.
3. Work in useful implementation slices; inspect actual results before deciding the next slice. Resolve discoverable questions without repeatedly asking the user to continue.
4. Report progress and real blockers in the existing task. Preserve failures and residuals; a reached budget is not completion.

## Stop conditions and real protections

Stop promptly when the user asks. Also stop or return a truthful partial result when the objective is validated, the agreed budget is reached, repeated attempts show no meaningful progress, or a decision outside existing authorization prevents further work. Continue independent authorized work when possible.

Do not bypass safety or actual permission requirements. Preserve unrelated dirty work; use the task-owned workspace or an isolated worktree rather than overwriting another session’s files. High-risk or irreversible actions retain their real authorization boundary. Failed validation must not be reported as a pass.

## Host boundary

The current agent carries out this bounded loop. Do not enable a repo marker, install or depend on a Stop hook, send a reload action, or run a separate `nsr-commit-gate` as an incidental NSR step. Use the repository’s actual commit identity and applicable checks; NSR adds no commit gate.

Historical markers and explicitly invoked legacy CLI tools are not modified by this skill. Their existence does not reactivate them or authorize unattended continuation. A paused/stopped task stays under user control.

The [previous entry](references/history/pre-stride-hook-hygiene-20260908.md) is archived for traceability and does not define the current execution protocol.
