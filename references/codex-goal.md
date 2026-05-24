# Codex Goal Bridge

Codex CLI 0.128.0 的公开 changelog 已写明：Codex 增加了 persisted `/goal` workflows，包含 app-server APIs、model tools、runtime continuation，以及 TUI 的 create / pause / resume / clear 控制。

源码层也能看到 `Feature::Goals`，说明它是 experimental feature，默认关闭，并连接到 goal tools、thread goal state 和 continuation。

NSR 的定位不是替代 `/goal`，而是把同一份 goal contract 落到 agent 可执行、可验证、可恢复的 runtime 里。

可靠边界：

- Codex `/goal` 是产品层的目标声明和延续入口；是否可用取决于当前 Codex 版本、feature flag 和宿主暴露的工具。
- NSR 是 runtime 层的执行、打点、验证、commit gate、recovery harness。
- 两者可以共享同一份 goal contract，但 NSR 不依赖 `/goal` 存在。
- 当前本机工具层仍不应该假装能直接控制隐藏/未暴露的 `/goal` API；可用时桥接，不可用时用普通 prompt + NSR runtime。

Use:

```bash
python3 /Users/xin/auto-skills/Non-Stop-Run/scripts/controller.py goal-contract --write
python3 /Users/xin/auto-skills/Non-Stop-Run/scripts/controller.py goal-prompt
```

Recommended mapping:

- `/goal`: capture the human-facing objective, target phase, done_when, and ask policy when available.
- `nsr start`: store the same contract into durable runtime state.
- `nsr goal-contract --write`: persist `goal.md` under the NSR session directory.
- `nsr goal-prompt`: emit a prompt suitable for Codex `/goal` or a normal chat message.

Useful verified references:

- OpenAI Codex changelog, Codex CLI 0.128.0: https://developers.openai.com/codex/changelog
- Codex source feature flag: https://github.com/openai/codex/blob/main/codex-rs/features/src/lib.rs
- Codex source tool config: https://github.com/openai/codex/blob/main/codex-rs/tools/src/tool_config.rs
- Codex source thread goal model: https://github.com/openai/codex/blob/main/codex-rs/state/src/model/thread_goal.rs

Maintenance note: created by `web agent` (`Role: coordinator`) on 2026-05-08.
