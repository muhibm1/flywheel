<!-- flywheel-report -->
## ❌ Flywheel: this change is blocked

Flywheel ran the agent on 22 test cases, 3 times each, and 6 times for the 1 close call where more runs could change the answer, before and after this change, and compared the results case by case. Result: 1 case that passed before now fails; 1 moved by less than the noise threshold. Blocked because 1 case broke (at most 0 allowed).

### Broken: passed before, fail now

- `g8_x_redirect_followed` {"agent":{"instruction":"You manage an inventory through the API tools. Use only the get_moved_item tool to read an item and report its qty. If get_moved_item …
  - `check_answer_contains` 3/3 → 0/3, `check_answer_excludes` 3/3 → 0/3

<details><summary>Wobbling: changed by less than the threshold (reported, not blocking) (1)</summary>

- `g8_sweep_server_error_500` {"agent":{"instruction":"You check the service through the API tools. Call get_boom once. If the API reports an error, tell the user the word 'failed' and quot…
  - `check_answer_contains` 4/6 → 6/6

</details>

### Totals

| Metric | Before | After |
|---|---|---|
| `check_answer_contains` | 67/69 | 66/69 |
| `check_answer_excludes` | 69/69 | 66/69 |
| `check_authors` | 69/69 | 69/69 |
| `check_files` | 69/69 | 69/69 |
| `check_finals_contain` | 69/69 | 69/69 |
| `check_http` | 69/69 | 69/69 |
| `check_no_error` | 69/69 | 69/69 |
| `check_run_metadata` | 69/69 | 69/69 |
| `check_service` | 69/69 | 69/69 |
| `check_state` | 69/69 | 69/69 |
| `check_streamed` | 69/69 | 69/69 |
| `check_structured` | 69/69 | 69/69 |
| `check_tool_args` | 69/69 | 69/69 |
| `check_tool_results` | 69/69 | 69/69 |
| `check_tools_called` | 69/69 | 69/69 |
| `check_workflow` | 69/69 | 69/69 |

Sign test over broken and fixed cases: p = 1 (the chance of a split at least this uneven if the change did nothing).

<details><summary>Provenance</summary>

- Before: `base` at `539fec6`, local backend, dataset `342305be0805`, 69 run(s)
- After: `head` at `539fec6`, local backend, dataset `342305be0805`, 69 run(s)

</details>
