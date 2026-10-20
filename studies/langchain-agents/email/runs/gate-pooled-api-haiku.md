<!-- flywheel-report -->
## ❌ Flywheel: this change is blocked

Flywheel ran the agent on 20 test cases, 3 times each, before and after this change, and compared the results case by case. Result: 2 cases that passed before now fail; 5 cases that failed before now pass; 3 moved by less than the noise threshold. Blocked because 2 cases broke (at most 0 allowed).

### Broken: passed before, fail now

- `16e8090d3b20` {"email_input":{"author":"Lincoln Elementary <office@lincolnelementary.org>","email_thread":"Dear Parent,\n\nYour daughter Emma's class is presenting at the sc…
  - `criteria` 8/12 → 0/3
- `d936c521e222` {"email_input":{"author":"GitHub <notifications@github.com>","email_thread":"Hey there!\n\nalex-dev commented on your pull request #42 in langchain-ai/project:…
  - `triage` 6/12 → 0/3

### Fixed: failed before, pass now

- `48793f4067db` {"email_input":{"author":"Rachel Kim <rachel.kim@company.com>","email_thread":"Hi Lance,\n\nI just joined the applied AI team and would love to pick your brain…
  - `criteria` 4/12 → 3/3, `tool_calls` 4/12 → 3/3
- `7686fdceb450` {"email_input":{"author":"Conference Organizer <events@techconf.com>","email_thread":"Hi Lance,\n\nWe're reaching out to invite you to TechConf 2025, happening…
  - `criteria` 0/12 → 3/3, `tool_calls` 1/12 → 3/3, `triage` 1/12 → 3/3
- `b04a1ebbfaa5` {"email_input":{"author":"Project Team <project@company.com>","email_thread":"Hi Lance,\n\nThe leadership team has asked us to prepare a joint presentation on …
  - `criteria` 0/12 → 3/3, `tool_calls` 0/12 → 3/3
- `b1391c55ef27` {"email_input":{"author":"Omar Haddad <omar@company.com>","email_thread":"Lance,\n\nWe need one more interviewer for a staff engineer candidate on Friday. The …
  - `criteria` 3/12 → 3/3
- `e9092291cb7c` {"email_input":{"author":"Team Lead <teamlead@company.com>","email_thread":"Hi Lance,\n\nIt's time for our quarterly planning session. I'd like to schedule a 9…
  - `criteria` 5/12 → 3/3, `tool_calls` 5/12 → 3/3

<details><summary>Wobbling: changed by less than the threshold (reported, not blocking) (3)</summary>

- `2368ed5bdcc6` {"email_input":{"author":"Marketing Team <marketing@openai.com>","email_thread":"Hi Lance,\n\nWe're excited to announce that we've released a new model from Op…
  - `triage` 2/12 → 0/3
- `7fd34b3c68ac` {"email_input":{"author":"CI Bot <ci@company.com>","email_thread":"Build #4821 on main FAILED.\n\nStage: integration-tests\nFailed test: test_streaming_metadat…
  - `triage` 11/12 → 3/3
- `d7f5b1d40e05` {"email_input":{"author":"Community Pool <info@cityrecreation.org>","email_thread":"Dear Lance,\n\nSummer swimming registration is now open! Based on your daug…
  - `criteria` 9/12 → 3/3

</details>

### Totals

| Metric | Before | After |
|---|---|---|
| `criteria` | 65/132 | 27/33 |
| `tool_calls` | 70/132 | 27/33 |
| `triage` | 200/240 | 51/60 |

Sign test over broken and fixed cases: p = 0.453 (the chance of a split at least this uneven if the change did nothing).

<details><summary>Provenance</summary>

- Before: `main-a + main-b`, local backend, dataset `7514c07d09a6`, 12 repetition(s)
- After: `api-haiku` at `e72d51a`, local backend, dataset `7514c07d09a6`, 3 repetition(s)

</details>
