<!-- flywheel-report -->
## ✅ Flywheel: no regressions

Flywheel ran the agent on 18 test cases, 3 times each, and 6 times for the 3 close calls where more runs could change the answer, before and after this change, and compared the results case by case. Result: 2 moved by less than the noise threshold.

<details><summary>Wobbling: changed by less than the threshold (reported, not blocking) (2)</summary>

- `s-search-filter` {"max_steps":10,"pages":{"/books.html":"<html><head><title>Library</title></head><body><h1>Library catalogue</h1><form method='get' action='/search.html'><inpu…
  - `check_answer` 3/6 → 4/6, `check_requests` 4/6 → 5/6
- `s-sensitive-login` {"max_steps":10,"pages":{"/login.html":"<html><head><title>Bank login</title></head><body><h1>Sign in</h1><form method='post' action='/session'><label>Username…
  - `check_answer` 4/6 → 3/6, `check_completed` 6/6 → 5/6

</details>

### Totals

| Metric | Before | After |
|---|---|---|
| `check_answer` | 33/39 | 33/39 |
| `check_completed` | 63/63 | 62/63 |
| `check_requests` | 19/24 | 20/24 |
| `check_structured` | 24/24 | 24/24 |
| `check_tools` | 3/3 | 3/3 |

<details><summary>Provenance</summary>

- Before: `base` at `539fec6`, local backend, dataset `5b42af5107dc`, 63 run(s)
- After: `head` at `539fec6`, local backend, dataset `5b42af5107dc`, 63 run(s)

</details>
