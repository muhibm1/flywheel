<!-- flywheel-report -->
## ✅ Flywheel: no regressions

Flywheel ran the agent on 20 test cases, 6 times each, before and after this change, and compared the results case by case. Result: 9 moved by less than the noise threshold.

<details><summary>Wobbling: changed by less than the threshold (reported, not blocking) (9)</summary>

- `16e8090d3b20` {"email_input":{"author":"Lincoln Elementary <office@lincolnelementary.org>","email_thread":"Dear Parent,\n\nYour daughter Emma's class is presenting at the sc…
  - `criteria` 8/12 → 3/6
- `2368ed5bdcc6` {"email_input":{"author":"Marketing Team <marketing@openai.com>","email_thread":"Hi Lance,\n\nWe're excited to announce that we've released a new model from Op…
  - `triage` 2/12 → 0/6
- `48793f4067db` {"email_input":{"author":"Rachel Kim <rachel.kim@company.com>","email_thread":"Hi Lance,\n\nI just joined the applied AI team and would love to pick your brain…
  - `criteria` 4/12 → 1/6, `tool_calls` 4/12 → 1/6
- `7686fdceb450` {"email_input":{"author":"Conference Organizer <events@techconf.com>","email_thread":"Hi Lance,\n\nWe're reaching out to invite you to TechConf 2025, happening…
  - `criteria` 0/12 → 1/6, `tool_calls` 1/12 → 1/6, `triage` 1/12 → 1/6
- `7fd34b3c68ac` {"email_input":{"author":"CI Bot <ci@company.com>","email_thread":"Build #4821 on main FAILED.\n\nStage: integration-tests\nFailed test: test_streaming_metadat…
  - `triage` 11/12 → 5/6
- `b1391c55ef27` {"email_input":{"author":"Omar Haddad <omar@company.com>","email_thread":"Lance,\n\nWe need one more interviewer for a staff engineer candidate on Friday. The …
  - `criteria` 3/12 → 2/6
- `d7f5b1d40e05` {"email_input":{"author":"Community Pool <info@cityrecreation.org>","email_thread":"Dear Lance,\n\nSummer swimming registration is now open! Based on your daug…
  - `criteria` 9/12 → 3/6, `tool_calls` 12/12 → 4/6
- `d936c521e222` {"email_input":{"author":"GitHub <notifications@github.com>","email_thread":"Hey there!\n\nalex-dev commented on your pull request #42 in langchain-ai/project:…
  - `triage` 6/12 → 4/6
- `e9092291cb7c` {"email_input":{"author":"Team Lead <teamlead@company.com>","email_thread":"Hi Lance,\n\nIt's time for our quarterly planning session. I'd like to schedule a 9…
  - `criteria` 5/12 → 4/6, `tool_calls` 5/12 → 4/6

</details>

### Totals

| Metric | Before | After |
|---|---|---|
| `criteria` | 65/132 | 32/66 |
| `tool_calls` | 70/132 | 34/66 |
| `triage` | 200/240 | 100/120 |

<details><summary>Provenance</summary>

- Before: `main-a + main-b`, local backend, dataset `7514c07d09a6`, 12 repetition(s)
- After: `main-c` at `ee13523`, local backend, dataset `7514c07d09a6`, 6 repetition(s)

</details>
