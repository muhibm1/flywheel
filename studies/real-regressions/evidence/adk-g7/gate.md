<!-- flywheel-report -->
## ✅ Flywheel: no regressions

Flywheel ran the agent on 22 test cases, 3 times each, and 6 times for the 2 close calls where more runs could change the answer, before and after this change, and compared the results case by case. Result: 2 moved by less than the noise threshold.

<details><summary>Wobbling: changed by less than the threshold (reported, not blocking) (2)</summary>

- `calc_two_step` {"agent":{"instruction":"You do arithmetic with the add and multiply tools, one call per step. When you have the final number, state it and stop calling tools.…
  - `check_answer_contains` 4/6 → 6/6, `check_answer_excludes` 4/6 → 6/6, `check_authors` 4/6 → 6/6, `check_files` 4/6 → 6/6, `check_finals_contain` 4/6 → 6/6, `check_http` 4/6 → 6/6, `check_live_direct` 4/6 → 6/6, `check_no_error` 4/6 → 6/6, `check_run_metadata` 4/6 → 6/6, `check_service` 4/6 → 6/6, `check_state` 4/6 → 6/6, `check_streamed` 4/6 → 6/6, `check_structured` 4/6 → 6/6, `check_tool_args` 4/6 → 6/6, `check_tool_results` 4/6 → 6/6, `check_tools_called` 4/6 → 6/6, `check_workflow` 4/6 → 6/6
- `g7_sweep_seeded_history_blocked_tool` {"agent":{"callbacks":["before_tool_block_delete"],"instruction":"You manage records. Use delete_record when asked to delete. If the tool says it is not allowe…
  - `check_answer_contains` 5/6 → 6/6

</details>

### Totals

| Metric | Before | After |
|---|---|---|
| `check_answer_contains` | 69/72 | 72/72 |
| `check_answer_excludes` | 70/72 | 72/72 |
| `check_authors` | 70/72 | 72/72 |
| `check_files` | 70/72 | 72/72 |
| `check_finals_contain` | 70/72 | 72/72 |
| `check_http` | 70/72 | 72/72 |
| `check_live_direct` | 70/72 | 72/72 |
| `check_no_error` | 70/72 | 72/72 |
| `check_run_metadata` | 70/72 | 72/72 |
| `check_service` | 70/72 | 72/72 |
| `check_state` | 70/72 | 72/72 |
| `check_streamed` | 70/72 | 72/72 |
| `check_structured` | 70/72 | 72/72 |
| `check_tool_args` | 70/72 | 72/72 |
| `check_tool_results` | 70/72 | 72/72 |
| `check_tools_called` | 70/72 | 72/72 |
| `check_workflow` | 70/72 | 72/72 |

<details><summary>Provenance</summary>

- Before: `base` at `539fec6`, local backend, dataset `cf262828886a`, 72 run(s)
- After: `head` at `539fec6`, local backend, dataset `cf262828886a`, 72 run(s)

</details>
