<!-- flywheel-report -->
## ✅ Flywheel: no regressions

Flywheel ran the agent on 15 test cases, 3 times each, and 6 times for the 2 close calls where more runs could change the answer, before and after this change, and compared the results case by case. Result: 2 moved by less than the noise threshold.

<details><summary>Wobbling: changed by less than the threshold (reported, not blocking) (2)</summary>

- `g5-general-purpose-subagent` {"files":{"data/fruit.txt":"apple pie\nbanana bread\ngreen apple\ncherry tart\napple juice\npear\n"},"task":"Use the task tool to delegate this to a general-pu…
  - `check_tools` 4/6 → 3/6
- `g5-subagent-hr` {"subagents":["hr-agent"],"task":"Ask the hr-agent subagent who manages Carla Gomez and in which year she started. Then tell me both facts."}
  - `check_answer` 5/6 → 6/6

</details>

### Totals

| Metric | Before | After |
|---|---|---|
| `check_answer` | 49/51 | 50/51 |
| `check_exit` | 51/51 | 51/51 |
| `check_files` | 51/51 | 51/51 |
| `check_structured` | 51/51 | 51/51 |
| `check_tools` | 48/51 | 47/51 |

<details><summary>Provenance</summary>

- Before: `base` at `539fec6`, local backend, dataset `2b3b3209bf8a`, 51 run(s)
- After: `head` at `539fec6`, local backend, dataset `2b3b3209bf8a`, 51 run(s)

</details>
