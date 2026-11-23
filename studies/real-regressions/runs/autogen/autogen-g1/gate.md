<!-- flywheel-report -->
## ❌ Flywheel: this change is blocked

Flywheel ran the agent on 13 test cases, 3 times each, and 6 times for the 3 close calls where more runs could change the answer, before and after this change, and compared the results case by case. Result: 3 cases that passed before now fail; 1 moved by less than the noise threshold. Blocked because 3 cases broke (at most 0 allowed); and 2 cases raise an error it did not raise before.

### Broken: passed before, fail now

- `g1-reflect-system-format` {"scenario":"weather_styled","task":"What is the weather in Paris right now?"}
  - `check_answer` 3/3 → 0/3
- `s-swarm-handoff` {"scenario":"swarm","task":"Hi, how much do I owe on invoice INV-7731?"}
  - `check_answer` 6/6 → 3/6, `check_files` 6/6 → 4/6, `check_flow` 6/6 → 4/6, `check_json` 6/6 → 4/6, `check_tools` 6/6 → 4/6
  - new error: `TimeoutError: `
- `s-weather-tool` {"scenario":"weather","task":"What is the weather in Paris right now?"}
  - `check_answer` 5/6 → 2/6

<details><summary>Wobbling: changed by less than the threshold (reported, not blocking) (1)</summary>

- `g1-tool-then-handoff` {"scenario":"swarm_tool_handoff","task":"Hello, what is the amount due on invoice INV-7731?"}
  - `check_answer` 6/6 → 4/6, `check_files` 6/6 → 5/6, `check_flow` 6/6 → 5/6, `check_json` 6/6 → 5/6, `check_tools` 6/6 → 5/6
  - new error: `TimeoutError: `

</details>

### Totals

| Metric | Before | After |
|---|---|---|
| `check_answer` | 45/48 | 34/48 |
| `check_files` | 46/48 | 43/48 |
| `check_flow` | 46/48 | 43/48 |
| `check_json` | 46/48 | 43/48 |
| `check_tools` | 45/48 | 42/48 |

Sign test over broken and fixed cases: p = 0.25 (the chance of a split at least this uneven if the change did nothing).

<details><summary>Provenance</summary>

- Before: `base + base`, local backend, dataset `e073ca6bec6a`, 48 run(s)
- After: `head + head`, local backend, dataset `e073ca6bec6a`, 48 run(s)

</details>
