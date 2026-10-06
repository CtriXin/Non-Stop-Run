#!/usr/bin/env python3
"""Tests for loop_hook — focus on the failure paths the old NSR never covered.

Plain stdlib, no pytest needed:  python3 test_loop_hook.py
"""
import os
import subprocess
import tempfile
from pathlib import Path

import loop_hook as L


class FakeRepo:
    """Drive decide() without a real git repo: control diff hash + test result."""

    def __init__(self):
        self._hash = "h0"
        self._tests = None  # None / True / False

    def install(self):
        L.diff_hash = lambda repo: self._hash
        L.tests_pass = lambda cmd, repo: self._tests


def run_checks():
    out = []
    real_diff_hash = L.diff_hash
    real_tests_pass = L.tests_pass

    def check(name, cond):
        out.append((name, bool(cond)))

    # ---- atomic state roundtrip ----
    with tempfile.TemporaryDirectory() as d:
        p = os.path.join(d, "s.json")
        st = L.fresh_state()
        st["step_count"] = 7
        L.save_state(p, st)
        check("atomic save/load roundtrip", L.load_state(p)["step_count"] == 7)
        check("tmp file cleaned up", not os.path.exists(p + ".tmp"))

    # ---- corrupt / missing state -> fresh, never crash (pit #4/#5) ----
    with tempfile.TemporaryDirectory() as d:
        p = os.path.join(d, "s.json")
        with open(p, "w") as f:
            f.write('{"step_count": 3, TRUNCATED')  # corrupt JSON
        check("corrupt state loads fresh", L.load_state(p)["step_count"] == 0)
        check("missing state loads fresh",
              L.load_state(os.path.join(d, "nope.json"))["step_count"] == 0)

    fake = FakeRepo()
    fake.install()

    # ---- brake 1: step limit ----
    L.MAX_STEPS, L.MAX_NO_CHANGE, L.MAX_RED, L.TEST_CMD = 3, 99, 99, ""
    st = L.fresh_state()
    st["step_count"] = 2
    fake._hash = "changing-1"
    allow, _ = L.decide(st, ".")
    check("step limit trips -> allow stop", allow is True)

    # ---- brake 2: stall / infinite-block guard ----
    L.MAX_STEPS, L.MAX_NO_CHANGE = 99, 3
    st = L.fresh_state()
    st["no_change_streak"], st["last_diff_hash"] = 2, "same"
    fake._hash = "same"  # unchanged -> streak hits 3
    allow, _ = L.decide(st, ".")
    check("stall trips -> allow stop", allow is True)

    # change resets the stall streak -> keep going
    st = L.fresh_state()
    st["no_change_streak"], st["last_diff_hash"] = 2, "old"
    fake._hash = "new"
    allow, _ = L.decide(st, ".")
    check("worktree change resets streak", st["no_change_streak"] == 0)
    check("progressing -> block (keep going)", allow is False)

    # ---- brake 3: tests green = done ----
    L.TEST_CMD = "pytest"
    fake._tests = True
    st = L.fresh_state()
    fake._hash = "x1"
    allow, reason = L.decide(st, ".")
    check("tests green -> allow stop (done)", allow is True and "done" in reason)

    # tests red -> block, keep fixing
    L.MAX_RED = 5
    fake._tests = False
    st = L.fresh_state()
    fake._hash = "x2"
    allow, _ = L.decide(st, ".")
    check("tests red -> block (keep fixing)", allow is False and st["red_streak"] == 1)

    # tests red death-spiral -> stop after MAX_RED
    L.MAX_RED = 3
    fake._tests = False
    st = L.fresh_state()
    st["red_streak"] = 2
    fake._hash = "x3"
    allow, _ = L.decide(st, ".")
    check("red death-spiral -> allow stop after MAX_RED", allow is True)

    # ---- real git smoke: state file itself must not defeat no-change brake ----
    L.diff_hash = real_diff_hash
    L.tests_pass = real_tests_pass
    old_state_file = L.STATE_FILE
    with tempfile.TemporaryDirectory() as d:
        repo = Path(d)
        subprocess.run(["git", "-C", d, "init"], check=True, capture_output=True)
        subprocess.run(["git", "-C", d, "config", "user.name", "test"],
                       check=True, capture_output=True)
        subprocess.run(["git", "-C", d, "config", "user.email", "test@example.com"],
                       check=True, capture_output=True)
        (repo / "README.md").write_text("# fixture\n", encoding="utf-8")
        subprocess.run(["git", "-C", d, "add", "README.md"],
                       check=True, capture_output=True)
        subprocess.run(["git", "-C", d, "commit", "-m", "init"],
                       check=True, capture_output=True)

        L.STATE_FILE = ".loop_state_test.json"
        L.MAX_STEPS, L.MAX_NO_CHANGE, L.MAX_RED, L.TEST_CMD = 99, 2, 99, ""
        state_path = str(repo / L.STATE_FILE)
        st = L.load_state(state_path)
        allow1, _ = L.decide(st, d)
        L.save_state(state_path, st)
        st = L.load_state(state_path)
        allow2, _ = L.decide(st, d)
        L.save_state(state_path, st)
        st = L.load_state(state_path)
        allow3, reason = L.decide(st, d)
        check("real git state file ignored for stall",
              allow1 is False and allow2 is False and allow3 is True
              and "no change" in reason)
    L.STATE_FILE = old_state_file

    # ---- regression: untracked file CONTENT change must move the fingerprint.
    # git diff omits untracked content and status only shows the path, so without
    # untracked_fingerprint an agent polishing a new file looks stalled. ----
    with tempfile.TemporaryDirectory() as d:
        subprocess.run(["git", "-C", d, "init"], check=True, capture_output=True)
        repo = Path(d)
        (repo / "fresh.py").write_text("v1\n", encoding="utf-8")
        h1 = L.diff_hash(d)
        (repo / "fresh.py").write_text("v2-completely-different\n", encoding="utf-8")
        h2 = L.diff_hash(d)
        check("untracked content change moves fingerprint", h1 != h2)

    # ---- regression: Stop-hook cwd moving between repo root and a subdir must
    # NOT split state into per-directory files. Before the fix each dir had its
    # own .loop_state.json: counters restarted per dir and each dir's rewritten
    # state file looked like an untracked change to the other, so an agent that
    # alternated cwd with zero edits ran ~59 steps instead of stalling at 3. ----
    import json
    import sys
    hook = str(Path(__file__).resolve().parent / "loop_hook.py")

    def run_hook(cwd, env):
        r = subprocess.run([sys.executable, hook], input=json.dumps({"cwd": str(cwd)}),
                           capture_output=True, text=True, env=env, timeout=60)
        return json.loads(r.stdout or "{}").get("decision") != "block"

    def git_fixture(d):
        repo = Path(d)
        subprocess.run(["git", "-C", d, "init"], check=True, capture_output=True)
        (repo / "src").mkdir()
        (repo / "src" / "a.py").write_text("x = 1\n", encoding="utf-8")
        subprocess.run(["git", "-C", d, "add", "."], check=True, capture_output=True)
        subprocess.run(["git", "-C", d, "-c", "user.name=t", "-c", "user.email=t@e",
                        "commit", "-m", "init"], check=True, capture_output=True)
        return repo

    base_env = {k: v for k, v in os.environ.items() if not k.startswith("LOOP_")}
    with tempfile.TemporaryDirectory() as d:
        repo = git_fixture(d)
        env = {**base_env, "LOOP_MAX_STEPS": "30", "LOOP_MAX_NO_CHANGE": "3"}
        calls = None
        for i in range(12):
            if run_hook(repo if i % 2 == 0 else repo / "src", env):
                calls = i + 1
                break
        check("cwd alternating root/subdir still trips stall brake", calls == 4)
        check("state file anchored at git root, not subdir",
              (repo / ".loop_state.json").exists()
              and not (repo / "src" / ".loop_state.json").exists())

    with tempfile.TemporaryDirectory() as d:
        repo = git_fixture(d)
        env = {**base_env, "LOOP_MAX_STEPS": "4", "LOOP_MAX_NO_CHANGE": "99"}
        calls = None
        for i in range(12):
            (repo / "src" / "a.py").write_text(f"x = {i + 2}\n", encoding="utf-8")
            if run_hook(repo if i % 2 == 0 else repo / "src", env):
                calls = i + 1
                break
        check("cwd alternating does not multiply step limit", calls == 4)

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
