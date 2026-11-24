"""Find the change that introduced a reported bug, by proof.

Usage: python trace.py <case_dir> [--reps 3] [--timeout 180]
       python trace.py <case_dir> --at good|bad|<sha>     run the probe once at one commit

This is a thin shim over `flywheel.culprit` (the same as `flywheel culprit trace`); it puts the
repository's `src` folder on the import path so it runs without the package installed.
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent / "src"))
from flywheel.culprit import export_tree, git, trace_main  # noqa: E402,F401

if __name__ == "__main__":
    sys.exit(trace_main())
