<!-- flywheel-report -->
## ✅ Flywheel: no regressions

Flywheel ran the agent on 22 test cases, 3 times each, and 6 times for the 2 close calls where more runs could change the answer, before and after this change, and compared the results case by case. Result: 2 moved by less than the noise threshold.

<details><summary>Wobbling: changed by less than the threshold (reported, not blocking) (2)</summary>

- `calc_two_step` {"agent":{"instruction":"You do arithmetic with the add and multiply tools, one call per step. When you have the final number, state it and stop calling tools.…
  - `check_answer_contains` 6/6 → 5/6, `check_answer_excludes` 6/6 → 5/6, `check_authors` 6/6 → 5/6, `check_files` 6/6 → 5/6, `check_finals_contain` 6/6 → 5/6, `check_http` 6/6 → 5/6, `check_no_error` 6/6 → 5/6, `check_run_metadata` 6/6 → 5/6, `check_service` 6/6 → 5/6, `check_state` 6/6 → 5/6, `check_streamed` 6/6 → 5/6, `check_structured` 6/6 → 5/6, `check_tool_args` 6/6 → 5/6, `check_tool_results` 6/6 → 5/6, `check_tools_called` 6/6 → 5/6, `check_workflow` 6/6 → 5/6
- `g5_sweep_run_after_disconnect_same_session` {"server":{"ops":[{"json":{},"method":"POST","path":"/apps/demo_app/users/u1/sessions/r1"},{"disconnect_after":1,"method":"POST","path":"/run_sse","session_id"…
  - `check_http` 6/6 → 5/6

</details>

### Totals

| Metric | Before | After |
|---|---|---|
| `check_answer_contains` | 72/72 | 71/72 |
| `check_answer_excludes` | 72/72 | 71/72 |
| `check_authors` | 72/72 | 71/72 |
| `check_files` | 72/72 | 71/72 |
| `check_finals_contain` | 72/72 | 71/72 |
| `check_http` | 72/72 | 70/72 |
| `check_no_error` | 72/72 | 71/72 |
| `check_run_metadata` | 72/72 | 71/72 |
| `check_service` | 72/72 | 71/72 |
| `check_state` | 72/72 | 71/72 |
| `check_streamed` | 72/72 | 71/72 |
| `check_structured` | 72/72 | 71/72 |
| `check_tool_args` | 72/72 | 71/72 |
| `check_tool_results` | 72/72 | 71/72 |
| `check_tools_called` | 72/72 | 71/72 |
| `check_workflow` | 72/72 | 71/72 |

<details><summary>Provenance</summary>

- Before: `base` at `539fec6`, local backend, dataset `ee0084e8f6fe`, 72 run(s)
- After: `head` at `539fec6`, local backend, dataset `ee0084e8f6fe`, 72 run(s)

</details>
