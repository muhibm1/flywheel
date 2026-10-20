<!-- flywheel-report -->
## ❌ Flywheel: this change is blocked

Flywheel ran the agent on 20 test cases, 6 times each, before and after this change, and compared the results case by case. Result: 1 case that passed before now fails; 1 case that failed before now passes; 7 moved by less than the noise threshold. Blocked because 1 case broke (at most 0 allowed).

### Broken: passed before, fail now

- `16e8090d3b20` {"email_input":{"author":"Lincoln Elementary <office@lincolnelementary.org>","email_thread":"Dear Parent,\n\nYour daughter Emma's class is presenting at the sc…
  - `criteria` 8/12 → 1/6, `tool_calls` 12/12 → 5/6

### Fixed: failed before, pass now

- `94630342d70f` {"email_input":{"author":"Project Manager <pm@client.com>","email_thread":"Lance,\n\nIt's tax season again, and I wanted to schedule a call to discuss your tax…
  - `triage` 0/12 → 4/6

<details><summary>Wobbling: changed by less than the threshold (reported, not blocking) (7)</summary>

- `2368ed5bdcc6` {"email_input":{"author":"Marketing Team <marketing@openai.com>","email_thread":"Hi Lance,\n\nWe're excited to announce that we've released a new model from Op…
  - `triage` 2/12 → 0/6
- `48793f4067db` {"email_input":{"author":"Rachel Kim <rachel.kim@company.com>","email_thread":"Hi Lance,\n\nI just joined the applied AI team and would love to pick your brain…
  - `criteria` 4/12 → 0/6, `tool_calls` 4/12 → 0/6
- `7686fdceb450` {"email_input":{"author":"Conference Organizer <events@techconf.com>","email_thread":"Hi Lance,\n\nWe're reaching out to invite you to TechConf 2025, happening…
  - `criteria` 0/12 → 2/6, `tool_calls` 1/12 → 2/6, `triage` 1/12 → 2/6
- `7fd34b3c68ac` {"email_input":{"author":"CI Bot <ci@company.com>","email_thread":"Build #4821 on main FAILED.\n\nStage: integration-tests\nFailed test: test_streaming_metadat…
  - `triage` 11/12 → 6/6
- `b1391c55ef27` {"email_input":{"author":"Omar Haddad <omar@company.com>","email_thread":"Lance,\n\nWe need one more interviewer for a staff engineer candidate on Friday. The …
  - `criteria` 3/12 → 1/6
- `d7f5b1d40e05` {"email_input":{"author":"Community Pool <info@cityrecreation.org>","email_thread":"Dear Lance,\n\nSummer swimming registration is now open! Based on your daug…
  - `criteria` 9/12 → 5/6, `tool_calls` 12/12 → 5/6
- `e9092291cb7c` {"email_input":{"author":"Team Lead <teamlead@company.com>","email_thread":"Hi Lance,\n\nIt's time for our quarterly planning session. I'd like to schedule a 9…
  - `criteria` 5/12 → 0/6, `tool_calls` 5/12 → 0/6

</details>

### Totals

| Metric | Before | After |
|---|---|---|
| `criteria` | 65/132 | 27/66 |
| `tool_calls` | 70/132 | 30/66 |
| `triage` | 200/240 | 105/120 |

Sign test over broken and fixed cases: p = 1 (the chance of a split at least this uneven if the change did nothing).

<details><summary>Provenance</summary>

- Before: `main-a + main-b`, local backend, dataset `7514c07d09a6`, 12 repetition(s)
- After: `head-haiku`, local backend, dataset `7514c07d09a6`, 6 repetition(s)

</details>
