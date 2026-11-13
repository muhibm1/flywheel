"""Finish check: a Claude Code hook that will not let a turn end on unchecked code.

When a turn edited code and no test, type check, lint or build ran after the last edit, or the
last one failed, the Stop hook blocks once and tells the agent to check its work. A second stop
in the same turn is let through, so the hook can never trap an agent in a loop.

It keeps its own small record per session from the PostToolUse and PostToolUseFailure events,
so it works even when the session writes no transcript (`claude -p --no-session-persistence`).

Install by adding the output of `flywheel finish-check --settings` to a settings file.
"""

from __future__ import annotations

import json
import os
import re
import tempfile
from pathlib import Path

# Commands that count as checking the work (the same list Auspex grades turns with).
CHECK_COMMAND = re.compile(
    "|".join(
        [
            r"\b(?:npm|pnpm|yarn|bun)\s+(?:run\s+)?(?:test|build|lint|check|typecheck|verify|ci)\b",
            r"\b(?:pytest|unittest|tox|nox|jest|vitest|mocha|ava|playwright|cypress)\b",
            r"\bnode\s+--test\b",
            r"\b(?:tsc|mypy|pyright|ruff|eslint|oxlint|flake8|pylint|shellcheck|golangci-lint|clippy)\b",
            r"\b(?:cargo|go|dotnet|swift|zig)\s+(?:test|build|check|vet|clippy)\b",
            r"\b(?:make|gradle|gradlew|mvn|bazel|ctest|cmake)\b",
            r"\b(?:dbt)\s+(?:build|test|run|compile|parse)\b",
            r"\bvite\s+build\b",
            r"\bclaude\s+plugin\s+validate\b",
            r"\bpython3?\s+-m\s+(?:pytest|unittest|compileall|py_compile)\b",
        ]
    ),
    re.I,
)

# Edits that need no check: prose, data, images and scratch files outside a project.
NO_CHECK_FILE = re.compile(
    r"\.(?:md|mdx|markdown|txt|rst|adoc|csv|tsv|png|jpe?g|gif|svg|webp|ico|pdf|lock|log)$", re.I
)
NO_CHECK_PLACE = re.compile(r"^/(?:tmp|private/tmp|var/folders)/|/scratchpad/|/\.claude/|/memory/")
EDIT_TOOLS = {"Edit", "Write", "MultiEdit", "NotebookEdit"}

REASON = (
    "You changed {files} and have not checked the change since your last edit{failed}. "
    "Run the project's tests (or its type check, lint or build if it has no tests) now, fix "
    "anything that fails, and then finish. If there is truly nothing that can check this "
    "change, say so in one line and finish."
)


def state_dir() -> Path:
    """Where the per-session records live."""
    return Path(os.environ.get("FINISH_CHECK_DIR") or Path(tempfile.gettempdir()) / "finish-check")


def is_code_edit(tool: str, tool_input: dict, cwd: str = "") -> str | None:
    """The file a tool call changed, when that change should be checked; otherwise None.

    A file inside the session's folder always counts; one outside it is skipped when it sits in
    a scratch place (a temporary folder, a scratchpad, the harness's own files).
    """
    if tool not in EDIT_TOOLS:
        return None
    path = str(tool_input.get("file_path") or tool_input.get("notebook_path") or "")
    if not path or NO_CHECK_FILE.search(path):
        return None
    inside = bool(cwd) and path.startswith(cwd.rstrip("/") + "/")
    if not inside and NO_CHECK_PLACE.search(path):
        return None
    return path


def is_check(tool: str, tool_input: dict) -> bool:
    """True when a tool call ran a test, type check, lint or build."""
    return tool == "Bash" and bool(CHECK_COMMAND.search(str(tool_input.get("command") or "")))


def verdict(steps: list[dict]) -> str | None:
    """Why the turn should not end yet, or None when it may."""
    edits = [i for i, s in enumerate(steps) if s["kind"] == "edit"]
    if not edits:
        return None
    after = [s for s in steps[edits[-1] + 1 :] if s["kind"] == "check"]
    if after and after[-1]["ok"]:
        return None
    files = sorted({steps[i]["file"] for i in edits})
    named = ", ".join(Path(f).name for f in files[:3]) + (" and others" if len(files) > 3 else "")
    failed = ", and your last check failed" if after else ""
    return REASON.format(files=named, failed=failed)


def handle(event: dict, folder: Path | None = None) -> dict | None:
    """Act on one hook event; returns the hook's JSON answer, or None for no answer."""
    folder = folder or state_dir()
    session = re.sub(r"[^\w.-]", "_", str(event.get("session_id") or "default"))
    record = folder / f"{session}.json"
    name = event.get("hook_event_name")
    steps: list[dict] = json.loads(record.read_text()) if record.exists() else []
    if name == "UserPromptSubmit":
        steps = []
    elif name in ("PostToolUse", "PostToolUseFailure"):
        tool, tool_input = event.get("tool_name", ""), event.get("tool_input") or {}
        path = is_code_edit(tool, tool_input, str(event.get("cwd") or ""))
        if path and name == "PostToolUse":
            steps.append({"kind": "edit", "file": path})
        elif is_check(tool, tool_input):
            steps.append({"kind": "check", "ok": name == "PostToolUse"})
        else:
            return None
    elif name == "Stop":
        reason = None if event.get("stop_hook_active") else verdict(steps)
        if reason:
            steps.append({"kind": "blocked"})
            folder.mkdir(parents=True, exist_ok=True)
            record.write_text(json.dumps(steps))
            return {"decision": "block", "reason": reason}
        record.unlink(missing_ok=True)
        return None
    else:
        return None
    folder.mkdir(parents=True, exist_ok=True)
    record.write_text(json.dumps(steps))
    return None


def settings(command: str = "flywheel finish-check") -> dict:
    """The hooks block that installs the finish check."""
    hook = [{"hooks": [{"type": "command", "command": command, "timeout": 10}]}]
    tools = [{"matcher": "*", "hooks": hook[0]["hooks"]}]
    return {
        "hooks": {
            "UserPromptSubmit": hook,
            "PostToolUse": tools,
            "PostToolUseFailure": tools,
            "Stop": hook,
        }
    }
