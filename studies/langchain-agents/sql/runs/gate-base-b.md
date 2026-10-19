<!-- flywheel-report -->
## ✅ Flywheel: no regressions

Flywheel ran the agent on 36 test cases, 3 times each, before and after this change, and compared the results case by case. Result: 3 moved by less than the noise threshold.

<details><summary>Wobbling: changed by less than the threshold (reported, not blocking) (3)</summary>

- `9d15b0a4640f` {"question":"What is the title of the album with AlbumId 100?"}
  - `correct` 3/3 → 2/3
- `ab4ddb8fd2a7` {"question":"How many customers bought at least one track from every one of the genres Rock, Jazz and Blues?"}
  - `correct` 2/3 → 3/3
- `c44fefab71a1` {"question":"How many customers are from Brazil?"}
  - `correct` 3/3 → 2/3

</details>

### Totals

| Metric | Before | After |
|---|---|---|
| `correct` | 107/108 | 106/108 |
| `read_only` | 108/108 | 108/108 |

<details><summary>Provenance</summary>

- Before: `base-a`, local backend, dataset `690f4c6138cc`, 3 repetition(s)
- After: `base-b`, local backend, dataset `690f4c6138cc`, 3 repetition(s)

</details>
