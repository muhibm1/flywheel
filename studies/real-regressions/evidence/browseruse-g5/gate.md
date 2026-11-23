<!-- flywheel-report -->
## ✅ Flywheel: no regressions

Flywheel ran the agent on 16 test cases, 3 times each, and 6 times for the 1 close call where more runs could change the answer, before and after this change, and compared the results case by case. Nothing changed.

### Totals

| Metric | Before | After |
|---|---|---|
| `check_answer` | 48/48 | 48/48 |
| `check_completed` | 51/51 | 51/51 |
| `check_requests` | 27/27 | 27/27 |
| `check_structured` | 3/3 | 3/3 |
| `check_tools` | 6/9 | 6/9 |

<details><summary>Provenance</summary>

- Before: `base` at `539fec6`, local backend, dataset `db40b5af05d2`, 51 run(s)
- After: `head` at `539fec6`, local backend, dataset `db40b5af05d2`, 51 run(s)

</details>
