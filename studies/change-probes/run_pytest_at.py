"""Run pytest against one source tree without any environment set on the command line.

Usage: <venv>/bin/python run_pytest_at.py <tree> <source_root_relative_to_tree or .> <pytest args...>

Puts the tree's source root first on the import path, changes into the tree, sets harmless
placeholder credentials so imports that only check for their presence do not fail, switches
tracing off, and calls pytest. Exit code is pytest's.
"""

import os
import sys


def main() -> int:
    tree = os.path.abspath(sys.argv[1])
    src = os.path.normpath(os.path.join(tree, sys.argv[2]))
    args = sys.argv[3:]
    for name in list(os.environ):
        up = name.upper()
        if any(t in up for t in ("API_KEY", "TOKEN", "SECRET", "LANGSMITH", "LANGCHAIN_", "ANTHROPIC", "OPENAI")):
            os.environ.pop(name)
    os.environ["OPENAI_API_KEY"] = "placeholder-not-a-key"
    os.environ["ANTHROPIC_API_KEY"] = "placeholder-not-a-key"
    os.environ["LANGSMITH_TRACING"] = "false"
    os.environ["LANGCHAIN_TRACING_V2"] = "false"
    os.environ["PYTHONPATH"] = src
    os.environ["PYTHONDONTWRITEBYTECODE"] = "1"
    sys.path.insert(0, src)
    os.chdir(tree)
    import pytest

    return int(pytest.main(["--rootdir", tree, "-p", "no:cacheprovider", *args]))


if __name__ == "__main__":
    sys.exit(main())
