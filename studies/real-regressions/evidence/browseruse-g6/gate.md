<!-- flywheel-report -->
## ✅ Flywheel: no regressions

Flywheel ran the agent on 16 test cases, 3 times each, and 6 times for the 1 close call where more runs could change the answer, before and after this change, and compared the results case by case. Result: 1 moved by less than the noise threshold.

<details><summary>Wobbling: changed by less than the threshold (reported, not blocking) (1)</summary>

- `s-custom-tool` {"max_steps":10,"pages":{"/cart.html":"<html><head><title>Cart</title></head><body><h1>Your cart</h1><ul><li>Desk lamp - SKU A-100 - qty 1</li><li>Office chair…
  - `check_tools` 2/6 → 3/6

</details>

### Totals

| Metric | Before | After |
|---|---|---|
| `check_answer` | 39/39 | 39/39 |
| `check_completed` | 51/51 | 51/51 |
| `check_files` | 6/6 | 6/6 |
| `check_requests` | 12/12 | 12/12 |
| `check_structured` | 12/12 | 12/12 |
| `check_tools` | 2/6 | 3/6 |

<details><summary>Provenance</summary>

- Before: `base` at `539fec6`, local backend, dataset `57d469e7aa77`, 51 run(s)
- After: `head` at `539fec6`, local backend, dataset `57d469e7aa77`, 51 run(s)

</details>
