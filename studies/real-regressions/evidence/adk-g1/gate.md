<!-- flywheel-report -->
## ✅ Flywheel: no regressions

Flywheel ran the agent on 21 test cases, 3 times each, before and after this change, and compared the results case by case. Nothing changed.

### Totals

| Metric | Before | After |
|---|---|---|
| `check_answer_contains` | 63/63 | 63/63 |
| `check_answer_excludes` | 63/63 | 63/63 |
| `check_authors` | 63/63 | 63/63 |
| `check_files` | 63/63 | 63/63 |
| `check_finals_contain` | 63/63 | 63/63 |
| `check_http` | 63/63 | 63/63 |
| `check_no_error` | 63/63 | 63/63 |
| `check_run_metadata` | 63/63 | 63/63 |
| `check_service` | 63/63 | 63/63 |
| `check_state` | 63/63 | 63/63 |
| `check_streamed` | 63/63 | 63/63 |
| `check_structured` | 63/63 | 63/63 |
| `check_tool_args` | 63/63 | 63/63 |
| `check_tool_results` | 63/63 | 63/63 |
| `check_tools_called` | 63/63 | 63/63 |
| `check_workflow` | 63/63 | 63/63 |

<details><summary>Provenance</summary>

- Before: `base` at `539fec6`, local backend, dataset `b7526f43b037`, 63 run(s)
- After: `head` at `539fec6`, local backend, dataset `b7526f43b037`, 63 run(s)

</details>
