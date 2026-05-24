#!/usr/bin/env python3
import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path


SCRIPTS = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPTS))

from runtime import current_runtime  # noqa: E402
from state import SKILL_VERSION  # noqa: E402
from hook_adapter import handle_request  # noqa: E402


def check(name: str, condition: bool, detail: str = "") -> None:
    status = "PASS" if condition else "FAIL"
    suffix = f": {detail}" if detail else ""
    print(f"[{status}] {name}{suffix}")
    if not condition:
        raise AssertionError(name)


def git(repo: Path, *args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["git", "-C", str(repo), *args],
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )


def setup_repo() -> Path:
    repo = Path(tempfile.mkdtemp(prefix="nsr-git-"))
    git(repo, "init")
    git(repo, "config", "user.email", "nsr@example.local")
    git(repo, "config", "user.name", "NSR Test")
    (repo / "demo.txt").write_text("one\n", encoding="utf-8")
    git(repo, "add", "demo.txt")
    first = git(repo, "commit", "-m", "chore: initial")
    check("initial commit succeeds", first.returncode == 0, first.stderr)
    return repo


def main() -> int:
    home = tempfile.mkdtemp(prefix="nsr-home-")
    os.environ["LOOOP_HOME"] = home

    repo = setup_repo()
    rt = current_runtime(session_id="test-session", project_root=str(repo))

    missing = rt.current()
    check("missing current is non-creating", missing["action"] == "missing")
    version = rt.version_info()
    check("version command reports skill version", version["skill_version"] == SKILL_VERSION)
    slots = rt.slots()
    check("slots include bugloop", any(slot["name"] == "bugloop" for slot in slots["slots"]))
    check("slots include audit", any(slot["name"] == "audit" for slot in slots["slots"]))
    check("slots include continuity", any(slot["name"] == "continuity" for slot in slots["slots"]))
    slot_info = rt.slot_info("nightly-fix")
    check("nightly-fix resolves to bugloop", slot_info["slot"]["name"] == "bugloop")
    audit_info = rt.slot_info("review-gate")
    check("review-gate resolves to audit", audit_info["slot"]["name"] == "audit")
    continuity_info = rt.slot_info("offduty")
    check("offduty resolves to continuity", continuity_info["slot"]["name"] == "continuity")

    started = rt.start(
        objective="Ship a traceable loop",
        target_phase="v0",
        owner_agent="web agent",
        role="coordinator",
        execution_mode="companion",
    )
    check("start activates loop", started["mode"] == "active")
    check("start records objective", started["objective"] == "Ship a traceable loop")
    check("summary includes skill version", started["skill_version"] == SKILL_VERSION)

    slot_rt = current_runtime(session_id="slot-session", project_root=str(repo))
    slot_started = slot_rt.start(
        objective="Run critical bug hunt",
        slot="nightly-fix",
        owner_agent="web agent",
        role="coordinator",
    )
    check("slot start records profile", slot_started["profile_slot"] == "bugloop")
    check("slot start applies target phase", slot_started["target_phase"] == "nightly-fix")
    check("slot start applies max iterations", slot_started["max_iterations"] == 12)
    slot_contract = slot_rt.goal_contract()
    check("slot contract names profile", "Profile slot: bugloop" in slot_contract["text"])

    audit_rt = current_runtime(session_id="audit-session", project_root=str(repo))
    audit_started = audit_rt.start(
        objective="Audit release gate",
        slot="audit",
        owner_agent="web agent",
        role="coordinator",
    )
    check("audit slot start records profile", audit_started["profile_slot"] == "audit")
    check("audit slot applies target phase", audit_started["target_phase"] == "audit-gate")
    check("audit slot applies max iterations", audit_started["max_iterations"] == 8)
    audit_contract = audit_rt.goal_contract()
    check("audit contract names profile skill", "Profile skill: multi-review" in audit_contract["text"])
    check("audit slot applies execution mode", "Execution mode: companion" in audit_contract["text"])
    check("audit slot applies commit policy", "Commit policy: manual" in audit_contract["text"])
    check("audit contract includes safety notes", "Never claim audit completion" in audit_contract["text"])
    check("audit slot requires completion gate", audit_started["completion_gate"] == "audit")
    check("audit slot gate starts pending", audit_started["completion_gate_status"] == "pending")

    gate_repo = setup_repo()
    forced_rt = current_runtime(session_id="forced-gate-session", project_root=str(gate_repo))
    forced_started = forced_rt.start(
        objective="Finish p100-p110",
        target_phase="p100-p110",
        owner_agent="web agent",
        role="coordinator",
        completion_gate="audit",
        gate_scope="p100-p110",
        gate_quorum=2,
    )
    check("forced gate records kind", forced_started["completion_gate"] == "audit")
    check("forced gate records scope", forced_started["completion_gate_scope"] == "p100-p110")
    premature = forced_rt.iteration_result(
        success=True,
        summary="Tried to close before audit",
        key_changes_made=["Prepared milestone"],
        validation="not yet audited",
        debugger="no blocker except gate",
        should_fully_stop=True,
    )
    check("forced gate blocks full stop", premature["result"]["should_fully_stop"] is False)
    blocked_close = forced_rt.close(summary="Should not close yet")
    check("forced gate blocks close", blocked_close["ok"] is False and blocked_close["blocked"] is True)
    evidence_path = gate_repo / ".ai" / "reviews" / "log" / "gate-p100-p110.json"
    evidence_path.parent.mkdir(parents=True, exist_ok=True)
    evidence_path.write_text('{"gate_status":"clear"}\n', encoding="utf-8")
    forced_rt.validate_command(command="test -f demo.txt", timeout=10)
    forced_gate = forced_rt.audit_gate(
        scope="p100-p110",
        verdict="pass",
        reviewers=2,
        p0_blockers=0,
        p1_blockers=0,
        validation="pass",
        evidence=[".ai/reviews/log/gate-p100-p110.json"],
        residual_risk="Only low-risk gaps remain",
    )
    check("forced audit gate passes", forced_gate["check"]["status"] == "pass")
    forced_closed = forced_rt.close(summary="Gate passed")
    check("forced gate allows close", forced_closed["mode"] == "disabled")

    multi_rt = current_runtime(session_id="multi-gate-session", project_root=str(gate_repo))
    multi_rt.start(
        objective="Check multi-review gate",
        target_phase="mr",
        owner_agent="web agent",
        role="coordinator",
        completion_gate="audit",
        gate_scope="mr",
        gate_quorum=2,
    )
    multi_rt.validate_command(command="test -f demo.txt", timeout=10)
    review_a = gate_repo / ".ai" / "reviews" / "model-a" / "mr-review-20260518.md"
    review_b = gate_repo / ".ai" / "reviews" / "model-b" / "mr-review-20260518.md"
    review_a.parent.mkdir(parents=True, exist_ok=True)
    review_b.parent.mkdir(parents=True, exist_ok=True)
    review_a.write_text("Reviewer: model-a\nVerdict: PASS\n", encoding="utf-8")
    review_b.write_text("Reviewer: model-b\nVerdict: PASS\n", encoding="utf-8")
    multi_gate_path = gate_repo / ".ai" / "reviews" / "log" / "gate-mr.json"
    multi_gate_path.write_text(
        json.dumps(
            {
                "schema": "multi_review.gate.v1",
                "milestone": "mr",
                "commit": "abc123",
                "gate_status": "clear",
                "review_count": 2,
                "min_reviews": 2,
                "blocking_count": 0,
                "unknown_count": 0,
                "invalid_count": 0,
                "reviews": [
                    {"path": ".ai/reviews/model-a/mr-review-20260518.md"},
                    {"path": ".ai/reviews/model-b/mr-review-20260518.md"},
                ],
            },
            ensure_ascii=False,
        )
        + "\n",
        encoding="utf-8",
    )
    multi_check = multi_rt.completion_check(artifact=".ai/reviews/log/gate-mr.json")
    check("multi-review gate artifact passes completion check", multi_check["status"] == "pass")

    slice_result = rt.begin_slice(
        summary="Edit demo file",
        owned_files=["demo.txt"],
    )
    check("begin slice creates id", bool(slice_result["current_slice_id"]))
    check("begin slice records clean baseline", slice_result["dirty_baseline"] == [])

    context = rt.context_for_user_prompt()
    check("context injects while active", context["action"] == "inject_context")
    check("context names NSR", "<nsr_context" in context["message"])
    check("context carries target phase", "v0" in context["message"])

    stop = rt.stop_decision(last_assistant_message="partial update")
    check("stop gate blocks active next action", stop["decision"] == "block")

    validation = rt.validate_command(command="test -f demo.txt", timeout=10)
    check("validate command passes", validation["status"] == "pass")
    check("validate command writes log", Path(validation["log_path"]).is_file())

    goal_contract = rt.goal_contract(write=True)
    check("goal contract writes file", Path(goal_contract["path"]).is_file())
    check("goal contract includes objective", "Ship a traceable loop" in goal_contract["text"])
    check("goal contract includes version", f"NSR version: {SKILL_VERSION}" in goal_contract["text"])
    check("goal contract includes execution mode", "Execution mode: companion" in goal_contract["text"])
    goal_prompt = rt.codex_goal_prompt()
    check("goal prompt is usable for Codex", "Codex /goal contract" in goal_prompt["text"])

    result = rt.iteration_result(
        success=True,
        summary="Validated goal bridge shape",
        key_changes_made=["Recorded the current slice result"],
        key_learnings=["Notes preserve iteration facts outside chat memory"],
        validation="test -f demo.txt passed",
        debugger="no blocker found",
    )
    check("iteration result records success", result["result"]["success"] is True)
    check("iteration result writes notes", Path(result["notes_path"]).is_file())
    check("notes include learning", "Notes preserve iteration facts" in Path(result["notes_path"]).read_text())

    learning = rt.learn(
        source="gnhf iteration prompt",
        summary="Record no-op slices as failed progress",
        evidence="Complete no-op iterations should not spin",
        tags=["loop", "no-op"],
        lesson_type="reusable-detail",
        priority="P1",
        promote_candidate=True,
    )
    check("learn writes learning log", Path(learning["learnings_path"]).is_file())
    check("learn records priority", learning["learning"]["priority"] == "P1")
    check("learn records lesson type", learning["learning"]["lesson_type"] == "reusable-detail")
    check("learn defaults to repo scope", learning["learning"]["scope"] == "repo")
    check("learn fills repo scope key", learning["learning"]["scope_key"] == str(repo.resolve()))
    check("learn updates notes", "Record no-op slices" in Path(learning["notes_path"]).read_text())
    duplicate = rt.learn(
        source="gnhf iteration prompt",
        summary="Record no-op slices as failed progress",
        evidence="duplicate smoke",
        tags=["loop", "no-op"],
        lesson_type="reusable-detail",
        priority="P1",
    )
    check("learn detects duplicate", duplicate["learning"]["duplicate"] is True)
    scoped_learning = rt.learn(
        source="provider postmortem",
        summary="Record no-op slices as failed progress",
        evidence="Provider-specific behavior can conflict with repo practice",
        tags=["loop", "no-op"],
        lesson_type="reusable-detail",
        priority="P1",
        scope="provider",
        scope_key="anthropic",
        conflicts_with=["repo default may allow verification-only no-op evidence"],
    )
    check("same lesson in another scope is not duplicate", scoped_learning["learning"]["duplicate"] is False)
    check("learn records conflicts", scoped_learning["learning"]["conflicts_with"])
    recovered_learning = rt.recovery_report()
    check("recover includes learnings path", Path(recovered_learning["learnings_path"]).is_file())

    (repo / "demo.txt").write_text("two\n", encoding="utf-8")
    hook_tool = handle_request(
        "claude",
        {
            "hook_event_name": "PostToolUse",
            "session_id": "test-session",
            "cwd": str(repo),
            "tool_name": "Edit",
            "tool_input": {"file_path": str(repo / "demo.txt")},
        },
    )
    check("post tool hook records activity", hook_tool.get("continue") is True)
    recovered_mid = rt.recovery_report()
    check("recover includes touched file", "demo.txt" in recovered_mid["loop"]["touched_files"])

    failed_gate = rt.commit_gate(
        validation_pass=False,
        debugger_pass=True,
        auto_commit=True,
    )
    check("commit gate rejects failed validation", failed_gate["can_commit"] is False)
    check("failed gate writes patch snapshot", bool(failed_gate.get("patch_path")))

    passed_gate = rt.commit_gate(
        validation_pass=True,
        debugger_pass=True,
        auto_commit=True,
        message="test(nsr): commit owned slice",
    )
    check("commit gate allows owned validated commit", passed_gate["can_commit"] is True)
    check("commit was created", bool(passed_gate.get("commit")))
    log = git(repo, "log", "-1", "--pretty=%B").stdout
    check("commit footer includes agent", "Agent: web agent" in log)
    check("commit footer includes slice", "NSR-Slice:" in log)

    milestone = rt.milestone(
        summary="Slice committed",
        validation="test validation passed",
        debugger="no P0/P1 blocker",
        next_action="Close the loop",
    )
    check("milestone file exists", Path(milestone["path"]).is_file())
    checkpoint = rt.brainkeeper_export(
        write=True,
        reason="Slice checkpoint",
        recent_events=2,
    )
    check("brainkeeper export writes file", Path(checkpoint["path"]).is_file())
    check("brainkeeper export uses checkpoint tool", checkpoint["tool"] == "brain_checkpoint")
    check("brainkeeper export records repo", checkpoint["payload"]["repo"] == str(repo.resolve()))
    check("brainkeeper export records task", checkpoint["payload"]["task"] == "Ship a traceable loop")
    stored_checkpoint = json.loads(Path(checkpoint["path"]).read_text(encoding="utf-8"))
    check("brainkeeper export stores arguments", stored_checkpoint["arguments"]["status"] == "Slice checkpoint")

    (repo / "parallel.txt").write_text("parallel\n", encoding="utf-8")
    rt.begin_slice(summary="Try with pre-existing dirty file", owned_files=["demo.txt"])
    (repo / "demo.txt").write_text("three\n", encoding="utf-8")
    blocked_gate = rt.commit_gate(
        validation_pass=True,
        debugger_pass=True,
        auto_commit=True,
    )
    check("baseline dirty blocks auto commit", blocked_gate["can_commit"] is False)
    check(
        "baseline dirty reason is explicit",
        any("existed before this slice" in reason for reason in blocked_gate["reasons"]),
    )
    git(repo, "add", "parallel.txt", "demo.txt")
    git(repo, "commit", "-m", "test: clear baseline fixture")
    rt.begin_slice(summary="Resume after clearing baseline", owned_files=["demo.txt"])
    (repo / "demo.txt").write_text("four\n", encoding="utf-8")

    hook_context = handle_request(
        "codex",
        {
            "hook_event_name": "UserPromptSubmit",
            "session_id": "test-session",
            "cwd": str(repo),
        },
    )
    check("codex hook injects context", "hookSpecificOutput" in hook_context)

    hook_session = handle_request(
        "codex",
        {
            "hook_event_name": "SessionStart",
            "session_id": "test-session",
            "cwd": str(repo),
            "source": "resume",
        },
    )
    check("codex session hook injects context", "hookSpecificOutput" in hook_session)
    check(
        "codex session hook labels event",
        hook_session["hookSpecificOutput"]["hookEventName"] == "SessionStart",
    )

    hook_permission = handle_request(
        "codex",
        {
            "hook_event_name": "PermissionRequest",
            "session_id": "test-session",
            "cwd": str(repo),
            "tool_name": "exec_command",
            "permission_mode": "danger-full-access",
            "tool_input": {"command": "echo ok"},
            "reason": "smoke",
        },
    )
    check(
        "permission hook records without deciding",
        hook_permission["hookSpecificOutput"]["hookEventName"] == "PermissionRequest",
    )

    hook_postcompact = handle_request(
        "codex",
        {
            "hook_event_name": "PostCompact",
            "session_id": "test-session",
            "cwd": str(repo),
        },
    )
    check("postcompact hook records activity", hook_postcompact.get("continue") is True)

    hook_stop = handle_request(
        "claude",
        {
            "hook_event_name": "Stop",
            "session_id": "test-session",
            "cwd": str(repo),
            "last_assistant_message": "done?",
        },
    )
    check("claude stop hook blocks active loop", hook_stop.get("decision") == "block")

    closed = rt.close(summary="Finished v0 test.")
    check("close disables mode", closed["mode"] == "disabled")
    check("close writes exit summary", Path(closed["latest_exit_summary"]).is_file())
    allowed = handle_request(
        "claude",
        {"hook_event_name": "Stop", "session_id": "test-session", "cwd": str(repo)},
    )
    check("stop hook allows after close", allowed.get("continue") is True)

    events_path = Path(home) / "sessions" / "test-session" / "events.jsonl"
    check("events log exists", events_path.is_file())
    check("events log has entries", len(events_path.read_text().splitlines()) >= 5)

    snippet = subprocess.check_output(
        [
            sys.executable,
            str(SCRIPTS / "install_snippets.py"),
            "--host",
            "claude",
        ],
        text=True,
    )
    check("install snippet mentions PostToolUse", "PostToolUse" in snippet)
    codex_snippet = subprocess.check_output(
        [
            sys.executable,
            str(SCRIPTS / "install_snippets.py"),
            "--host",
            "codex",
        ],
        text=True,
    )
    check("codex install snippet uses current hooks flag", "[features].hooks" in codex_snippet)
    codex_config = json.loads(codex_snippet)["codex"]
    check("codex install snippet includes hooks", codex_config["features"]["hooks"] is True)
    for event_name in (
        "SessionStart",
        "UserPromptSubmit",
        "PermissionRequest",
        "PreCompact",
        "PostCompact",
        "PreToolUse",
        "PostToolUse",
        "Stop",
    ):
        check(
            f"codex install snippet includes {event_name}",
            event_name in codex_config["hooks"],
        )
    check(
        "codex session hook matcher is constrained",
        codex_config["hooks"]["SessionStart"][0]["matcher"] == "startup|resume|clear",
    )
    check("codex install snippet avoids old longrun", "longrun_hook.py" not in codex_snippet)

    guard_repo = setup_repo()
    guard_rt = current_runtime(session_id="guard-session", project_root=str(guard_repo))
    guard_rt.start(
        objective="Stop after one slice",
        target_phase="guard",
        owner_agent="web agent",
        role="coordinator",
        max_iterations=1,
    )
    guard_rt.begin_slice(summary="Allowed slice", owned_files=["demo.txt"])
    blocked = guard_rt.begin_slice(summary="Blocked slice", owned_files=["demo.txt"])
    check("max iteration guard blocks second slice", blocked["status"] == "blocked")
    restarted = guard_rt.start(
        objective="Restart cleanly",
        target_phase="guard",
        owner_agent="web agent",
        role="coordinator",
        max_iterations=1,
    )
    check("start resets iteration guard state", restarted["status"] == "running")
    allowed_again = guard_rt.begin_slice(summary="Allowed after restart", owned_files=["demo.txt"])
    check("restart allows first slice again", allowed_again["status"] == "running")

    print("\nALL CHECKS PASSED")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
