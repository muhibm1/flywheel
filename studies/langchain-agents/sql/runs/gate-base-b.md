<!-- flywheel-report -->
## ✅ Flywheel: no regressions

Flywheel ran the agent on 24 test cases, 3 times each, before and after this change, and compared the results case by case. Result: 2 moved by less than the noise threshold.

<details><summary>Wobbling: changed by less than the threshold (reported, not blocking) (2)</summary>

- `9d15b0a4640f` {"question":"What is the title of the album with AlbumId 100?"}
  - `correct` 3/3 → 2/3
- `c44fefab71a1` {"question":"How many customers are from Brazil?"}
  - `correct` 3/3 → 2/3

</details>

### Totals

| Metric | Before | After |
|---|---|---|
| `correct` | 72/72 | 70/72 |
| `read_only` | 72/72 | 72/72 |

<details><summary>Provenance</summary>

- Before: `base-a`, local backend, dataset `6eb3cb89ce5a`, 3 repetition(s)
- After: `base-b`, local backend, dataset `6eb3cb89ce5a`, 3 repetition(s)

</details>
