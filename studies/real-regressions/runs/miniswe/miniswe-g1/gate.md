<!-- flywheel-report -->
## ✅ Flywheel: no regressions

Flywheel ran the agent on 11 test cases, 3 times each, before and after this change, and compared the results case by case. Nothing changed.

### Totals

| Metric | Before | After |
|---|---|---|
| `check_exit_status` | 33/33 | 33/33 |
| `check_files` | 33/33 | 33/33 |
| `check_limits` | 33/33 | 33/33 |
| `check_trajectory` | 33/33 | 33/33 |
| `check_verify` | 33/33 | 33/33 |

<details><summary>Provenance</summary>

- Before: `base` at `5ae8178`, local backend, dataset `901ed98fd6d8`, 33 run(s)
- After: `head` at `5ae8178`, local backend, dataset `901ed98fd6d8`, 33 run(s)

</details>
