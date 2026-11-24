# Shell rules for every agent in this study

These are hard rules. Breaking one stalls the whole study.

- One simple command per shell call. Never use `&&`, `||`, `;`, `|`, `>` redirects, backticks,
  `$(...)`, heredocs, a trailing `&`, or `VAR=value command`.
- Never set an environment variable on the command line, in any form (`VAR=value command` and
  `env VAR=value command` both stall the study). Set it inside a Python script with `os.environ`
  and run the script. Never put anything that looks like a key or token on a command line.
- To run pytest against a source tree use the helper, which sets the import path and placeholder
  credentials itself:
  `<venv>/bin/python /home/user/flywheel/studies/change-probes/run_pytest_at.py <tree> <source root or .> <pytest args>`.
- Never write a file from the shell. Use the Write tool for new files and the Edit tool for changes.
- Anything longer than one plain command goes in a Python script that you create with the Write
  tool and run as `python3 /path/script.py` (or with a venv's own python).
- Stay inside the folders your brief names, plus `/tmp`. Never `cd` elsewhere; use absolute paths
  and `git -C <dir>`, `uv --directory <dir>`.
- Never run `claude`, never call a paid API, never use an API key from the environment.
- Never use `sudo`, never install system packages, never delete outside your own folder.
- If a command is refused or asks for permission, do not retry it. Find another way.
- Long commands: pass a timeout. Nothing may run longer than 10 minutes in one call.
