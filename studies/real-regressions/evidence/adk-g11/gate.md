<!-- flywheel-report -->
## ✅ Flywheel: no regressions

Flywheel ran the agent on 22 test cases, 3 times each, and 6 times for the 1 close call where more runs could change the answer, before and after this change, and compared the results case by case. Result: 1 moved by less than the noise threshold.

<details><summary>Wobbling: changed by less than the threshold (reported, not blocking) (1)</summary>

- `g11_resumable_multi_step_tools` {"agent":{"instruction":"You do arithmetic. Use the tools for every step.","tools":["add","multiply"]},"messages":["What is (6 + 8) * 3? Use the tools."],"resu…
  - `check_answer_excludes` 5/6 → 6/6, `check_authors` 5/6 → 6/6, `check_files` 5/6 → 6/6, `check_finals_contain` 5/6 → 6/6, `check_http` 5/6 → 6/6, `check_no_error` 5/6 → 6/6, `check_run_metadata` 5/6 → 6/6, `check_service` 5/6 → 6/6, `check_state` 5/6 → 6/6, `check_streamed` 5/6 → 6/6, `check_structured` 5/6 → 6/6, `check_tool_args` 5/6 → 6/6, `check_tool_results` 5/6 → 6/6, `check_tools_called` 5/6 → 6/6, `check_workflow` 5/6 → 6/6

</details>

### Totals

| Metric | Before | After |
|---|---|---|
| `check_answer_contains` | 68/69 | 68/69 |
| `check_answer_excludes` | 68/69 | 69/69 |
| `check_authors` | 68/69 | 69/69 |
| `check_files` | 68/69 | 69/69 |
| `check_finals_contain` | 68/69 | 69/69 |
| `check_http` | 68/69 | 69/69 |
| `check_no_error` | 68/69 | 69/69 |
| `check_run_metadata` | 68/69 | 69/69 |
| `check_service` | 68/69 | 69/69 |
| `check_state` | 68/69 | 69/69 |
| `check_streamed` | 68/69 | 69/69 |
| `check_structured` | 68/69 | 69/69 |
| `check_tool_args` | 68/69 | 69/69 |
| `check_tool_results` | 68/69 | 69/69 |
| `check_tools_called` | 68/69 | 69/69 |
| `check_workflow` | 68/69 | 69/69 |

<details><summary>Provenance</summary>

- Before: `base` at `539fec6`, local backend, dataset `bfe276b66ed1`, 69 run(s)
- After: `head` at `539fec6`, local backend, dataset `bfe276b66ed1`, 69 run(s)

</details>
