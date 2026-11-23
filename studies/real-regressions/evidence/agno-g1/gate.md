<!-- flywheel-report -->
## ❌ Flywheel: this change is blocked

Flywheel ran the agent on 17 test cases, 3 times each, before and after this change, and compared the results case by case. Result: 2 cases that passed before now fail. Blocked because 2 cases broke (at most 0 allowed).

### Broken: passed before, fail now

- `chg-g1-multi-mcp-provider` {"header_provider":{"headers":{"X-Tenant":"globex"},"style":"static"},"kind":"mcp_http","prompt":"What is my account balance, and what would it cost to ship a …
  - `check_answer` 3/3 → 0/3, `check_tool_args` 3/3 → 0/3, `check_tools` 3/3 → 0/3
- `diff-g1-multi-server-params-no-headers` {"header_provider":{"headers":{"X-Tenant":"globex"},"style":"static"},"kind":"mcp_http","prompt":"What would it cost to ship a 10 kg parcel? Use your tools.","…
  - `check_answer` 3/3 → 0/3, `check_tools` 3/3 → 0/3

### Totals

| Metric | Before | After |
|---|---|---|
| `check_answer` | 51/51 | 45/51 |
| `check_files` | 51/51 | 51/51 |
| `check_knowledge` | 51/51 | 51/51 |
| `check_no_error` | 51/51 | 51/51 |
| `check_state` | 51/51 | 51/51 |
| `check_structured` | 51/51 | 51/51 |
| `check_tool_args` | 51/51 | 48/51 |
| `check_tools` | 51/51 | 45/51 |

Sign test over broken and fixed cases: p = 0.5 (the chance of a split at least this uneven if the change did nothing).

<details><summary>Provenance</summary>

- Before: `base` at `539fec6`, local backend, dataset `7704fec769c2`, 51 run(s)
- After: `head` at `539fec6`, local backend, dataset `7704fec769c2`, 51 run(s)

</details>
