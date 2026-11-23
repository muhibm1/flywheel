# Shell rules for every agent in this study

These are hard rules. Breaking one stalls the whole study.

- One simple command per shell call. Never use `&&`, `||`, `;`, `|`, `>` redirects, backticks,
  `$(...)`, heredocs, a trailing `&`, or `VAR=value command`.
- To set an environment variable for a command, use `env VAR=value command ...`, or put the logic
  in a Python script.
- Never write a file from the shell. Use the Write tool for new files and the Edit tool for changes.
- Anything longer than one plain command goes in a Python script that you create with the Write
  tool and run as `python3 /path/script.py` (or with a venv's own python).
- Stay inside the folders your brief names, plus `/tmp`. Never `cd` elsewhere; use absolute paths
  and `git -C <dir>`, `uv --directory <dir>`.
- Never run `claude`, never call a paid API, never use an API key from the environment.
- Never use `sudo`, never install system packages, never delete outside your own folder.
- If a command is refused or asks for permission, do not retry it. Find another way.
- Long commands: pass a timeout. Nothing may run longer than 10 minutes in one call.
