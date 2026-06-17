#!/usr/bin/env python3
"""loop_hook.py — keep Claude Code / Codex writing until done or a brake trips.

A Stop hook. When the agent tries to stop, this decides:
  - block -> "keep going, next step"   (the default)
  - allow -> let it stop, with a reason (a brake tripped, or it's done)

Three brakes — "don't stop" MUST have limits, or it burns money and drifts:
  1. step limit       ran too many steps -> stop before it goes off the rails
  2. stall/no-change   worktree unchanged N steps in a row -> stop. This also
                       kills the infinite-block loop the old NSR died on.
  3. tests             if a test cmd is set: green = done (allow stop);
                       red = keep fixing (block), but give up after MAX_RED so
                       it doesn't death-spiral on a red bar.

State lives in .loop_state.json, written atomically (tmp + os.replace) so a
crash/interrupt can't leave a corrupt file; load tolerates corruption and
starts fresh instead of crashing.
"""
from __future__ import annotations

import hashlib
import json
import os
import shlex
import subprocess
import sys
from datetime import datetime, timezone

# --- config (override via env) ---------------------------------------------
MAX_STEPS = int(os.environ.get("LOOP_MAX_STEPS", "30"))
MAX_NO_CHANGE = int(os.environ.get("LOOP_MAX_NO_CHANGE", "3"))
MAX_RED = int(os.environ.get("LOOP_MAX_RED", "5"))
TEST_CMD = os.environ.get("LOOP_TEST_CMD", "").strip()
STATE_FILE = os.environ.get("LOOP_STATE_FILE", ".loop_state.json")


def now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def fresh_state() -> dict:
    return {
        "step_count": 0,
        "last_diff_hash": "",
        "no_change_streak": 0,
        "red_streak": 0,
        "started_at": now_iso(),
    }


def load_state(path: str) -> dict:
    # tolerate missing OR corrupt state — never crash the loop (NSR pit #4/#5)
    try:
        with open(path, encoding="utf-8") as f:
            data = json.load(f)
    except (FileNotFoundError, json.JSONDecodeError, OSError, ValueError):
        return fresh_state()
    base = fresh_state()
    if isinstance(data, dict):
        base.update({k: data[k] for k in base if k in data})
    return base


def save_state(path: str, data: dict) -> None:
    # atomic write: tmp + os.replace (NSR pit #4 — old code wrote in place)
    tmp = f"{path}.tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    os.replace(tmp, path)


def diff_hash(repo: str) -> str:
    # fingerprint the worktree; git failure must not crash the hook (NSR pit)
    parts = []
    for args in (["diff", "--no-color"],
                 ["diff", "--cached", "--no-color"],
                 ["status", "--porcelain"]):
        try:
            r = subprocess.run(["git", "-C", repo, *args],
                               capture_output=True, text=True, timeout=30)
            parts.append(r.stdout)
        except (OSError, subprocess.SubprocessError):
            parts.append("")
    return hashlib.sha256("".join(parts).encode("utf-8", "replace")).hexdigest()


def tests_pass(cmd: str, repo: str):
    # None = no test cmd configured. cmd is the user's own (local trust).
    # default: shlex.split (no shell). Set LOOP_TEST_SHELL=1 for pipes etc.
    if not cmd:
        return None
    use_shell = bool(os.environ.get("LOOP_TEST_SHELL"))
    try:
        r = subprocess.run(cmd if use_shell else shlex.split(cmd),
                           shell=use_shell, cwd=repo,
                           capture_output=True, text=True, timeout=600)
        return r.returncode == 0
    except (OSError, subprocess.SubprocessError):
        return False


def decide(state: dict, repo: str) -> tuple[bool, str]:
    """Return (allow_stop, reason). Mutates state counters."""
    state["step_count"] += 1
    h = diff_hash(repo)
    if h == state["last_diff_hash"]:
        state["no_change_streak"] += 1
    else:
        state["no_change_streak"] = 0
    state["last_diff_hash"] = h

    # brake 1: step limit
    if state["step_count"] >= MAX_STEPS:
        return True, f"step limit reached ({MAX_STEPS}) — stopping before drift"
    # brake 2: stall / infinite-block guard
    if state["no_change_streak"] >= MAX_NO_CHANGE:
        return True, f"no change for {state['no_change_streak']} steps — stalled"
    # brake 3: tests
    passed = tests_pass(TEST_CMD, repo)
    if passed is True:
        return True, "tests green — done"
    if passed is False:
        state["red_streak"] += 1
        if state["red_streak"] >= MAX_RED:
            return True, f"tests still red after {MAX_RED} tries — stop and ask"
        return False, f"tests red — keep fixing ({state['red_streak']}/{MAX_RED})"
    # no test cmd: default keep going
    return False, "keep going — next step"


def main() -> int:
    try:
        payload = json.load(sys.stdin)
    except (json.JSONDecodeError, OSError, ValueError):
        payload = {}
    repo = (isinstance(payload, dict) and payload.get("cwd")) or os.getcwd()
    state_path = os.path.join(repo, STATE_FILE)

    state = load_state(state_path)
    allow_stop, reason = decide(state, repo)

    if allow_stop:
        save_state(state_path, fresh_state())   # reset for the next objective
        sys.stdout.write(json.dumps({}) + "\n")  # allow stop
        sys.stderr.write(f"[loop] stop: {reason}\n")
    else:
        save_state(state_path, state)
        sys.stdout.write(json.dumps({"decision": "block", "reason": reason}) + "\n")
        sys.stderr.write(f"[loop] continue: {reason}\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
