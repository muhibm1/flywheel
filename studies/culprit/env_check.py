"""Check that a case's environment can import the project at both ends of its window.

Usage: python3 env_check.py <case_dir> <module> [<module> ...]

For the working version (`good`) and the broken version (`bad`) in case.json, the tree is written
to a scratch folder, the case's `source_roots` go on the import path, and each named module is
imported with the case's interpreter. Prints one line per version: OK, or FAIL with the error.
"""

from __future__ import annotations

import json
import shutil
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from trace import export_tree  # noqa: E402

SNIPPET = (
    "import importlib, sys\n"
    "roots, mods = sys.argv[1].split('|'), sys.argv[2:]\n"
    "sys.path[:0] = roots\n"
    "for m in mods:\n"
    "    importlib.import_module(m)\n"
    "print('imported', ', '.join(mods))\n"
)


def main() -> int:
    """Import the named modules at both ends and report."""
    case = Path(sys.argv[1]).resolve()
    mods = sys.argv[2:]
    cfg = json.loads((case / "case.json").read_text())
    failed = 0
    for end in ("good", "bad"):
        tree = case / "trees" / f"envcheck-{end}"
        export_tree(cfg["repo"], cfg[end], tree)
        roots = "|".join(str(tree / r) if r not in ("", ".") else str(tree) for r in cfg.get("source_roots") or ["."])
        try:
            p = subprocess.run([cfg["python"], "-c", SNIPPET, roots, *mods], cwd=tree, capture_output=True, text=True, timeout=300)
            ok, tail = p.returncode == 0, (p.stdout + p.stderr).strip()[-700:]
        except (OSError, subprocess.TimeoutExpired) as e:
            ok, tail = False, str(e)[-700:]
        shutil.rmtree(tree, ignore_errors=True)
        failed += not ok
        print(f"{end}: {'OK' if ok else 'FAIL'}\n{tail}")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
