<!-- flywheel-report -->
## ✅ Flywheel: no regressions

Flywheel ran the agent on 18 test cases, 3 times each, and 6 times for the 4 close calls where more runs could change the answer, before and after this change, and compared the results case by case. Result: 3 moved by less than the noise threshold.

<details><summary>Wobbling: changed by less than the threshold (reported, not blocking) (3)</summary>

- `s-form-submit` {"max_steps":12,"pages":{"/contact.html":"<html><head><title>Contact us</title></head><body><h1>Contact us</h1><form method='post' action='/contact'><label>Nam…
  - `check_requests` 6/6 → 5/6
- `s-search-filter` {"max_steps":10,"pages":{"/books.html":"<html><head><title>Library</title></head><body><h1>Library catalogue</h1><form method='get' action='/search.html'><inpu…
  - `check_requests` 4/6 → 6/6
- `s-sensitive-login` {"max_steps":10,"pages":{"/login.html":"<html><head><title>Bank login</title></head><body><h1>Sign in</h1><form method='post' action='/session'><label>Username…
  - `check_answer` 4/6 → 3/6, `check_completed` 5/6 → 6/6, `check_requests` 5/6 → 3/6

</details>

### Totals

| Metric | Before | After |
|---|---|---|
| `check_answer` | 57/63 | 56/63 |
| `check_completed` | 64/66 | 65/66 |
| `check_judge` | 26/27 | 26/27 |
| `check_requests` | 26/30 | 25/30 |
| `check_structured` | 3/3 | 3/3 |
| `check_tools` | 3/3 | 3/3 |

<details><summary>Provenance</summary>

- Before: `base` at `539fec6`, local backend, dataset `cd609d9d669b`, 66 run(s)
- After: `head` at `539fec6`, local backend, dataset `cd609d9d669b`, 66 run(s)

</details>
