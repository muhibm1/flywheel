"""Shim: load the shared suite adapter (../suite/adapter.py) and re-export it."""

import importlib.util
import sys
from pathlib import Path

_PATH = Path(__file__).resolve().parent.parent / "suite" / "adapter.py"
_spec = importlib.util.spec_from_file_location("autogen_suite_adapter", _PATH)
_module = importlib.util.module_from_spec(_spec)
sys.modules["autogen_suite_adapter"] = _module
_spec.loader.exec_module(_module)

target = _module.target
check_answer = _module.check_answer
check_tools = _module.check_tools
check_files = _module.check_files
check_json = _module.check_json
check_flow = _module.check_flow
