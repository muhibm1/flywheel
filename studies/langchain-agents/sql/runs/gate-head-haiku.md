<!-- flywheel-report -->
## ✅ Flywheel: no regressions

Flywheel ran the agent on 24 test cases, 3 times each, before and after this change, and compared the results case by case. Result: 2 moved by less than the noise threshold.

<details><summary>Wobbling: changed by less than the threshold (reported, not blocking) (2)</summary>

- `d013ff596964` {"question":"In which month of 2012 was revenue highest? Give the month as YYYY-MM and the revenue rounded to two decimals."}
  - `correct` 3/3 → 2/3
- `e5608cd625e5` {"question":"How many tracks have never been sold?"}
  - `correct` 3/3 → 2/3

</details>

### Totals

| Metric | Before | After |
|---|---|---|
| `correct` | 72/72 | 70/72 |
| `read_only` | 72/72 | 72/72 |

<details><summary>Provenance</summary>

- Before: `base-a`, local backend, dataset `6eb3cb89ce5a`, 3 repetition(s)
- After: `head-haiku`, local backend, dataset `6eb3cb89ce5a`, 3 repetition(s)

</details>
