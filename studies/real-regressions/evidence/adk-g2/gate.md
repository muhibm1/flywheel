<!-- flywheel-report -->
## ✅ Flywheel: no regressions

Flywheel ran the agent on 24 test cases, 3 times each, and 6 times for the 1 close call where more runs could change the answer, before and after this change, and compared the results case by case. Nothing changed.

### Totals

| Metric | Before | After |
|---|---|---|
| `check_answer_contains` | 74/75 | 74/75 |
| `check_answer_excludes` | 75/75 | 75/75 |
| `check_authors` | 75/75 | 75/75 |
| `check_files` | 75/75 | 75/75 |
| `check_finals_contain` | 75/75 | 75/75 |
| `check_http` | 75/75 | 75/75 |
| `check_no_error` | 75/75 | 75/75 |
| `check_run_metadata` | 75/75 | 75/75 |
| `check_service` | 75/75 | 75/75 |
| `check_state` | 75/75 | 75/75 |
| `check_streamed` | 75/75 | 75/75 |
| `check_structured` | 75/75 | 75/75 |
| `check_tool_args` | 75/75 | 75/75 |
| `check_tool_results` | 75/75 | 75/75 |
| `check_tools_called` | 75/75 | 75/75 |
| `check_workflow` | 75/75 | 75/75 |

<details><summary>Provenance</summary>

- Before: `base` at `539fec6`, local backend, dataset `7e82467f4128`, 75 run(s)
- After: `head` at `539fec6`, local backend, dataset `7e82467f4128`, 75 run(s)

</details>
