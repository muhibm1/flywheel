<!-- flywheel-report -->
## ❌ Flywheel: this change is blocked

Flywheel ran the agent on 22 test cases, 3 times each, and 6 times for the 2 close calls where more runs could change the answer, before and after this change, and compared the results case by case. Result: 1 case that passed before now fails; 1 moved by less than the noise threshold. Blocked because 1 case broke (at most 0 allowed).

### Broken: passed before, fail now

- `g10_x_clone_task_sub_agent_instruction_update` {"agent":{"instruction":"You are a coordinator. For any arithmetic, delegate to the worker helper and report its result.","name":"root","sub_agents":[{"descrip…
  - `check_answer_contains` 5/6 → 2/6

<details><summary>Wobbling: changed by less than the threshold (reported, not blocking) (1)</summary>

- `g10_sweep_clone_streaming_with_new_tools` {"agent":{"instruction":"You do arithmetic using the tools you have."},"clone":{"update":{"tools":["multiply"]}},"messages":["What is 6 times 7? Use the multip…
  - `check_answer_contains` 6/6 → 5/6

</details>

### Totals

| Metric | Before | After |
|---|---|---|
| `check_answer_contains` | 71/72 | 67/72 |
| `check_answer_excludes` | 72/72 | 72/72 |
| `check_authors` | 72/72 | 72/72 |
| `check_files` | 72/72 | 72/72 |
| `check_finals_contain` | 72/72 | 72/72 |
| `check_http` | 72/72 | 72/72 |
| `check_no_error` | 72/72 | 72/72 |
| `check_run_metadata` | 72/72 | 72/72 |
| `check_service` | 72/72 | 72/72 |
| `check_state` | 72/72 | 72/72 |
| `check_streamed` | 72/72 | 72/72 |
| `check_structured` | 72/72 | 72/72 |
| `check_tool_args` | 72/72 | 72/72 |
| `check_tool_results` | 72/72 | 72/72 |
| `check_tools_called` | 72/72 | 72/72 |
| `check_workflow` | 72/72 | 72/72 |

Sign test over broken and fixed cases: p = 1 (the chance of a split at least this uneven if the change did nothing).

<details><summary>Provenance</summary>

- Before: `base` at `539fec6`, local backend, dataset `794381093534`, 72 run(s)
- After: `head` at `539fec6`, local backend, dataset `794381093534`, 72 run(s)

</details>
