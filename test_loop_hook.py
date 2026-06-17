#!/usr/bin/env python3
"""Tests for loop_hook — focus on the failure paths the old NSR never covered.

Plain stdlib, no pytest needed:  python3 test_loop_hook.py
"""
import os
import tempfile

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
