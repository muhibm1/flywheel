<!-- flywheel-report -->
## ✅ Flywheel: no regressions

Flywheel ran the agent on 16 test cases, 3 times each, and 6 times for the 1 close call where more runs could change the answer, before and after this change, and compared the results case by case. Result: 1 moved by less than the noise threshold.

<details><summary>Wobbling: changed by less than the threshold (reported, not blocking) (1)</summary>

- `custom-report-json` {"docs":{"brannoch.txt":"The Brannoch Observatory\n\nThe Brannoch Observatory sits on Carn Liath in the Scottish Highlands. It was founded by the amateur astro…
  - `check_completed` 5/6 → 4/6, `check_facts` 5/6 → 4/6, `check_format` 5/6 → 4/6, `check_no_forbidden` 5/6 → 4/6, `check_search_results` 5/6 → 4/6, `check_sources` 5/6 → 4/6

</details>

### Totals

| Metric | Before | After |
|---|---|---|
| `check_completed` | 50/51 | 49/51 |
| `check_facts` | 50/51 | 49/51 |
| `check_format` | 50/51 | 49/51 |
| `check_no_forbidden` | 50/51 | 49/51 |
| `check_search_results` | 50/51 | 49/51 |
| `check_sources` | 50/51 | 49/51 |

<details><summary>Provenance</summary>

- Before: `base` at `539fec6`, local backend, dataset `197d0d337328`, 51 run(s)
- After: `head` at `539fec6`, local backend, dataset `197d0d337328`, 51 run(s)

</details>
