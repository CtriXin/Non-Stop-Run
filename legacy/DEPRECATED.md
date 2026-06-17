# DEPRECATED — 旧 NSR 实现

这一版 NSR 已废弃,推翻重写。代码归零,经验不归零。

## 为什么废弃

概念膨胀。价值内核其实只有 4 件事(继续 / 刹车 / 验证 / 安全 commit),
其余(brainkeeper / self-improve / learnings / audit quorum / slot 泛化 /
2306 行 god class)是没有验证价值的概念。个人用工具不需要框架。

## 新方向

一个 Stop hook + 3 条刹车,约 100 行单文件。让 Claude Code / Codex
自主写代码不停,直到完成或撞刹车。

## 重写时要带走的坑(NSR 用一个多月血换的)

1. **Stop hook 会无限刷屏 / 死循环** → 刹车要对同一停止状态计数,别死循环。
2. **要有步数上限**(旧版的 iteration guard) → 防跑飞烧钱。
3. **commit 前挡 secret / 危险文件** → 旧版 `_looks_dangerous` 是黑名单可绕,意识要带、实现要更稳。
4. **状态要原子写**(`os.replace`) → 旧版这里是破的(直接 `write_text` 覆写),崩溃即损坏。
5. **测试要覆盖失败路径**(空转 / 测试红 / 状态损坏) → 旧版的盲区。

## 状态

保留作参考,不再维护。新实现见上一级目录。
