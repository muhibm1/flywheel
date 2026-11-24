"""Score culprit cases against the sealed key.

Usage: python score.py <key.json> <SET> <cases_dir> [--answers <file>] [--out <file>]

This is a thin shim over `flywheel.culprit` (the same as `flywheel culprit score`); it puts the
repository's `src` folder on the import path so it runs without the package installed.
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent / "src"))
from flywheel.culprit import score_main  # noqa: E402

if __name__ == "__main__":
    sys.exit(score_main())
