<!-- flywheel-report -->
## ✅ Flywheel: no regressions

Flywheel ran the agent on 16 test cases, 3 times each, before and after this change, and compared the results case by case. Nothing changed.

### Totals

| Metric | Before | After |
|---|---|---|
| `check_answer` | 48/48 | 48/48 |
| `check_outputs` | 48/48 | 48/48 |
| `check_tool_returns` | 48/48 | 48/48 |
| `check_tools` | 48/48 | 48/48 |

<details><summary>Provenance</summary>

- Before: `base` at `539fec6`, local backend, dataset `4f4a9f4f856e`, 48 run(s)
- After: `head` at `539fec6`, local backend, dataset `4f4a9f4f856e`, 48 run(s)

</details>
