<!-- flywheel-report -->
## ❌ Flywheel: this change is blocked

Flywheel ran the agent on 20 test cases, 3 times each, before and after this change, and compared the results case by case. Result: 1 case that passed before now fails; 1 case that failed before now passes; 5 moved by less than the noise threshold. Blocked because 1 case broke (at most 0 allowed).

### Broken: passed before, fail now

- `48793f4067db` {"email_input":{"author":"Rachel Kim <rachel.kim@company.com>","email_thread":"Hi Lance,\n\nI just joined the applied AI team and would love to pick your brain…
  - `criteria` 2/3 → 0/3, `tool_calls` 2/3 → 0/3

### Fixed: failed before, pass now

- `94630342d70f` {"email_input":{"author":"Project Manager <pm@client.com>","email_thread":"Lance,\n\nIt's tax season again, and I wanted to schedule a call to discuss your tax…
  - `triage` 0/3 → 2/3

<details><summary>Wobbling: changed by less than the threshold (reported, not blocking) (5)</summary>

- `7686fdceb450` {"email_input":{"author":"Conference Organizer <events@techconf.com>","email_thread":"Hi Lance,\n\nWe're reaching out to invite you to TechConf 2025, happening…
  - `criteria` 0/3 → 1/3, `tool_calls` 0/3 → 1/3, `triage` 0/3 → 1/3
- `b1391c55ef27` {"email_input":{"author":"Omar Haddad <omar@company.com>","email_thread":"Lance,\n\nWe need one more interviewer for a staff engineer candidate on Friday. The …
  - `criteria` 2/3 → 1/3
- `d7f5b1d40e05` {"email_input":{"author":"Community Pool <info@cityrecreation.org>","email_thread":"Dear Lance,\n\nSummer swimming registration is now open! Based on your daug…
  - `tool_calls` 3/3 → 2/3
- `d936c521e222` {"email_input":{"author":"GitHub <notifications@github.com>","email_thread":"Hey there!\n\nalex-dev commented on your pull request #42 in langchain-ai/project:…
  - `triage` 3/3 → 2/3
- `e9092291cb7c` {"email_input":{"author":"Team Lead <teamlead@company.com>","email_thread":"Hi Lance,\n\nIt's time for our quarterly planning session. I'd like to schedule a 9…
  - `criteria` 1/3 → 0/3, `tool_calls` 1/3 → 0/3

</details>

### Totals

| Metric | Before | After |
|---|---|---|
| `criteria` | 17/33 | 14/33 |
| `tool_calls` | 18/33 | 15/33 |
| `triage` | 51/60 | 53/60 |

Sign test over broken and fixed cases: p = 1 (the chance of a split at least this uneven if the change did nothing).

<details><summary>Provenance</summary>

- Before: `main-a`, local backend, dataset `7514c07d09a6`, 3 repetition(s)
- After: `head-haiku` at `ad3aac9`, local backend, dataset `7514c07d09a6`, 3 repetition(s)

</details>
