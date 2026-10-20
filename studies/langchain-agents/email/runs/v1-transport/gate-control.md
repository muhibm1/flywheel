<!-- flywheel-report -->
## ✅ Flywheel: no regressions

Flywheel ran the agent on 20 test cases, 3 times each, before and after this change, and compared the results case by case. Result: 2 cases that failed before now pass; 3 moved by less than the noise threshold.

### Fixed: failed before, pass now

- `16e8090d3b20` {"email_input":{"author":"Lincoln Elementary <office@lincolnelementary.org>","email_thread":"Dear Parent,\n\nYour daughter Emma's class is presenting at the sc…
  - `criteria` 0/3 → 2/3
- `7686fdceb450` {"email_input":{"author":"Conference Organizer <events@techconf.com>","email_thread":"Hi Lance,\n\nWe're reaching out to invite you to TechConf 2025, happening…
  - `criteria` 0/3 → 2/3, `tool_calls` 0/3 → 2/3, `triage` 0/3 → 2/3

<details><summary>Wobbling: changed by less than the threshold (reported, not blocking) (3)</summary>

- `48793f4067db` {"email_input":{"author":"Rachel Kim <rachel.kim@company.com>","email_thread":"Hi Lance,\n\nI just joined the applied AI team and would love to pick your brain…
  - `criteria` 1/3 → 0/3, `tool_calls` 1/3 → 0/3
- `b1391c55ef27` {"email_input":{"author":"Omar Haddad <omar@company.com>","email_thread":"Lance,\n\nWe need one more interviewer for a staff engineer candidate on Friday. The …
  - `criteria` 1/3 → 0/3
- `e9092291cb7c` {"email_input":{"author":"Team Lead <teamlead@company.com>","email_thread":"Hi Lance,\n\nIt's time for our quarterly planning session. I'd like to schedule a 9…
  - `criteria` 1/3 → 0/3

</details>

### Totals

| Metric | Before | After |
|---|---|---|
| `criteria` | 14/33 | 15/33 |
| `tool_calls` | 17/33 | 18/33 |
| `triage` | 49/60 | 51/60 |

Sign test over broken and fixed cases: p = 0.5 (the chance of a split at least this uneven if the change did nothing).

<details><summary>Provenance</summary>

- Before: `main-a` at `161b913`, local backend, dataset `7514c07d09a6`, 3 repetition(s)
- After: `main-b` at `161b913`, local backend, dataset `7514c07d09a6`, 3 repetition(s)

</details>
