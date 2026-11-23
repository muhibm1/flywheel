<!-- flywheel-report -->
## ❌ Flywheel: this change is blocked

Flywheel ran the agent on 16 test cases, 3 times each, and 6 times for the 1 close call where more runs could change the answer, before and after this change, and compared the results case by case. Result: 8 cases that passed before now fail. Blocked because 8 cases broke (at most 0 allowed); and 8 cases raise an error it did not raise before.

### Broken: passed before, fail now

- `d-g4-edit-quotes-and-dollars` {"backend":"sandbox","files":{"env.sh":"export NAME=demo\nexport GREETING='hi'\n"},"system_prompt":"Your workspace is the folder {root}. Always use absolute pa…
  - `check_answer` 3/3 → 0/3, `check_exit` 3/3 → 0/3, `check_files` 3/3 → 0/3, `check_structured` 3/3 → 0/3, `check_tools` 3/3 → 0/3
  - new error: `KeyError: 'e'`
- `d-g4-write-heredoc-marker-text` {"backend":"sandbox","system_prompt":"Your workspace is the folder {root}. Always use absolute paths under it.","task":"Create the file {root}/script.sh with e…
  - `check_answer` 3/3 → 0/3, `check_exit` 3/3 → 0/3, `check_files` 3/3 → 0/3, `check_structured` 3/3 → 0/3, `check_tools` 3/3 → 0/3
  - new error: `KeyError: 'e'`
- `d-g4-write-large-file` {"backend":"sandbox","system_prompt":"Your workspace is the folder {root}. Always use absolute paths under it.","task":"Write a file {root}/ids.txt with 300 li…
  - `check_answer` 6/6 → 2/6, `check_exit` 6/6 → 2/6, `check_files` 6/6 → 2/6, `check_structured` 6/6 → 2/6, `check_tools` 6/6 → 2/6
  - new error: `KeyError: 'e'`
- `f-g4-unknown-tool` {"backend":"sandbox","fault":"unknown_tool","files":{"README.txt":"Release v1.2\nInstall v1.2 with pip.\nSee notes for v1.2.\n"},"system_prompt":"Your workspac…
  - `check_answer` 3/3 → 0/3, `check_exit` 3/3 → 0/3, `check_files` 3/3 → 0/3, `check_structured` 3/3 → 0/3, `check_tools` 3/3 → 0/3
  - new error: `KeyError: 'e'`
- `g4-sandbox-edit-replace-all` {"backend":"sandbox","files":{"README.txt":"Release v1.2\nInstall v1.2 with pip.\nSee notes for v1.2.\n"},"system_prompt":"Your workspace is the folder {root}.…
  - `check_answer` 3/3 → 0/3, `check_exit` 3/3 → 0/3, `check_files` 3/3 → 0/3, `check_structured` 3/3 → 0/3, `check_tools` 3/3 → 0/3
  - new error: `KeyError: 'e'`
- `g4-sandbox-edit-special-chars` {"backend":"sandbox","files":{"config.py":"import os\nname = 'old'\nport = 8000\n"},"system_prompt":"Your workspace is the folder {root}. Always use absolute p…
  - `check_answer` 3/3 → 0/3, `check_exit` 3/3 → 0/3, `check_files` 3/3 → 0/3, `check_structured` 3/3 → 0/3, `check_tools` 3/3 → 0/3
  - new error: `KeyError: 'e'`
- `g4-sandbox-write-many-lines` {"backend":"sandbox","system_prompt":"Your workspace is the folder {root}. Always use absolute paths under it.","task":"Write a file {root}/squares.csv with a …
  - `check_answer` 3/3 → 0/3, `check_exit` 3/3 → 0/3, `check_files` 3/3 → 0/3, `check_structured` 3/3 → 0/3, `check_tools` 3/3 → 0/3
  - new error: `KeyError: 'e'`
- `g4-sandbox-write-special-chars` {"backend":"sandbox","system_prompt":"Your workspace is the folder {root}. Always use absolute paths under it.","task":"Create the file {root}/deploy.sh with e…
  - `check_answer` 3/3 → 0/3, `check_exit` 3/3 → 0/3, `check_files` 3/3 → 0/3, `check_structured` 3/3 → 0/3, `check_tools` 3/3 → 0/3
  - new error: `KeyError: 'e'`

### Totals

| Metric | Before | After |
|---|---|---|
| `check_answer` | 51/51 | 26/51 |
| `check_exit` | 51/51 | 26/51 |
| `check_files` | 51/51 | 26/51 |
| `check_structured` | 51/51 | 26/51 |
| `check_tools` | 51/51 | 26/51 |

Sign test over broken and fixed cases: p = 0.00781 (the chance of a split at least this uneven if the change did nothing).

<details><summary>Provenance</summary>

- Before: `base` at `539fec6`, local backend, dataset `8148678a2f2f`, 51 run(s)
- After: `head` at `539fec6`, local backend, dataset `8148678a2f2f`, 51 run(s)

</details>
