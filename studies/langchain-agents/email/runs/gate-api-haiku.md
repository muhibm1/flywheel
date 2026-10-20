<!-- flywheel-report -->
## ❌ Flywheel: this change is blocked

Flywheel ran the agent on 20 test cases, 3 times each, before and after this change, and compared the results case by case. Result: 1 case that passed before now fails; 1 case that failed before now passes; 1 moved by less than the noise threshold. Blocked because 1 case broke (at most 0 allowed).

### Broken: passed before, fail now

- `16e8090d3b20` {"email_input":{"author":"Lincoln Elementary <office@lincolnelementary.org>","email_thread":"Dear Parent,\n\nYour daughter Emma's class is presenting at the sc…
  - `criteria` 3/3 → 0/3

### Fixed: failed before, pass now

- `b04a1ebbfaa5` {"email_input":{"author":"Project Team <project@company.com>","email_thread":"Hi Lance,\n\nThe leadership team has asked us to prepare a joint presentation on …
  - `criteria` 0/3 → 3/3, `tool_calls` 0/3 → 3/3

<details><summary>Wobbling: changed by less than the threshold (reported, not blocking) (1)</summary>

- `d936c521e222` {"email_input":{"author":"GitHub <notifications@github.com>","email_thread":"Hey there!\n\nalex-dev commented on your pull request #42 in langchain-ai/project:…
  - `triage` 1/3 → 0/3

</details>

### Totals

| Metric | Before | After |
|---|---|---|
| `criteria` | 27/33 | 27/33 |
| `tool_calls` | 24/33 | 27/33 |
| `triage` | 52/60 | 51/60 |

Sign test over broken and fixed cases: p = 1 (the chance of a split at least this uneven if the change did nothing).

<details><summary>Provenance</summary>

- Before: `api-sonnet` at `fac5578`, local backend, dataset `7514c07d09a6`, 3 repetition(s)
- After: `api-haiku` at `e72d51a`, local backend, dataset `7514c07d09a6`, 3 repetition(s)

</details>
