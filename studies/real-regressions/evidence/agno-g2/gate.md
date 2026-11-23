<!-- flywheel-report -->
## ✅ Flywheel: no regressions

Flywheel ran the agent on 17 test cases, 3 times each, before and after this change, and compared the results case by case. Nothing changed.

### Totals

| Metric | Before | After |
|---|---|---|
| `check_answer` | 51/51 | 51/51 |
| `check_files` | 51/51 | 51/51 |
| `check_knowledge` | 51/51 | 51/51 |
| `check_no_error` | 51/51 | 51/51 |
| `check_state` | 51/51 | 51/51 |
| `check_structured` | 51/51 | 51/51 |
| `check_tool_args` | 51/51 | 51/51 |
| `check_tools` | 51/51 | 51/51 |

<details><summary>Provenance</summary>

- Before: `base` at `539fec6`, local backend, dataset `b797a919f14e`, 51 run(s)
- After: `head` at `539fec6`, local backend, dataset `b797a919f14e`, 51 run(s)

</details>
