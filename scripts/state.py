#!/usr/bin/env python3
import hashlib
import json
import os
import re
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional


SKILL_NAME = "nsr"
SKILL_VERSION = "0.8.3"
STATE_SCHEMA_VERSION = 5
MODE_VALUES = {"disabled", "active"}
EXECUTION_MODE_VALUES = {"hands-off", "companion"}
COMMIT_POLICY_VALUES = {"auto", "manual", "disabled"}
LOOP_STATUS_VALUES = {"idle", "running", "blocked", "complete"}


def now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def clean_string(value: object) -> str:
    return str(value).strip() if value is not None else ""


def clean_list(values: object) -> list[str]:
    if not isinstance(values, list):
        return []
    return [clean_string(value) for value in values if clean_string(value)]


def real_home() -> Path:
    home = Path(os.environ.get("HOME", str(Path.home()))).expanduser()
    match = re.match(r"^(/(?:Users|home)/[^/]+)/\.config/mms/", str(home))
    if match:
        return Path(match.group(1))
    return home


def nsr_root() -> Path:
    value = clean_string(os.environ.get("NSR_HOME", os.environ.get("LOOOP_HOME", "")))
    if value:
        return Path(value).expanduser().resolve()
    return (real_home() / ".nsr").resolve()


def sessions_root() -> Path:
    return nsr_root() / "sessions"


def global_learnings_path() -> Path:
    return nsr_root() / "learnings" / "global.jsonl"


def default_project_root(project_root: Optional[str]) -> str:
    if project_root:
        return str(Path(project_root).expanduser().resolve())
    project_dir = clean_string(os.environ.get("CLAUDE_PROJECT_DIR", ""))
    if project_dir:
        return str(Path(project_dir).expanduser().resolve())
    return str(Path.cwd().resolve())


def default_session_id(project_root: str) -> str:
    for key in ("NSR_SESSION_ID", "CODEX_THREAD_ID", "CLAUDE_SESSION_ID"):
        value = clean_string(os.environ.get(key, ""))
        if value:
            return value
    digest = hashlib.sha1(project_root.encode("utf-8")).hexdigest()[:12]
    return f"local-{digest}"


@dataclass
class SessionIdentity:
    session_id: str
    session_dir: Path
    state_path: Path
    source: str


def resolve_identity(
    session_id: Optional[str] = None,
    path: Optional[str] = None,
    project_root: Optional[str] = None,
) -> SessionIdentity:
    if path:
        resolved = Path(path).expanduser().resolve()
        if resolved.suffix == ".json":
            session_dir = resolved.parent
            state_path = resolved
        else:
            session_dir = resolved
            state_path = resolved / "state.json"
        return SessionIdentity(
            session_id=session_id or session_dir.name,
            session_dir=session_dir,
            state_path=state_path,
            source="explicit_path",
        )

    root = default_project_root(project_root)
    chosen = session_id or default_session_id(root)
    session_dir = (sessions_root() / chosen).resolve()
    return SessionIdentity(
        session_id=chosen,
        session_dir=session_dir,
        state_path=session_dir / "state.json",
        source="explicit_session_id" if session_id else "environment_or_project",
    )


def default_state(session_id: str, project_root: str) -> dict[str, Any]:
    timestamp = now_iso()
    return {
        "runtime": {
            "schema_version": STATE_SCHEMA_VERSION,
            "skill": SKILL_NAME,
            "skill_version": SKILL_VERSION,
            "session_id": session_id,
            "mode": "disabled",
            "project_root": project_root,
            "created_at": timestamp,
            "updated_at": timestamp,
        },
        "goal": {
            "objective": "",
            "target_phase": "",
            "done_when": "",
            "owner_agent": "",
            "role": "",
            "profile_slot": "",
            "profile_alias": "",
            "profile_skill": "",
            "profile_description": "",
            "execution_mode": "hands-off",
            "ask_policy": [
                "Ask only for irreversible, external, cost, credential, or genuinely blocked decisions."
            ],
            "commit_policy": "auto",
            "max_iterations": 20,
            "confirmed": False,
        },
        "loop": {
            "status": "idle",
            "iteration": 0,
            "current_slice_id": "",
            "current_slice": "",
            "next_action": "",
            "stop_condition": "",
            "dirty_baseline": [],
            "dirty_current": [],
            "touched_files": [],
            "owned_files": [],
            "last_result": {
                "success": False,
                "summary": "",
                "key_changes_made": [],
                "key_learnings": [],
                "validation": "",
                "debugger": "",
                "should_fully_stop": False,
            },
            "cost": {
                "total_tokens": 0,
                "total_cost_usd": 0.0,
                "max_tokens": 0,
                "max_cost_usd": 0.0,
            },
        },
        "quality": {
            "validation_status": "unknown",
            "validation_summary": "",
            "debugger_status": "unknown",
            "debugger_summary": "",
            "residual_uncertainty": "",
            "blocker": "",
        },
        "gate": {
            "kind": "",
            "scope": "",
            "quorum": 0,
            "status": "not_required",
            "artifact": "",
            "summary": "",
            "checked_at": "",
            "reasons": [],
            "evidence": [],
            "checks": {},
        },
        "trace": {
            "latest_event": "",
            "latest_milestone": "",
            "latest_commit": "",
            "latest_exit_summary": "",
            "latest_learning": "",
            "event_count": 0,
        },
    }


def normalize_state(state: dict[str, Any]) -> dict[str, Any]:
    runtime = state.get("runtime") if isinstance(state.get("runtime"), dict) else {}
    goal = state.get("goal") if isinstance(state.get("goal"), dict) else {}
    loop = state.get("loop") if isinstance(state.get("loop"), dict) else {}
    quality = state.get("quality") if isinstance(state.get("quality"), dict) else {}
    gate = state.get("gate") if isinstance(state.get("gate"), dict) else {}
    trace = state.get("trace") if isinstance(state.get("trace"), dict) else {}

    base = default_state(
        clean_string(runtime.get("session_id", "")) or "unknown",
        clean_string(runtime.get("project_root", "")) or default_project_root(None),
    )
    base["runtime"].update(
        {
            "schema_version": STATE_SCHEMA_VERSION,
            "skill": SKILL_NAME,
            "skill_version": SKILL_VERSION,
            "mode": clean_string(runtime.get("mode", "disabled")).lower(),
            "created_at": clean_string(runtime.get("created_at", "")) or now_iso(),
            "updated_at": clean_string(runtime.get("updated_at", "")) or now_iso(),
        }
    )
    if base["runtime"]["mode"] not in MODE_VALUES:
        base["runtime"]["mode"] = "disabled"

    base["goal"].update(
        {
            "objective": clean_string(goal.get("objective", "")),
            "target_phase": clean_string(goal.get("target_phase", "")),
            "done_when": clean_string(goal.get("done_when", "")),
            "owner_agent": clean_string(goal.get("owner_agent", "")),
            "role": clean_string(goal.get("role", "")),
            "profile_slot": clean_string(goal.get("profile_slot", "")),
            "profile_alias": clean_string(goal.get("profile_alias", "")),
            "profile_skill": clean_string(goal.get("profile_skill", "")),
            "profile_description": clean_string(goal.get("profile_description", "")),
            "execution_mode": clean_string(
                goal.get("execution_mode", "hands-off")
            ).lower(),
            "ask_policy": clean_list(goal.get("ask_policy"))
            or base["goal"]["ask_policy"],
            "commit_policy": clean_string(goal.get("commit_policy", "auto")).lower(),
            "max_iterations": int(goal.get("max_iterations", 20) or 20),
            "confirmed": bool(goal.get("confirmed", False)),
        }
    )
    if base["goal"]["commit_policy"] not in COMMIT_POLICY_VALUES:
        base["goal"]["commit_policy"] = "auto"
    if base["goal"]["execution_mode"] not in EXECUTION_MODE_VALUES:
        base["goal"]["execution_mode"] = "hands-off"

    last_result = (
        loop.get("last_result") if isinstance(loop.get("last_result"), dict) else {}
    )
    base["loop"].update(
        {
            "status": clean_string(loop.get("status", "idle")).lower(),
            "iteration": int(loop.get("iteration", 0) or 0),
            "current_slice_id": clean_string(loop.get("current_slice_id", "")),
            "current_slice": clean_string(loop.get("current_slice", "")),
            "next_action": clean_string(loop.get("next_action", "")),
            "stop_condition": clean_string(loop.get("stop_condition", "")),
            "dirty_baseline": clean_list(loop.get("dirty_baseline")),
            "dirty_current": clean_list(loop.get("dirty_current")),
            "touched_files": clean_list(loop.get("touched_files")),
            "owned_files": clean_list(loop.get("owned_files")),
            "last_result": {
                "success": bool(last_result.get("success", False)),
                "summary": clean_string(last_result.get("summary", "")),
                "key_changes_made": clean_list(last_result.get("key_changes_made")),
                "key_learnings": clean_list(last_result.get("key_learnings")),
                "validation": clean_string(last_result.get("validation", "")),
                "debugger": clean_string(last_result.get("debugger", "")),
                "should_fully_stop": bool(
                    last_result.get("should_fully_stop", False)
                ),
            },
        }
    )
    if base["loop"]["status"] not in LOOP_STATUS_VALUES:
        base["loop"]["status"] = "idle"

    for key in base["quality"]:
        base["quality"][key] = clean_string(quality.get(key, ""))
    base["gate"].update(
        {
            "kind": clean_string(gate.get("kind", "")).lower(),
            "scope": clean_string(gate.get("scope", "")),
            "quorum": int(gate.get("quorum", 0) or 0),
            "status": clean_string(gate.get("status", "not_required")).lower()
            or "not_required",
            "artifact": clean_string(gate.get("artifact", "")),
            "summary": clean_string(gate.get("summary", "")),
            "checked_at": clean_string(gate.get("checked_at", "")),
            "reasons": clean_list(gate.get("reasons")),
            "evidence": clean_list(gate.get("evidence")),
        }
    )
    if base["gate"]["status"] not in {"not_required", "pending", "pass", "fail"}:
        base["gate"]["status"] = "pending" if base["gate"]["kind"] else "not_required"
    for key in base["trace"]:
        if key == "event_count":
            base["trace"][key] = int(trace.get(key, 0) or 0)
        else:
            base["trace"][key] = clean_string(trace.get(key, ""))
    return base


def load_state(identity: SessionIdentity) -> Optional[dict[str, Any]]:
    if not identity.state_path.is_file():
        return None
    data = json.loads(identity.state_path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError("state file must contain a JSON object")
    return normalize_state(data)


def save_state(identity: SessionIdentity, state: dict[str, Any]) -> None:
    state["runtime"]["updated_at"] = now_iso()
    identity.session_dir.mkdir(parents=True, exist_ok=True)
    identity.state_path.write_text(
        json.dumps(normalize_state(state), ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )


def append_jsonl(path: Path, entry: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as f:
        f.write(json.dumps(entry, ensure_ascii=False, sort_keys=True) + "\n")
