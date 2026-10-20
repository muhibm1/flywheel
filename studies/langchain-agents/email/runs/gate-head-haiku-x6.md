<!-- flywheel-report -->
## ❌ Flywheel: this change is blocked

Flywheel ran the agent on 20 test cases, 6 times each, before and after this change, and compared the results case by case. Result: 1 case that passed before now fails; 1 case that failed before now passes; 7 moved by less than the noise threshold. Blocked because 1 case broke (at most 0 allowed).

### Broken: passed before, fail now

- `48793f4067db` {"email_input":{"author":"Rachel Kim <rachel.kim@company.com>","email_thread":"Hi Lance,\n\nI just joined the applied AI team and would love to pick your brain…
  - `criteria` 4/6 → 0/6, `tool_calls` 4/6 → 0/6

### Fixed: failed before, pass now

- `94630342d70f` {"email_input":{"author":"Project Manager <pm@client.com>","email_thread":"Lance,\n\nIt's tax season again, and I wanted to schedule a call to discuss your tax…
  - `triage` 0/6 → 4/6

<details><summary>Wobbling: changed by less than the threshold (reported, not blocking) (7)</summary>

- `16e8090d3b20` {"email_input":{"author":"Lincoln Elementary <office@lincolnelementary.org>","email_thread":"Dear Parent,\n\nYour daughter Emma's class is presenting at the sc…
  - `criteria` 2/6 → 1/6, `tool_calls` 6/6 → 5/6
- `7686fdceb450` {"email_input":{"author":"Conference Organizer <events@techconf.com>","email_thread":"Hi Lance,\n\nWe're reaching out to invite you to TechConf 2025, happening…
  - `criteria` 0/6 → 2/6, `tool_calls` 0/6 → 2/6, `triage` 0/6 → 2/6
- `7fd34b3c68ac` {"email_input":{"author":"CI Bot <ci@company.com>","email_thread":"Build #4821 on main FAILED.\n\nStage: integration-tests\nFailed test: test_streaming_metadat…
  - `triage` 5/6 → 6/6
- `b1391c55ef27` {"email_input":{"author":"Omar Haddad <omar@company.com>","email_thread":"Lance,\n\nWe need one more interviewer for a staff engineer candidate on Friday. The …
  - `criteria` 2/6 → 1/6
- `d7f5b1d40e05` {"email_input":{"author":"Community Pool <info@cityrecreation.org>","email_thread":"Dear Lance,\n\nSummer swimming registration is now open! Based on your daug…
  - `criteria` 4/6 → 5/6, `tool_calls` 6/6 → 5/6
- `d936c521e222` {"email_input":{"author":"GitHub <notifications@github.com>","email_thread":"Hey there!\n\nalex-dev commented on your pull request #42 in langchain-ai/project:…
  - `triage` 4/6 → 3/6
- `e9092291cb7c` {"email_input":{"author":"Team Lead <teamlead@company.com>","email_thread":"Hi Lance,\n\nIt's time for our quarterly planning session. I'd like to schedule a 9…
  - `criteria` 2/6 → 0/6, `tool_calls` 2/6 → 0/6

</details>

### Totals

| Metric | Before | After |
|---|---|---|
| `criteria` | 32/66 | 27/66 |
| `tool_calls` | 36/66 | 30/66 |
| `triage` | 99/120 | 105/120 |

Sign test over broken and fixed cases: p = 1 (the chance of a split at least this uneven if the change did nothing).

<details><summary>Provenance</summary>

- Before: `main-a`, local backend, dataset `7514c07d09a6`, 6 repetition(s)
- After: `head-haiku`, local backend, dataset `7514c07d09a6`, 6 repetition(s)

</details>
