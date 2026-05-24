#!/usr/bin/env python3
import json
import sys
from typing import Any

from runtime import current_runtime


def load_request() -> dict[str, Any]:
    try:
        data = json.load(sys.stdin)
    except Exception:
        return {}
    return data if isinstance(data, dict) else {}


def session_id_from(request: dict[str, Any]) -> str:
    for key in ("session_id", "sessionId", "conversation_id", "thread_id"):
        value = str(request.get(key, "")).strip()
        if value:
            return value
    return ""


def project_root_from(request: dict[str, Any]) -> str:
    for key in ("cwd", "project_root", "workspace", "workspace_dir"):
        value = str(request.get(key, "")).strip()
        if value:
            return value
    return ""


def event_name_from(request: dict[str, Any]) -> str:
    return str(request.get("hook_event_name", request.get("event", ""))).strip()


def output_context(event_name: str, message: str) -> dict[str, Any]:
    return {
        "continue": True,
        "hookSpecificOutput": {
            "hookEventName": event_name,
            "additionalContext": message,
        },
    }


def output_no_decision(event_name: str) -> dict[str, Any]:
    return {
        "hookSpecificOutput": {
            "hookEventName": event_name,
        },
    }


def handle_request(host: str, request: dict[str, Any]) -> dict[str, Any]:
    event_name = event_name_from(request)
    session_id = session_id_from(request)
    if not session_id:
        return {"continue": True}

    runtime = current_runtime(
        session_id=session_id,
        project_root=project_root_from(request) or None,
    )

    if event_name == "SessionStart":
        context = runtime.session_start(
            source=str(request.get("source", "")),
            host=host,
        )
        if context.get("action") == "inject_context" and context.get("message"):
            return output_context(event_name, str(context["message"]))
        return {"continue": True}

    if event_name == "UserPromptSubmit":
        context = runtime.context_for_user_prompt()
        if context.get("action") == "inject_context" and context.get("message"):
            return output_context(event_name, str(context["message"]))
        return {"continue": True}

    if event_name == "PreCompact":
        runtime.precompact(reason=f"{host} PreCompact hook")
        return {"continue": True}

    if event_name == "PostCompact":
        runtime.postcompact(reason=f"{host} PostCompact hook")
        return {"continue": True}

    if event_name == "PermissionRequest":
        runtime.record_permission_request(
            tool_name=str(request.get("tool_name", "")),
            tool_input=request.get("tool_input", {}),
            permission_mode=str(request.get("permission_mode", "")),
            reason=str(request.get("reason", "")),
        )
        return output_no_decision(event_name)

    if event_name in {"PostToolUse", "PreToolUse"}:
        runtime.record_tool_use(
            tool_name=str(request.get("tool_name", "")),
            tool_input=request.get("tool_input", {}),
            tool_output=request.get("tool_output", request.get("tool_response", {})),
        )
        return {"continue": True}

    if event_name == "Stop":
        decision = runtime.stop_decision(
            last_assistant_message=str(request.get("last_assistant_message", ""))
        )
        if decision.get("decision") == "block":
            return {
                "decision": "block",
                "reason": str(decision.get("reason", "")),
            }
        return {"continue": True}

    return {"continue": True}


def should_emit_response(host: str, response: dict[str, Any]) -> bool:
    # Codex/OpenCode displays hook stdout; keep no-op hook results silent.
    if host == "codex" and response == {"continue": True}:
        return False
    return True


def main(host: str) -> int:
    response = handle_request(host, load_request())
    if should_emit_response(host, response):
        print(json.dumps(response, ensure_ascii=False))
    return 0
