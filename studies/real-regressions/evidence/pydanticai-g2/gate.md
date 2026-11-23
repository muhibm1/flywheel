<!-- flywheel-report -->
## ✅ Flywheel: no regressions

Flywheel ran the agent on 19 test cases, 3 times each, before and after this change, and compared the results case by case. Nothing changed.

### Totals

| Metric | Before | After |
|---|---|---|
| `check_answer` | 57/57 | 57/57 |
| `check_outputs` | 57/57 | 57/57 |
| `check_tool_returns` | 57/57 | 57/57 |
| `check_tools` | 57/57 | 57/57 |

<details><summary>Provenance</summary>

- Before: `base` at `539fec6`, local backend, dataset `bc1fbab8f90d`, 57 run(s)
- After: `head` at `539fec6`, local backend, dataset `bc1fbab8f90d`, 57 run(s)

</details>
