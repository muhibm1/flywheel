<!-- flywheel-report -->
## ✅ Flywheel: no regressions

Flywheel ran the agent on 16 test cases, 3 times each, before and after this change, and compared the results case by case. Nothing changed.

### Totals

| Metric | Before | After |
|---|---|---|
| `check_answer` | 47/48 | 47/48 |
| `check_exit` | 48/48 | 48/48 |
| `check_files` | 48/48 | 48/48 |
| `check_structured` | 48/48 | 48/48 |
| `check_tools` | 47/48 | 47/48 |

<details><summary>Provenance</summary>

- Before: `base` at `539fec6`, local backend, dataset `3fdcb0c01567`, 48 run(s)
- After: `head` at `539fec6`, local backend, dataset `3fdcb0c01567`, 48 run(s)

</details>
