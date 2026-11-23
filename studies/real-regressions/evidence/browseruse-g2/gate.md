<!-- flywheel-report -->
## ✅ Flywheel: no regressions

Flywheel ran the agent on 16 test cases, 3 times each, and 6 times for the 3 close calls where more runs could change the answer, before and after this change, and compared the results case by case. Result: 3 moved by less than the noise threshold.

<details><summary>Wobbling: changed by less than the threshold (reported, not blocking) (3)</summary>

- `c2-report-file-attached` {"max_steps":12,"pages":{"/sales.html":"<html><body><h1>Q3 sales</h1><table border='1'><tr><th>Region</th><th>Total</th></tr><tr><td>North</td><td>18,400</td><…
  - `check_files` 5/6 → 6/6
- `s-custom-tool` {"max_steps":10,"pages":{"/cart.html":"<html><head><title>Cart</title></head><body><h1>Your cart</h1><ul><li>Desk lamp - SKU A-100 - qty 1</li><li>Office chair…
  - `check_tools` 5/6 → 6/6
- `s-sensitive-login` {"max_steps":10,"pages":{"/login.html":"<html><head><title>Bank login</title></head><body><h1>Sign in</h1><form method='post' action='/session'><label>Username…
  - `check_requests` 4/6 → 6/6

</details>

### Totals

| Metric | Before | After |
|---|---|---|
| `check_answer` | 39/39 | 39/39 |
| `check_completed` | 57/57 | 57/57 |
| `check_files` | 14/15 | 15/15 |
| `check_requests` | 13/15 | 15/15 |
| `check_structured` | 3/3 | 3/3 |
| `check_tools` | 5/6 | 6/6 |

<details><summary>Provenance</summary>

- Before: `base` at `539fec6`, local backend, dataset `325c1778509e`, 57 run(s)
- After: `head` at `539fec6`, local backend, dataset `325c1778509e`, 57 run(s)

</details>
