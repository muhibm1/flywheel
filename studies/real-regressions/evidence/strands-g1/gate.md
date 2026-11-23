<!-- flywheel-report -->
## ✅ Flywheel: no regressions

Flywheel ran the agent on 18 test cases, 3 times each, before and after this change, and compared the results case by case. Nothing changed.

### Totals

| Metric | Before | After |
|---|---|---|
| `check_answer` | 54/54 | 54/54 |
| `check_bedrock` | 54/54 | 54/54 |
| `check_files` | 54/54 | 54/54 |
| `check_graph` | 54/54 | 54/54 |
| `check_no_subagent_error` | 54/54 | 54/54 |
| `check_sent_status` | 54/54 | 54/54 |
| `check_session` | 54/54 | 54/54 |
| `check_state` | 54/54 | 54/54 |
| `check_structured` | 54/54 | 54/54 |
| `check_tools` | 54/54 | 54/54 |
| `check_turns` | 54/54 | 54/54 |

<details><summary>Provenance</summary>

- Before: `base` at `539fec6`, local backend, dataset `839bb50c62e5`, 54 run(s)
- After: `head` at `539fec6`, local backend, dataset `839bb50c62e5`, 54 run(s)

</details>
