<!-- flywheel-report -->
## ✅ Flywheel: no regressions

Flywheel ran the agent on 20 test cases, 3 times each, before and after this change, and compared the results case by case. Result: 1 case that failed before now passes; 6 moved by less than the noise threshold.

### Fixed: failed before, pass now

- `94630342d70f` {"email_input":{"author":"Project Manager <pm@client.com>","email_thread":"Lance,\n\nIt's tax season again, and I wanted to schedule a call to discuss your tax…
  - `triage` 0/3 → 2/3

<details><summary>Wobbling: changed by less than the threshold (reported, not blocking) (6)</summary>

- `48793f4067db` {"email_input":{"author":"Rachel Kim <rachel.kim@company.com>","email_thread":"Hi Lance,\n\nI just joined the applied AI team and would love to pick your brain…
  - `criteria` 1/3 → 0/3, `tool_calls` 1/3 → 0/3
- `714903d07aba` {"email_input":{"author":"Dr. Roberts <droberts@medical.org>","email_thread":"Hello Lance,\n\nThis is a reminder that it's time for your annual checkup. Our re…
  - `criteria` 3/3 → 2/3, `tool_calls` 3/3 → 2/3, `triage` 3/3 → 2/3
- `7686fdceb450` {"email_input":{"author":"Conference Organizer <events@techconf.com>","email_thread":"Hi Lance,\n\nWe're reaching out to invite you to TechConf 2025, happening…
  - `criteria` 0/3 → 1/3, `tool_calls` 0/3 → 1/3, `triage` 0/3 → 1/3
- `d7f5b1d40e05` {"email_input":{"author":"Community Pool <info@cityrecreation.org>","email_thread":"Dear Lance,\n\nSummer swimming registration is now open! Based on your daug…
  - `tool_calls` 3/3 → 2/3
- `d936c521e222` {"email_input":{"author":"GitHub <notifications@github.com>","email_thread":"Hey there!\n\nalex-dev commented on your pull request #42 in langchain-ai/project:…
  - `triage` 1/3 → 2/3
- `e9092291cb7c` {"email_input":{"author":"Team Lead <teamlead@company.com>","email_thread":"Hi Lance,\n\nIt's time for our quarterly planning session. I'd like to schedule a 9…
  - `criteria` 1/3 → 2/3, `tool_calls` 1/3 → 2/3

</details>

### Totals

| Metric | Before | After |
|---|---|---|
| `criteria` | 14/33 | 14/33 |
| `tool_calls` | 17/33 | 16/33 |
| `triage` | 49/60 | 52/60 |

Sign test over broken and fixed cases: p = 1 (the chance of a split at least this uneven if the change did nothing).

<details><summary>Provenance</summary>

- Before: `main-a` at `161b913`, local backend, dataset `7514c07d09a6`, 3 repetition(s)
- After: `head-haiku` at `161b913`, local backend, dataset `7514c07d09a6`, 3 repetition(s)

</details>
