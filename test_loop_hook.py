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

    # ---- regression: concurrent sessions in one repo share the state file.
    # A fixed "<state>.tmp" made writers truncate/interleave the same inode
    # (torn JSON -> load_state silently resets every brake) and the loser's
    # os.replace raised FileNotFoundError (hook crash). ----
    import json
    import threading
    with tempfile.TemporaryDirectory() as d:
        p = os.path.join(d, ".loop_state.json")
        errors, torn = [], []

        def writer(wid):
            for i in range(300):
                st = L.fresh_state()
                st["step_count"] = i
                st["started_at"] = "x" * ((wid * 37) % 200)  # varied lengths
                try:
                    L.save_state(p, st)
                except Exception as exc:  # noqa: BLE001
                    errors.append(exc)

        threads = [threading.Thread(target=writer, args=(w,)) for w in range(8)]
        for t in threads:
            t.start()
        while any(t.is_alive() for t in threads):
            try:
                with open(p, encoding="utf-8") as f:
                    json.load(f)
            except FileNotFoundError:
                pass
            except json.JSONDecodeError:
                torn.append(1)
        for t in threads:
            t.join()
        check("concurrent save_state never crashes", not errors)
        check("concurrent save_state never leaves torn JSON", not torn)
        check("concurrent save_state leaves no tmp files",
              [n for n in os.listdir(d) if n.endswith(".tmp")] == [])

    # another session's in-flight "<state>.<rand>.tmp" is not worktree progress
    with tempfile.TemporaryDirectory() as d:
        subprocess.run(["git", "-C", d, "init"], check=True, capture_output=True)
        Path(d, "README.md").write_text("x\n", encoding="utf-8")
        h1 = L.diff_hash(d)
        Path(d, ".loop_state.json.k3j9x_.tmp").write_text("{}", encoding="utf-8")
        h2 = L.diff_hash(d)
        check("in-flight state tmp ignored by fingerprint", h1 == h2)

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
