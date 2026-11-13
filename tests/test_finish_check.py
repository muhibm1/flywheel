"""Tests for the finish-check hook."""

import json
import subprocess
import sys
from pathlib import Path

import flywheel
from flywheel import finish_check


def ev(name: str, **kw) -> dict:
    """A hook event for one session."""
    return {"hook_event_name": name, "session_id": "s1", **kw}


def edit(path: str = "/repo/src/app.py") -> dict:
    """An edit that succeeded."""
    return ev("PostToolUse", tool_name="Edit", tool_input={"file_path": path})


def bash(command: str, ok: bool = True) -> dict:
    """A shell command that passed or failed."""
    name = "PostToolUse" if ok else "PostToolUseFailure"
    return ev(name, tool_name="Bash", tool_input={"command": command})


def play(tmp_path, *events) -> dict | None:
    """Feed the events in order; return the answer to the last one."""
    answer = None
    for e in events:
        answer = finish_check.handle(e, tmp_path)
    return answer


def test_unchecked_edit_is_blocked_once(tmp_path):
    answer = play(tmp_path, ev("UserPromptSubmit"), edit(), ev("Stop"))
    assert answer["decision"] == "block" and "app.py" in answer["reason"]
    assert play(tmp_path, ev("Stop", stop_hook_active=True)) is None


def test_passing_check_after_the_last_edit_lets_it_finish(tmp_path):
    assert play(tmp_path, edit(), bash("python -m pytest -q"), ev("Stop")) is None


def test_check_before_the_last_edit_does_not_count(tmp_path):
    answer = play(tmp_path, edit(), bash("pytest"), edit("/repo/src/b.py"), ev("Stop"))
    assert answer["decision"] == "block"


def test_failing_last_check_is_blocked(tmp_path):
    answer = play(tmp_path, edit(), bash("npm test", ok=False), ev("Stop"))
    assert answer["decision"] == "block" and "failed" in answer["reason"]


def test_prose_scratch_and_failed_edits_need_no_check(tmp_path):
    events = [
        edit("/repo/README.md"),
        edit("/tmp/notes.py"),
        ev("PostToolUseFailure", tool_name="Edit", tool_input={"file_path": "/repo/x.py"}),
        bash("ls -la"),
        ev("Stop"),
    ]
    assert play(tmp_path, *events) is None


def test_a_temporary_project_folder_still_counts(tmp_path):
    inside = edit("/tmp/work/src/app.py") | {"cwd": "/tmp/work"}
    assert play(tmp_path, inside, ev("Stop"))["decision"] == "block"


def test_a_new_prompt_starts_a_new_turn(tmp_path):
    play(tmp_path, edit(), ev("Stop"), ev("Stop", stop_hook_active=True))
    assert play(tmp_path, ev("UserPromptSubmit"), bash("echo hi"), ev("Stop")) is None


def test_command_line_answers_on_stdout_and_never_fails(tmp_path):
    src = str(Path(flywheel.__file__).parents[1])
    env = {"FINISH_CHECK_DIR": str(tmp_path), "PATH": "/usr/bin:/bin", "PYTHONPATH": src}
    run = [sys.executable, "-m", "flywheel", "finish-check"]
    for e in (edit(), ev("Stop")):
        done = subprocess.run(run, input=json.dumps(e), capture_output=True, text=True, env=env)
    assert done.returncode == 0 and json.loads(done.stdout)["decision"] == "block"
    bad = subprocess.run(run, input="not json", capture_output=True, text=True, env=env)
    assert bad.returncode == 0 and bad.stdout == ""


def test_settings_block_installs_every_event():
    hooks = finish_check.settings("x")["hooks"]
    assert set(hooks) == {"UserPromptSubmit", "PostToolUse", "PostToolUseFailure", "Stop"}
