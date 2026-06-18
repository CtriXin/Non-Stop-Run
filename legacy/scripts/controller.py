#!/usr/bin/env python3
import argparse
import json
from typing import Optional

from runtime import current_runtime


def _print(data: dict) -> int:
    print(json.dumps(data, ensure_ascii=False, indent=2))
    return 0


def _runtime(args: argparse.Namespace):
    return current_runtime(
        session_id=args.session_id,
        path=args.path,
        project_root=getattr(args, "project_root", None),
    )


def current_command(args: argparse.Namespace) -> int:
    return _print(_runtime(args).current(auto_create=args.auto_create))


def version_command(args: argparse.Namespace) -> int:
    return _print(_runtime(args).version_info())


def slots_command(args: argparse.Namespace) -> int:
    return _print(_runtime(args).slots())


def slot_info_command(args: argparse.Namespace) -> int:
    try:
        return _print(_runtime(args).slot_info(args.name))
    except ValueError as exc:
        return _print({"ok": False, "error": str(exc)})


def start_command(args: argparse.Namespace) -> int:
    try:
        return _print(
            _runtime(args).start(
                objective=args.objective,
                target_phase=args.target_phase,
                done_when=args.done_when,
                owner_agent=args.owner_agent,
                role=args.role,
                execution_mode=args.execution_mode,
                commit_policy=args.commit_policy,
                max_iterations=args.max_iterations,
                slot=args.slot,
                completion_gate=args.completion_gate,
                gate_scope=args.gate_scope,
                gate_quorum=args.gate_quorum,
                auto_rollback=args.auto_rollback,
            )
        )
    except ValueError as exc:
        return _print({"ok": False, "error": str(exc)})


def begin_slice_command(args: argparse.Namespace) -> int:
    return _print(
        _runtime(args).begin_slice(
            summary=args.summary,
            owned_files=args.owned_file,
        )
    )


def event_command(args: argparse.Namespace) -> int:
    return _print(
        _runtime(args).event(
            args.kind,
            args.summary,
            detail=args.detail,
            touched_files=args.touched_file,
        )
    )


def milestone_command(args: argparse.Namespace) -> int:
    return _print(
        _runtime(args).milestone(
            summary=args.summary,
            validation=args.validation,
            debugger=args.debugger,
            next_action=args.next_action,
            screenshots=args.screenshot,
        )
    )


def goal_contract_command(args: argparse.Namespace) -> int:
    return _print(_runtime(args).goal_contract(write=args.write))


def goal_prompt_command(args: argparse.Namespace) -> int:
    return _print(_runtime(args).codex_goal_prompt())


def quality_command(args: argparse.Namespace) -> int:
    return _print(
        _runtime(args).update_quality(
            validation_status=args.validation_status,
            validation_summary=args.validation_summary,
            debugger_status=args.debugger_status,
            debugger_summary=args.debugger_summary,
            residual_uncertainty=args.residual_uncertainty,
            blocker=args.blocker,
        )
    )


def iteration_result_command(args: argparse.Namespace) -> int:
    return _print(
        _runtime(args).iteration_result(
            success=args.success,
            summary=args.summary,
            key_changes_made=args.key_change,
            key_learnings=args.key_learning,
            validation=args.validation,
            debugger=args.debugger,
            should_fully_stop=args.should_fully_stop,
        )
    )


def audit_gate_command(args: argparse.Namespace) -> int:
    return _print(
        _runtime(args).audit_gate(
            scope=args.scope,
            verdict=args.verdict,
            artifact=args.artifact,
            reviewers=args.reviewers,
            p0_blockers=args.p0_blockers,
            p1_blockers=args.p1_blockers,
            validation=args.validation,
            evidence=args.evidence,
            browser_evidence=args.browser_evidence,
            residual_risk=args.residual_risk,
            commit=args.commit,
        )
    )


def completion_check_command(args: argparse.Namespace) -> int:
    return _print(
        _runtime(args).completion_check(
            artifact=args.artifact,
            require=args.require,
        )
    )


def learn_command(args: argparse.Namespace) -> int:
    return _print(
        _runtime(args).learn(
            source=args.source,
            summary=args.summary,
            evidence=args.evidence,
            tags=args.tag,
            lesson_type=args.lesson_type,
            priority=args.priority,
            fingerprint=args.fingerprint,
            promote_candidate=args.promote_candidate,
            scope=args.scope,
            scope_key=args.scope_key,
            conflicts_with=args.conflicts_with,
        )
    )


def slice_rollback_command(args: argparse.Namespace) -> int:
    return _print(_runtime(args).slice_rollback())


def validate_command(args: argparse.Namespace) -> int:
    return _print(
        _runtime(args).validate_command(
            command=args.command,
            timeout=args.timeout,
        )
    )


def context_command(args: argparse.Namespace) -> int:
    return _print(_runtime(args).context_for_user_prompt())


def stop_decision_command(args: argparse.Namespace) -> int:
    return _print(
        _runtime(args).stop_decision(
            last_assistant_message=args.last_assistant_message
        )
    )


def precompact_command(args: argparse.Namespace) -> int:
    return _print(_runtime(args).precompact(reason=args.reason))


def tool_use_command(args: argparse.Namespace) -> int:
    tool_input = json.loads(args.tool_input) if args.tool_input else {}
    tool_output = json.loads(args.tool_output) if args.tool_output else {}
    return _print(
        _runtime(args).record_tool_use(
            tool_name=args.tool_name,
            tool_input=tool_input,
            tool_output=tool_output,
        )
    )


def recover_command(args: argparse.Namespace) -> int:
    return _print(_runtime(args).recovery_report())


def close_command(args: argparse.Namespace) -> int:
    return _print(_runtime(args).close(summary=args.summary))


def tokens_report_command(args: argparse.Namespace) -> int:
    return _print(_runtime(args).tokens_report(tokens=args.tokens))


def session_stats_command(args: argparse.Namespace) -> int:
    return _print(_runtime(args).session_stats())


def exit_summary_command(args: argparse.Namespace) -> int:
    return _print(_runtime(args).exit_summary(summary=args.summary))


def brainkeeper_export_command(args: argparse.Namespace) -> int:
    return _print(
        _runtime(args).brainkeeper_export(
            write=args.write,
            reason=args.reason,
            recent_events=args.recent_events,
        )
    )


def commit_gate_command(args: argparse.Namespace) -> int:
    return _print(
        _runtime(args).commit_gate(
            validation_pass=args.validation_pass,
            debugger_pass=args.debugger_pass,
            auto_commit=args.auto_commit,
            message=args.message,
            owned_files=args.owned_file,
        )
    )


def gate_run_command(args: argparse.Namespace) -> int:
    try:
        return _print(
            _runtime(args).gate_run(
                checks=args.check,
                timeout=args.timeout,
            )
        )
    except ValueError as exc:
        return _print({"ok": False, "error": str(exc)})


def add_common(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--session-id")
    parser.add_argument("--path")
    parser.add_argument("--project-root")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="NSR controller.")
    sub = parser.add_subparsers(dest="command", required=True)

    current = sub.add_parser("current")
    add_common(current)
    current.add_argument("--auto-create", action="store_true")
    current.set_defaults(func=current_command)

    version = sub.add_parser("version")
    add_common(version)
    version.set_defaults(func=version_command)

    slots = sub.add_parser("slots")
    add_common(slots)
    slots.set_defaults(func=slots_command)

    slot_info = sub.add_parser("slot-info")
    add_common(slot_info)
    slot_info.add_argument("--name", required=True)
    slot_info.set_defaults(func=slot_info_command)

    start = sub.add_parser("start")
    add_common(start)
    start.add_argument("--objective", required=True)
    start.add_argument("--slot", default="")
    start.add_argument("--target-phase", default="")
    start.add_argument("--done-when", default="")
    start.add_argument("--owner-agent", default="")
    start.add_argument("--role", default="")
    start.add_argument(
        "--execution-mode", default="", choices=["", "hands-off", "companion"]
    )
    start.add_argument(
        "--commit-policy", default="", choices=["", "auto", "manual", "disabled"]
    )
    start.add_argument("--max-iterations", type=int, default=20)
    start.add_argument("--completion-gate", default="", choices=["", "audit"])
    start.add_argument("--gate-scope", default="")
    start.add_argument("--gate-quorum", type=int, default=0)
    start.add_argument("--auto-rollback", action="store_true", help="Auto git reset on failed slice")
    start.set_defaults(func=start_command)

    begin = sub.add_parser("begin-slice")
    add_common(begin)
    begin.add_argument("--summary", required=True)
    begin.add_argument("--owned-file", action="append", default=[])
    begin.set_defaults(func=begin_slice_command)

    event = sub.add_parser("event")
    add_common(event)
    event.add_argument("--kind", required=True)
    event.add_argument("--summary", required=True)
    event.add_argument("--detail", default="")
    event.add_argument("--touched-file", action="append", default=[])
    event.set_defaults(func=event_command)

    milestone = sub.add_parser("milestone")
    add_common(milestone)
    milestone.add_argument("--summary", required=True)
    milestone.add_argument("--validation", default="")
    milestone.add_argument("--debugger", default="")
    milestone.add_argument("--next-action", default="")
    milestone.add_argument("--screenshot", action="append", default=[])
    milestone.set_defaults(func=milestone_command)

    goal_contract = sub.add_parser("goal-contract")
    add_common(goal_contract)
    goal_contract.add_argument("--write", action="store_true")
    goal_contract.set_defaults(func=goal_contract_command)

    goal_prompt = sub.add_parser("goal-prompt")
    add_common(goal_prompt)
    goal_prompt.set_defaults(func=goal_prompt_command)

    quality = sub.add_parser("quality")
    add_common(quality)
    quality.add_argument("--validation-status", default="")
    quality.add_argument("--validation-summary", default="")
    quality.add_argument("--debugger-status", default="")
    quality.add_argument("--debugger-summary", default="")
    quality.add_argument("--residual-uncertainty", default="")
    quality.add_argument("--blocker", default="")
    quality.set_defaults(func=quality_command)

    result = sub.add_parser("iteration-result")
    add_common(result)
    result.add_argument("--success", action="store_true")
    result.add_argument("--summary", required=True)
    result.add_argument("--key-change", action="append", default=[])
    result.add_argument("--key-learning", action="append", default=[])
    result.add_argument("--validation", default="")
    result.add_argument("--debugger", default="")
    result.add_argument("--should-fully-stop", action="store_true")
    result.set_defaults(func=iteration_result_command)

    audit_gate = sub.add_parser("audit-gate")
    add_common(audit_gate)
    audit_gate.add_argument("--scope", default="")
    audit_gate.add_argument("--verdict", required=True, choices=["pass", "fail"])
    audit_gate.add_argument("--artifact", default="")
    audit_gate.add_argument("--reviewers", type=int, default=0)
    audit_gate.add_argument("--p0-blockers", type=int, default=0)
    audit_gate.add_argument("--p1-blockers", type=int, default=0)
    audit_gate.add_argument("--validation", default="")
    audit_gate.add_argument("--evidence", action="append", default=[])
    audit_gate.add_argument("--browser-evidence", action="append", default=[])
    audit_gate.add_argument("--residual-risk", default="")
    audit_gate.add_argument("--commit", default="")
    audit_gate.set_defaults(func=audit_gate_command)

    completion = sub.add_parser("completion-check")
    add_common(completion)
    completion.add_argument("--artifact", default="")
    completion.add_argument("--require", default="")
    completion.set_defaults(func=completion_check_command)

    learn = sub.add_parser("learn")
    add_common(learn)
    learn.add_argument("--source", required=True)
    learn.add_argument("--summary", required=True)
    learn.add_argument("--evidence", default="")
    learn.add_argument("--tag", action="append", default=[])
    learn.add_argument(
        "--lesson-type",
        default="candidate",
        choices=["one-off", "candidate", "reusable-detail", "stable-default"],
    )
    learn.add_argument("--priority", default="P2", choices=["P0", "P1", "P2", "P3"])
    learn.add_argument("--fingerprint", default="")
    learn.add_argument("--promote-candidate", action="store_true")
    learn.add_argument(
        "--scope",
        default="repo",
        choices=["repo", "project", "provider", "domain", "global", "run"],
    )
    learn.add_argument("--scope-key", default="")
    learn.add_argument("--conflicts-with", action="append", default=[])
    learn.set_defaults(func=learn_command)

    rollback = sub.add_parser("slice-rollback")
    add_common(rollback)
    rollback.set_defaults(func=slice_rollback_command)

    validate = sub.add_parser("validate")
    add_common(validate)
    validate.add_argument("--command", required=True)
    validate.add_argument("--timeout", type=int, default=120)
    validate.set_defaults(func=validate_command)

    context = sub.add_parser("context")
    add_common(context)
    context.set_defaults(func=context_command)

    stop = sub.add_parser("stop-decision")
    add_common(stop)
    stop.add_argument("--last-assistant-message", default="")
    stop.set_defaults(func=stop_decision_command)

    precompact = sub.add_parser("precompact")
    add_common(precompact)
    precompact.add_argument("--reason", default="")
    precompact.set_defaults(func=precompact_command)

    tool_use = sub.add_parser("tool-use")
    add_common(tool_use)
    tool_use.add_argument("--tool-name", required=True)
    tool_use.add_argument("--tool-input", default="")
    tool_use.add_argument("--tool-output", default="")
    tool_use.set_defaults(func=tool_use_command)

    recover = sub.add_parser("recover")
    add_common(recover)
    recover.set_defaults(func=recover_command)

    close = sub.add_parser("close")
    add_common(close)
    close.add_argument("--summary", default="")
    close.set_defaults(func=close_command)

    tokens_report = sub.add_parser("tokens-report")
    add_common(tokens_report)
    tokens_report.add_argument("--tokens", type=int, default=0, help="Tokens to report for this session")
    tokens_report.set_defaults(func=tokens_report_command)

    stats = sub.add_parser("session-stats")
    add_common(stats)
    stats.set_defaults(func=session_stats_command)

    exit_summary = sub.add_parser("exit-summary")
    add_common(exit_summary)
    exit_summary.add_argument("--summary", default="")
    exit_summary.set_defaults(func=exit_summary_command)

    brainkeeper = sub.add_parser("brainkeeper-export")
    add_common(brainkeeper)
    brainkeeper.add_argument("--write", action="store_true")
    brainkeeper.add_argument("--reason", default="")
    brainkeeper.add_argument("--recent-events", type=int, default=5)
    brainkeeper.set_defaults(func=brainkeeper_export_command)

    commit = sub.add_parser("commit-gate")
    add_common(commit)
    commit.add_argument("--validation-pass", action="store_true")
    commit.add_argument("--debugger-pass", action="store_true")
    commit.add_argument("--auto-commit", action="store_true")
    commit.add_argument("--message", default="")
    commit.add_argument("--owned-file", action="append", default=[])
    commit.set_defaults(func=commit_gate_command)

    gate_run = sub.add_parser("gate-run")
    add_common(gate_run)
    gate_run.add_argument("--check", action="append", default=[], help="Run only named checks (repeatable)")
    gate_run.add_argument("--timeout", type=int, default=120, help="Default timeout per check in seconds")
    gate_run.set_defaults(func=gate_run_command)

    return parser


def main(argv: Optional[list[str]] = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
