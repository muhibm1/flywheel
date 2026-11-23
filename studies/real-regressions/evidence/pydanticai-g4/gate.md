<!-- flywheel-report -->
## ❌ Flywheel: this change is blocked

Flywheel ran the agent on 18 test cases, 3 times each, before and after this change, and compared the results case by case. Result: 1 case that passed before now fails. Blocked because 1 case broke (at most 0 allowed); and 1 case raises an error it did not raise before.

### Broken: passed before, fail now

- `g4-diff-server-already-running` {"kind":"mcp_sampling2","mode":"already_running","prompts":["Classify this ticket with the classify_ticket tool: 'I was charged twice for my annual plan and ne…
  - `check_answer` 3/3 → 0/3, `check_outputs` 3/3 → 0/3, `check_tool_returns` 3/3 → 0/3, `check_tools` 3/3 → 0/3
  - new error: `UsageLimitExceeded: The next request would exceed the request_limit of 15`

### Totals

| Metric | Before | After |
|---|---|---|
| `check_answer` | 54/54 | 51/54 |
| `check_outputs` | 54/54 | 51/54 |
| `check_tool_returns` | 54/54 | 51/54 |
| `check_tools` | 54/54 | 51/54 |

Sign test over broken and fixed cases: p = 1 (the chance of a split at least this uneven if the change did nothing).

<details><summary>Provenance</summary>

- Before: `base` at `539fec6`, local backend, dataset `e1fe47e56711`, 54 run(s)
- After: `head` at `539fec6`, local backend, dataset `e1fe47e56711`, 54 run(s)

</details>
