<!-- flywheel-report -->
## ✅ Flywheel: no regressions

Flywheel ran the agent on 21 test cases, 3 times each, and 6 times for the 2 close calls where more runs could change the answer, before and after this change, and compared the results case by case. Result: 2 moved by less than the noise threshold.

<details><summary>Wobbling: changed by less than the threshold (reported, not blocking) (2)</summary>

- `g4_sweep_streaming_two_turns_tools` {"agent":{"instruction":"Use the tools for all arithmetic.","tools":["add","multiply"]},"messages":["Add 20 and 22 with the add tool.","Multiply the previous r…
  - `check_finals_contain` 5/6 → 6/6
- `session_memory_two_turns` {"agent":{"instruction":"You keep notes for the user in session state with save_note and read them back with get_note.","tools":["save_note","get_note"]},"mess…
  - `check_finals_contain` 6/6 → 5/6

</details>

### Totals

| Metric | Before | After |
|---|---|---|
| `check_answer_contains` | 69/69 | 69/69 |
| `check_answer_excludes` | 69/69 | 69/69 |
| `check_authors` | 69/69 | 69/69 |
| `check_files` | 69/69 | 69/69 |
| `check_finals_contain` | 68/69 | 68/69 |
| `check_http` | 69/69 | 69/69 |
| `check_no_error` | 69/69 | 69/69 |
| `check_run_metadata` | 69/69 | 69/69 |
| `check_service` | 69/69 | 69/69 |
| `check_state` | 69/69 | 69/69 |
| `check_streamed` | 69/69 | 69/69 |
| `check_structured` | 69/69 | 69/69 |
| `check_tool_args` | 69/69 | 69/69 |
| `check_tool_results` | 69/69 | 69/69 |
| `check_tools_called` | 69/69 | 69/69 |
| `check_workflow` | 69/69 | 69/69 |

<details><summary>Provenance</summary>

- Before: `base` at `539fec6`, local backend, dataset `75d2d0e0bc69`, 69 run(s)
- After: `head` at `539fec6`, local backend, dataset `75d2d0e0bc69`, 69 run(s)

</details>
