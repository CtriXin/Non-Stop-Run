# NSR

**已推翻重写。**

NSR 现在是一个极简 Stop hook:agent 想停时默认 `block` 继续写代码;
只有完成或撞刹车才 `allow stop`。

旧实现(deprecated)已归档到 [`legacy/`](legacy/),废弃原因和重写带走的坑
清单见 [`legacy/DEPRECATED.md`](legacy/DEPRECATED.md)。

## 新方向

让 Claude Code / Codex 自主写代码不停,直到完成或撞刹车。
一个 Stop hook + 3 条刹车(步数上限 / 空转检测 / 测试红死磕),单文件核心。

## 核心文件

- [`loop_hook.py`](loop_hook.py):新版核心 Stop hook。
- [`test_loop_hook.py`](test_loop_hook.py):轻量回归测试。
- [`commit_gate.py`](commit_gate.py):agent commit 前的保守 safety gate。
- [`test_commit_gate.py`](test_commit_gate.py):commit gate 回归测试。
- [`legacy/`](legacy/):旧 NSR 实现,只作参考,不再维护。

## 3 条刹车

1. `LOOP_MAX_STEPS`(默认 30):步数上限,防止跑飞烧钱。
2. `LOOP_MAX_NO_CHANGE`(默认 3):worktree 连续 N 步没变就停,防无限 block。
3. `LOOP_TEST_CMD`:测试绿灯就停,红灯继续修;红满 `LOOP_MAX_RED`(默认 5)就停下问人。

状态写入 `.loop_state.json`,使用 tmp + `os.replace` 原子写;状态损坏时自动重建,
不让 hook 崩溃。worktree 指纹会忽略 state/tmp 文件,避免 hook 自己写状态导致
空转刹车失效。

## 安全 commit gate

`commit_gate.py` 不创建 commit,只检查当前 dirty tree 是否适合 agent 自主提交。
它会保守拦截:

- secret/local config 路径,例如 `.env*`, key/cert/db 文件。
- secret-like 内容,例如 private key block、常见 token、长 secret assignment。
- generated/cache 路径,例如 `node_modules/`, `dist/`, `build/`, `__pycache__/`。
- dependency lockfile、binary file、large file、symlink 等需要人工看一眼的改动。

运行:

```bash
python3 commit_gate.py --repo /path/to/repo
python3 commit_gate.py --repo /path/to/repo --json
```

## 用法

把 Claude Code / Codex 的 Stop hook 指向:

```bash
python3 /path/to/nsr/loop_hook.py
```

常用环境变量:

```bash
LOOP_TEST_CMD="pytest -q"
LOOP_MAX_STEPS=30
LOOP_MAX_NO_CHANGE=3
LOOP_MAX_RED=5
LOOP_TEST_SHELL=1   # 测试命令需要管道/重定向时再开
```

验证:

```bash
python3 test_loop_hook.py
python3 test_commit_gate.py
python3 commit_gate.py --repo .
```
