#!/usr/bin/env python3
"""Tests for commit_gate.

Plain stdlib, no pytest needed:  python3 test_commit_gate.py
"""
import subprocess
import tempfile
from pathlib import Path

import commit_gate as G


def git(repo: Path, *args: str) -> None:
    result = subprocess.run(
        ["git", "-C", str(repo), *args],
        capture_output=True,
        text=True,
        timeout=30,
    )
    if result.returncode != 0:
        raise AssertionError(result.stderr or result.stdout)


def init_repo() -> Path:
    root = Path(tempfile.mkdtemp())
    git(root, "init")
    git(root, "config", "user.name", "test")
    git(root, "config", "user.email", "test@example.com")
    (root / "README.md").write_text("# fixture\n", encoding="utf-8")
    git(root, "add", "README.md")
    git(root, "commit", "-m", "init")
    return root


def has_reason(result: dict, text: str) -> bool:
    return any(text in item["reason"] for item in result["blocked"])


def run_checks():
    out = []

    def check(name, cond):
        out.append((name, bool(cond)))

    repo = init_repo()
    (repo / "notes.md").write_text("safe change\n", encoding="utf-8")
    result = G.scan(repo)
    check("safe dirty file passes", result["ok"] is True)

    repo = init_repo()
    env_name = "TO" + "KEN"
    (repo / ".env").write_text(env_name + "=" + ("abc" * 7) + "\n", encoding="utf-8")
    result = G.scan(repo)
    check(".env blocks", result["ok"] is False and has_reason(result, "secret"))

    repo = init_repo()
    (repo / "node_modules").mkdir()
    (repo / "node_modules" / "x.js").write_text("module.exports = 1\n", encoding="utf-8")
    result = G.scan(repo)
    check("generated path blocks", result["ok"] is False and has_reason(result, "generated"))

    repo = init_repo()
    key = "sk-" + ("a" * 32)
    (repo / "app.py").write_text(
        f"OPENAI_API_KEY={key}\n",
        encoding="utf-8",
    )
    result = G.scan(repo)
    check("secret-like content blocks", result["ok"] is False and len(result["blocked"]) == 1)

    repo = init_repo()
    (repo / "package-lock.json").write_text("{}\n", encoding="utf-8")
    result = G.scan(repo)
    check("lockfile blocks auto commit", result["ok"] is False and has_reason(result, "lockfile"))

    repo = init_repo()
    (repo / "blob.bin").write_bytes(b"abc\0def")
    result = G.scan(repo)
    check("binary file blocks", result["ok"] is False and has_reason(result, "binary"))

    return out


def main():
    results = run_checks()
    for name, ok in results:
        print(f"[{'PASS' if ok else 'FAIL'}] {name}")
    failed = [n for n, ok in results if not ok]
    if failed:
        print(f"\n{len(failed)} FAILED")
        return 1
    print("\nALL CHECKS PASSED")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
