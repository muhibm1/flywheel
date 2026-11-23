<!-- flywheel-report -->
## ❌ Flywheel: this change is blocked

Flywheel ran the agent on 16 test cases, 3 times each, and 6 times for the 3 close calls where more runs could change the answer, before and after this change, and compared the results case by case. Result: 1 case that passed before now fails; 1 moved by less than the noise threshold. Blocked because 1 case broke (at most 0 allowed).

### Broken: passed before, fail now

- `d-g1-effort-medium-sum` {"flags":["--model-params","{\"use_responses_api\": false, \"reasoning_effort\": \"medium\"}"],"mode":"code","task":"What is 123 plus 456? Reply with just the …
  - `check_answer` 5/6 → 2/6, `check_exit` 5/6 → 2/6

<details><summary>Wobbling: changed by less than the threshold (reported, not blocking) (1)</summary>

- `g1-no-effort-arith` {"flags":["--model-params","{\"use_responses_api\": false}"],"mode":"code","task":"What is 100 minus 37? Reply with just the number."}
  - `check_answer` 4/6 → 5/6, `check_exit` 4/6 → 5/6

</details>

### Totals

| Metric | Before | After |
|---|---|---|
| `check_answer` | 49/57 | 47/57 |
| `check_exit` | 49/57 | 47/57 |
| `check_files` | 57/57 | 57/57 |
| `check_structured` | 57/57 | 57/57 |
| `check_tools` | 57/57 | 57/57 |

Sign test over broken and fixed cases: p = 1 (the chance of a split at least this uneven if the change did nothing).

<details><summary>Provenance</summary>

- Before: `base` at `539fec6`, local backend, dataset `4bf3bc23c1c2`, 57 run(s)
- After: `head` at `539fec6`, local backend, dataset `4bf3bc23c1c2`, 57 run(s)

</details>
