<!-- flywheel-report -->
## ✅ Flywheel: no regressions

Flywheel ran the agent on 19 test cases, 3 times each, and 6 times for the 1 close call where more runs could change the answer, before and after this change, and compared the results case by case. Result: 1 moved by less than the noise threshold.

<details><summary>Wobbling: changed by less than the threshold (reported, not blocking) (1)</summary>

- `calc_two_step` {"agent":{"instruction":"You do arithmetic with the add and multiply tools, one call per step. When you have the final number, state it and stop calling tools.…
  - `check_answer_contains` 6/6 → 5/6, `check_answer_excludes` 6/6 → 5/6, `check_authors` 6/6 → 5/6, `check_files` 6/6 → 5/6, `check_finals_contain` 6/6 → 5/6, `check_http` 6/6 → 5/6, `check_no_error` 6/6 → 5/6, `check_run_metadata` 6/6 → 5/6, `check_service` 6/6 → 5/6, `check_state` 6/6 → 5/6, `check_streamed` 6/6 → 5/6, `check_structured` 6/6 → 5/6, `check_tool_args` 6/6 → 5/6, `check_tool_results` 6/6 → 5/6, `check_tools_called` 6/6 → 5/6, `check_workflow` 6/6 → 5/6

</details>

### Totals

| Metric | Before | After |
|---|---|---|
| `check_answer_contains` | 60/60 | 59/60 |
| `check_answer_excludes` | 60/60 | 59/60 |
| `check_authors` | 60/60 | 59/60 |
| `check_files` | 60/60 | 59/60 |
| `check_finals_contain` | 60/60 | 59/60 |
| `check_http` | 60/60 | 59/60 |
| `check_no_error` | 60/60 | 59/60 |
| `check_run_metadata` | 60/60 | 59/60 |
| `check_service` | 60/60 | 59/60 |
| `check_state` | 60/60 | 59/60 |
| `check_streamed` | 60/60 | 59/60 |
| `check_structured` | 60/60 | 59/60 |
| `check_tool_args` | 60/60 | 59/60 |
| `check_tool_results` | 60/60 | 59/60 |
| `check_tools_called` | 60/60 | 59/60 |
| `check_workflow` | 60/60 | 59/60 |

<details><summary>Provenance</summary>

- Before: `base` at `539fec6`, local backend, dataset `fe0cda40ee76`, 60 run(s)
- After: `head` at `539fec6`, local backend, dataset `fe0cda40ee76`, 60 run(s)

</details>
