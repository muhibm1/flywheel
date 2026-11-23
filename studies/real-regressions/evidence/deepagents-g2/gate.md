<!-- flywheel-report -->
## ❌ Flywheel: this change is blocked

Flywheel ran the agent on 17 test cases, 3 times each, and 6 times for the 2 close calls where more runs could change the answer, before and after this change, and compared the results case by case. Result: 1 case that passed before now fails; 1 moved by less than the noise threshold. Blocked because 1 case broke (at most 0 allowed).

### Broken: passed before, fail now

- `d-g2-posttool-hook-shell` {"files":{"b.txt":"mango-77\n"},"flags":["--model-params","{\"use_responses_api\": false}","-S","all","--max-turns","8"],"hooks_json":{"hooks":{"PostToolUse":[…
  - `check_answer` 3/3 → 0/3, `check_exit` 3/3 → 0/3

<details><summary>Wobbling: changed by less than the threshold (reported, not blocking) (1)</summary>

- `std-subagent-currency` {"subagents":["currency-agent"],"task":"Ask the currency-agent subagent to convert 80 EUR to GBP, then tell me the result."}
  - `check_answer` 5/6 → 6/6, `check_tools` 5/6 → 6/6

</details>

### Totals

| Metric | Before | After |
|---|---|---|
| `check_answer` | 55/57 | 53/57 |
| `check_exit` | 56/57 | 53/57 |
| `check_files` | 57/57 | 57/57 |
| `check_structured` | 57/57 | 57/57 |
| `check_tools` | 56/57 | 57/57 |

Sign test over broken and fixed cases: p = 1 (the chance of a split at least this uneven if the change did nothing).

<details><summary>Provenance</summary>

- Before: `base` at `539fec6`, local backend, dataset `4aa2cdf7339b`, 57 run(s)
- After: `head` at `539fec6`, local backend, dataset `4aa2cdf7339b`, 57 run(s)

</details>
