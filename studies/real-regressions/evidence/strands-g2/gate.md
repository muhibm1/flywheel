<!-- flywheel-report -->
## ❌ Flywheel: this change is blocked

Flywheel ran the agent on 18 test cases, 3 times each, before and after this change, and compared the results case by case. Result: 3 cases that passed before now fail. Blocked because 3 cases broke (at most 0 allowed); and 2 cases raise an error it did not raise before.

### Broken: passed before, fail now

- `g2-diff-session-subagent-async-tool` {"first_turns":["Please note: the warehouse door code is 7314. Acknowledge briefly."],"kind":"session_subagent","prompt":"Ask the notes-keeper agent what the w…
  - `check_answer` 3/3 → 0/3, `check_no_subagent_error` 3/3 → 0/3
- `g2-session-resume-async` {"first_turns":["Please remember: the deploy window is Thursday 14:00 UTC. Acknowledge briefly.","Also remember the on-call engineer is Okonkwo. Acknowledge br…
  - `check_answer` 3/3 → 0/3, `check_bedrock` 3/3 → 0/3, `check_files` 3/3 → 0/3, `check_graph` 3/3 → 0/3, `check_no_subagent_error` 3/3 → 0/3, `check_sent_status` 3/3 → 0/3, `check_session` 3/3 → 0/3, `check_state` 3/3 → 0/3, `check_structured` 3/3 → 0/3, `check_tools` 3/3 → 0/3, `check_turns` 3/3 → 0/3
  - new error: `RuntimeError: asyncio.run() cannot be called from a running event loop`
- `g2-session-resume-async-tools` {"first_turns":["How many gizmos are in stock?"],"kind":"session_resume","resume_mode":"async","second_prompt":"Now check how many widgets are in stock, and te…
  - `check_answer` 3/3 → 0/3, `check_bedrock` 3/3 → 0/3, `check_files` 3/3 → 0/3, `check_graph` 3/3 → 0/3, `check_no_subagent_error` 3/3 → 0/3, `check_sent_status` 3/3 → 0/3, `check_session` 3/3 → 0/3, `check_state` 3/3 → 0/3, `check_structured` 3/3 → 0/3, `check_tools` 3/3 → 0/3, `check_turns` 3/3 → 0/3
  - new error: `RuntimeError: asyncio.run() cannot be called from a running event loop`

### Totals

| Metric | Before | After |
|---|---|---|
| `check_answer` | 54/54 | 45/54 |
| `check_bedrock` | 54/54 | 48/54 |
| `check_files` | 54/54 | 48/54 |
| `check_graph` | 54/54 | 48/54 |
| `check_no_subagent_error` | 54/54 | 45/54 |
| `check_sent_status` | 54/54 | 48/54 |
| `check_session` | 54/54 | 48/54 |
| `check_state` | 54/54 | 48/54 |
| `check_structured` | 54/54 | 48/54 |
| `check_tools` | 54/54 | 48/54 |
| `check_turns` | 54/54 | 48/54 |

Sign test over broken and fixed cases: p = 0.25 (the chance of a split at least this uneven if the change did nothing).

<details><summary>Provenance</summary>

- Before: `base` at `539fec6`, local backend, dataset `da47c7efcc06`, 54 run(s)
- After: `head` at `539fec6`, local backend, dataset `da47c7efcc06`, 54 run(s)

</details>
