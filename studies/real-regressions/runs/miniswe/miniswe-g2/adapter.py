"""Flywheel adapter for mini-swe-agent.

Builds the agent the way the Python-bindings docs and the `mini` run script do (a config yaml
from the package, `get_model`, `get_environment`, `get_agent`), points the model at the local
OpenAI-compatible endpoint through LiteLLM, and runs one task in a fresh temp folder with the
local environment (never docker).

Inputs:
  task          the task text given to `agent.run`
  files         {relative path: content} written into the work folder before the run
  config        builtin config name (default "mini"; e.g. "mini_textbased")
  agent_class   "default" (python bindings) or "interactive" (the `mini` CLI agent, run in yolo
                mode with confirm_exit off, as `mini -y --exit-immediately`)
  step_limit    model calls allowed (default 30)
  agent_extra   extra agent config keys merged last
  env_extra     extra environment config keys merged last
  verify        shell command the harness runs in the work folder after the agent finishes
"""

import os
import subprocess
import tempfile
from pathlib import Path

os.environ.setdefault("MSWEA_SILENT_STARTUP", "1")
os.environ.setdefault("MSWEA_GLOBAL_CONFIG_DIR", tempfile.mkdtemp(prefix="mswea-cfg-"))
os.environ.setdefault("MSWEA_COST_TRACKING", "ignore_errors")

import json  # noqa: E402

from minisweagent.agents import get_agent  # noqa: E402
from minisweagent.config import get_config_from_spec  # noqa: E402
from minisweagent.environments import get_environment  # noqa: E402
from minisweagent.models import get_model  # noqa: E402
from minisweagent.utils.serialize import recursive_merge  # noqa: E402

API_BASE = "http://127.0.0.1:8765/v1"
MODEL_NAME = "openai/claude-haiku-4-5"
RUN_TIMEOUT_S = 300
MAX_FILE_BYTES = 50_000


def _snapshot(root: Path) -> dict[str, str]:
    """Every small text file under root, by relative path."""
    files = {}
    for path in sorted(root.rglob("*")):
        if not path.is_file() or "__pycache__" in path.parts or path.name.endswith(".traj.json"):
            continue
        if any(part.startswith(".") for part in path.relative_to(root).parts):
            continue
        try:
            if path.stat().st_size > MAX_FILE_BYTES:
                continue
            files[str(path.relative_to(root))] = path.read_text(encoding="utf-8")
        except (UnicodeDecodeError, OSError):
            continue
    return files


def target(inputs: dict) -> dict:
    """Run mini-swe-agent on one task in its own temp folder and report what happened."""
    run_root = Path(tempfile.mkdtemp(prefix="mswea-run-"))
    work = run_root / "work"
    work.mkdir()
    for rel, content in (inputs.get("files") or {}).items():
        dest = work / rel
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_text(content, encoding="utf-8")
    traj_path = run_root / "run.traj.json"

    base = get_config_from_spec(inputs.get("config", "mini"))
    agent_class = inputs.get("agent_class", "default")
    agent_cfg = {
        "agent_class": agent_class,
        "step_limit": int(inputs.get("step_limit", 30)),
        "cost_limit": 0.0,
        "wall_time_limit_seconds": RUN_TIMEOUT_S,
        "output_path": traj_path,
    }
    if agent_class == "interactive":
        agent_cfg |= {"mode": "yolo", "confirm_exit": False}
    config = recursive_merge(
        base,
        {
            "agent": agent_cfg,
            "environment": {"environment_class": "local", "cwd": str(work), "timeout": 30},
            "model": {
                "model_name": MODEL_NAME,
                "cost_tracking": "ignore_errors",
                "model_kwargs": {"api_base": API_BASE, "api_key": "sk-local"},
            },
        },
        {"agent": inputs.get("agent_extra") or {}, "environment": inputs.get("env_extra") or {}},
    )
    # The work folder is the agent's only place; keep the yaml's own env vars.
    model = get_model(config=config.get("model", {}))
    env = get_environment(config.get("environment", {}), default_type="local")
    agent = get_agent(model, env, config.get("agent", {}), default_type="default")

    # The model is not told where it is otherwise; every command already runs in `work`.
    task = f"{inputs['task']}\n\nYour working directory is {work}; all files for this task are there."
    result = agent.run(task)

    commands, format_errors = [], 0
    for msg in agent.messages:
        extra = msg.get("extra") or {}
        if msg.get("role") == "assistant":
            commands += [a.get("command", "") for a in extra.get("actions", [])]
        if extra.get("interrupt_type") == "FormatError":
            format_errors += 1

    traj = None
    if traj_path.exists():
        try:
            traj = json.loads(traj_path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            traj = {"_unparseable": True}

    verify = None
    if inputs.get("verify"):
        proc = subprocess.run(
            inputs["verify"], shell=True, cwd=work, capture_output=True, text=True, timeout=60
        )
        verify = {"stdout": proc.stdout, "stderr": proc.stderr[-2000:], "returncode": proc.returncode}

    return {
        "exit_status": result.get("exit_status"),
        "submission": result.get("submission", ""),
        "n_calls": agent.n_calls,
        "commands": commands,
        "format_errors": format_errors,
        "last_message_role": agent.messages[-1].get("role") if agent.messages else None,
        "files": _snapshot(work),
        "verify": verify,
        "trajectory": {
            "exists": traj is not None,
            "format": (traj or {}).get("trajectory_format"),
            "exit_status": ((traj or {}).get("info") or {}).get("exit_status"),
            "api_calls": (((traj or {}).get("info") or {}).get("model_stats") or {}).get("api_calls"),
            "n_messages": len((traj or {}).get("messages") or []),
        },
    }


# ---------------------------------------------------------------- checks
# Each check returns True when the case's reference does not ask for it.


def check_exit_status(inputs, outputs, reference_outputs) -> bool:
    """The run ended with the expected exit status (Submitted unless the case says otherwise)."""
    return outputs.get("exit_status") == reference_outputs.get("exit_status", "Submitted")


def check_verify(inputs, outputs, reference_outputs) -> bool:
    """The harness's verification command, run after the agent, gave the expected result."""
    want = reference_outputs.get("verify")
    if want is None:
        return True
    got = outputs.get("verify") or {}
    if "returncode" in want and got.get("returncode") != want["returncode"]:
        return False
    if "stdout" in want and (got.get("stdout") or "").strip() != want["stdout"].strip():
        return False
    for sub in want.get("stdout_contains", []):
        if sub not in (got.get("stdout") or ""):
            return False
    return True


def check_files(inputs, outputs, reference_outputs) -> bool:
    """Expected files exist with the expected content; protected files are unchanged."""
    files = outputs.get("files") or {}
    for rel, subs in (reference_outputs.get("files_contain") or {}).items():
        if rel not in files or any(s not in files[rel] for s in subs):
            return False
    for rel in reference_outputs.get("files_absent") or []:
        if rel in files:
            return False
    for rel in reference_outputs.get("unchanged") or []:
        if files.get(rel) != (inputs.get("files") or {}).get(rel):
            return False
    return True


def check_trajectory(inputs, outputs, reference_outputs) -> bool:
    """The trajectory was saved, parses, and agrees with the run's exit status and call count."""
    t = outputs.get("trajectory") or {}
    return (
        bool(t.get("exists"))
        and bool(t.get("format"))
        and t.get("exit_status") == outputs.get("exit_status")
        and t.get("api_calls") == outputs.get("n_calls")
        and t.get("n_messages", 0) >= 3
        and outputs.get("last_message_role") == "exit"
    )


def check_limits(inputs, outputs, reference_outputs) -> bool:
    """The run made no more model calls than the case allows."""
    limit = reference_outputs.get("max_calls", inputs.get("step_limit", 30))
    return 0 < (outputs.get("n_calls") or 0) <= limit
