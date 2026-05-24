---
name: nsr
description: Use when the user wants a goal-driven agent execution loop that should keep moving without repeated confirmation, run until a named phase or milestone, preserve traceable events/milestones, survive compaction/429/interruption, and auto-commit only safe self-owned validated slices. Supports Codex and Claude hook contexts.
metadata:
  short-description: "NSR: goal-driven execution, milestones, recovery, safe commits"
  version: "0.8.3"
---

# NSR

NSR 是目标驱动的 execution loop。它不是聊天记忆，也不是项目管理系统。

用它处理这类请求：

- 用户希望 agent 不要频繁停下来问，而是自己选最佳路径继续推进。
- 用户指定要做到某个阶段、milestone、验证结果或 release gate。
- 工作可能跨很多 turn、会被 compaction/429/中断影响。
- 每一小段完成后需要可追踪记录：events、milestone、validation、commit 或 patch snapshot。
- 需要 Codex / Claude hook 在下一轮 prompt 和 stop 阶段提醒 agent 继续主线。

## Core Contract

默认策略：

1. 先回应用户最新消息。
2. 如果用户没有改变目标或叫停，继续当前 goal。
3. 每轮只做一个 bounded slice。
4. slice 后必须验证；验证失败不 commit。
5. 运行 debugger pass：具体漏洞、失败场景、严重级别、修复、残余不确定性。
6. 能安全归因给当前 agent 的改动才 auto-commit。
7. 不能 commit 时必须写 milestone / event / patch path，让后续 agent 找得到家。
8. 每轮结束记录 `iteration-result`，把 summary、changes、learnings、stop 判断写入 `notes.md`。
9. 遇到能提升真实 loop 的外部知识、竞品做法或运行教训，用 `learn` 记录证据；多次命中后再升级长期规则。

只有这些情况才问用户：

- 全局配置、账单、权限、外部账号、不可逆删除、force push、生产发布。
- 目标本身冲突，无法靠项目证据判断。
- 用户明确要求暂停或选择。

## Quick Start

```bash
python3 /Users/xin/auto-skills/Non-Stop-Run/scripts/controller.py start \
  --project-root /path/to/repo \
  --objective "Ship the requested feature" \
  --target-phase "Phase D" \
  --owner-agent "web agent" \
  --role "coordinator" \
  --execution-mode companion
```

常用命令：

```bash
# 查看当前 NSR 版本
python3 /Users/xin/auto-skills/Non-Stop-Run/scripts/controller.py version

# 查看可用 profile slots
python3 /Users/xin/auto-skills/Non-Stop-Run/scripts/controller.py slots
python3 /Users/xin/auto-skills/Non-Stop-Run/scripts/controller.py slot-info --name nightly-fix

# 查看当前 session
python3 /Users/xin/auto-skills/Non-Stop-Run/scripts/controller.py current --project-root /path/to/repo

# 导出 Brainkeeper checkpoint payload；默认只生成，不自动写长期记忆
python3 /Users/xin/auto-skills/Non-Stop-Run/scripts/controller.py brainkeeper-export \
  --project-root /path/to/repo \
  --write \
  --reason "Phase shipped"

# 按 profile slot 启动，例如 bugloop / nightly-fix / audit
python3 /Users/xin/auto-skills/Non-Stop-Run/scripts/controller.py start \
  --project-root /path/to/repo \
  --slot nightly-fix \
  --objective "Run a critical bug hunt" \
  --owner-agent "web agent" \
  --role "coordinator"

# 启动 audit/review gate profile
python3 /Users/xin/auto-skills/Non-Stop-Run/scripts/controller.py start \
  --project-root /path/to/repo \
  --slot audit \
  --completion-gate audit \
  --gate-scope p100-p110 \
  --objective "Audit the requested milestone" \
  --owner-agent "web agent" \
  --role "coordinator"

# 记录并检查强制 audit completion gate
python3 /Users/xin/auto-skills/Non-Stop-Run/scripts/controller.py audit-gate \
  --scope p100-p110 \
  --verdict pass \
  --reviewers 3 \
  --p0-blockers 0 \
  --p1-blockers 0 \
  --validation pass \
  --evidence .ai/reviews/log/gate-p100-p110.json \
  --residual-risk "Only low-risk gaps remain"

python3 /Users/xin/auto-skills/Non-Stop-Run/scripts/controller.py completion-check

# 启动 continuity/offduty profile
python3 /Users/xin/auto-skills/Non-Stop-Run/scripts/controller.py start \
  --project-root /path/to/repo \
  --slot continuity \
  --objective "Write a shift-boundary continuation checkpoint" \
  --owner-agent "web agent" \
  --role "coordinator"

# 开始一轮 slice
python3 /Users/xin/auto-skills/Non-Stop-Run/scripts/controller.py begin-slice --summary "Implement search settings"

# 记录事件
python3 /Users/xin/auto-skills/Non-Stop-Run/scripts/controller.py event --kind validation --summary "npm test passed"

# 运行并记录验证命令
python3 /Users/xin/auto-skills/Non-Stop-Run/scripts/controller.py validate --command "npm test"

# 写 milestone
python3 /Users/xin/auto-skills/Non-Stop-Run/scripts/controller.py milestone --summary "Search settings shipped" --validation "npm test passed" --next-action "Manual browser smoke"

# 中断/429/压缩后恢复
python3 /Users/xin/auto-skills/Non-Stop-Run/scripts/controller.py recover

# 生成 NSR goal contract，或给 Codex /goal 使用的 prompt
python3 /Users/xin/auto-skills/Non-Stop-Run/scripts/controller.py goal-contract --write
python3 /Users/xin/auto-skills/Non-Stop-Run/scripts/controller.py goal-prompt

# 记录一轮结果，沉淀 notes.md
python3 /Users/xin/auto-skills/Non-Stop-Run/scripts/controller.py iteration-result \
  --success \
  --summary "Implemented and verified the bounded slice" \
  --key-change "Added traceable iteration notes" \
  --key-learning "No-op slices must stop instead of spinning"

# 记录可复用学习，供真实 loop 场景复盘和后续沉淀
python3 /Users/xin/auto-skills/Non-Stop-Run/scripts/controller.py learn \
  --source "project postmortem or external reference" \
  --summary "Small verified slices reduce recovery cost" \
  --evidence "Observed in run notes and validation logs" \
  --scope repo \
  --conflicts-with "Provider-specific projects may require larger atomic slices" \
  --tag loop \
  --lesson-type candidate \
  --priority P2 \
  --promote-candidate

# 安全 commit gate
python3 /Users/xin/auto-skills/Non-Stop-Run/scripts/controller.py commit-gate \
  --validation-pass \
  --debugger-pass \
  --auto-commit \
  --message "feat(search): add advanced settings"

# 写 exit summary，不依赖聊天记忆复盘
python3 /Users/xin/auto-skills/Non-Stop-Run/scripts/controller.py exit-summary \
  --summary "Phase shipped with validation"
```

## When To Load References

- 需要安装或接入 hook：读 [references/hook-setup.md](references/hook-setup.md)。
- 需要判断 auto-commit / milestone / recovery 规则：读 [references/loop-policy.md](references/loop-policy.md)。
- 需要理解 Codex `/goal` 与 NSR 的边界：读 [references/codex-goal.md](references/codex-goal.md)。
- 需要把 bugloop / audit / nightly-fix 这类专项能力接成插槽：读 [references/slots.md](references/slots.md)。
- 需要把 NSR 阶段结果导出到 Brainkeeper：读 [references/brainkeeper.md](references/brainkeeper.md)。
- 需要让 NSR 从真实运行/外部项目里持续精进：读 [references/self-improve.md](references/self-improve.md)。

## Agent Rule

NSR 可以主动执行，但不能冒充用户授权高风险动作。它负责推进和打点，不负责绕过安全边界。

维护记录：`web agent` / `Role: coordinator` 于 2026-05-08 创建第一版 NSR。
