<!-- flywheel-report -->
## ✅ Flywheel: no regressions

Flywheel ran the agent on 18 test cases, 3 times each, and 6 times for the 1 close call where more runs could change the answer, before and after this change, and compared the results case by case. Nothing changed.

### Totals

| Metric | Before | After |
|---|---|---|
| `check_answer` | 57/57 | 57/57 |
| `check_exit` | 57/57 | 57/57 |
| `check_files` | 57/57 | 57/57 |
| `check_structured` | 57/57 | 57/57 |
| `check_tools` | 57/57 | 57/57 |

<details><summary>Provenance</summary>

- Before: `base` at `539fec6`, local backend, dataset `7f25f5152f6c`, 57 run(s)
- After: `head` at `539fec6`, local backend, dataset `7f25f5152f6c`, 57 run(s)

</details>
