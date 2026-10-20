<!-- flywheel-report -->
## ❌ Flywheel: this change is blocked

Flywheel ran the agent on 20 test cases, 3 times each, before and after this change, and compared the results case by case. Result: 12 cases that passed before now fail; 2 moved by less than the noise threshold. Blocked because 12 cases broke (at most 0 allowed); and 16 cases raise an error it did not raise before.

### Broken: passed before, fail now

- `16e8090d3b20` {"email_input":{"author":"Lincoln Elementary <office@lincolnelementary.org>","email_thread":"Dear Parent,\n\nYour daughter Emma's class is presenting at the sc…
  - `tool_calls` 3/3 → 0/3, `triage` 3/3 → 0/3
  - new error: `SubscriptionError: headless call failed 3 times: You've hit your session limit · resets 7:10am (UTC)`
- `36cae117a337` {"email_input":{"author":"AWS Monitoring <no-reply@aws.amazon.com>","email_thread":"ALERT: High CPU Utilization\n\nThe following EC2 instance has exceeded the …
  - `triage` 3/3 → 0/3
  - new error: `SubscriptionError: headless call failed 3 times: You've hit your session limit · resets 7:10am (UTC)`
- `48793f4067db` {"email_input":{"author":"Rachel Kim <rachel.kim@company.com>","email_thread":"Hi Lance,\n\nI just joined the applied AI team and would love to pick your brain…
  - `criteria` 1/3 → 0/3, `tool_calls` 1/3 → 0/3, `triage` 3/3 → 0/3
  - new error: `SubscriptionError: headless call failed 3 times: You've hit your session limit · resets 7:10am (UTC)`
- `714903d07aba` {"email_input":{"author":"Dr. Roberts <droberts@medical.org>","email_thread":"Hello Lance,\n\nThis is a reminder that it's time for your annual checkup. Our re…
  - `criteria` 3/3 → 0/3, `tool_calls` 3/3 → 0/3, `triage` 3/3 → 0/3
  - new error: `SubscriptionError: headless call failed 3 times: You've hit your session limit · resets 7:10am (UTC)`
- `782e6b5fb339` {"email_input":{"author":"Social Media Platform <notifications@social.com>","email_thread":"Hi Lance,\n\n5 people liked your recent post about \"Machine Learni…
  - `triage` 3/3 → 0/3
  - new error: `SubscriptionError: headless call failed 3 times: You've hit your session limit · resets 7:10am (UTC)`
- `7ef49c4cebe7` {"email_input":{"author":"Client Success <success@vendor.com>","email_thread":"Hello Lance,\n\nThis is a friendly reminder that your annual subscription to our…
  - `triage` 3/3 → 0/3
  - new error: `SubscriptionError: headless call failed 3 times: You've hit your session limit · resets 7:10am (UTC)`
- `7fd34b3c68ac` {"email_input":{"author":"CI Bot <ci@company.com>","email_thread":"Build #4821 on main FAILED.\n\nStage: integration-tests\nFailed test: test_streaming_metadat…
  - `triage` 3/3 → 0/3
  - new error: `SubscriptionError: headless call failed 3 times: You've hit your session limit · resets 7:10am (UTC)`
- `b04a1ebbfaa5` {"email_input":{"author":"Project Team <project@company.com>","email_thread":"Hi Lance,\n\nThe leadership team has asked us to prepare a joint presentation on …
  - `triage` 3/3 → 0/3
  - new error: `SubscriptionError: headless call failed 3 times: You've hit your session limit · resets 7:10am (UTC)`
- `b1391c55ef27` {"email_input":{"author":"Omar Haddad <omar@company.com>","email_thread":"Lance,\n\nWe need one more interviewer for a staff engineer candidate on Friday. The …
  - `criteria` 1/3 → 0/3, `triage` 3/3 → 0/3
  - new error: `SubscriptionError: headless call failed 3 times: You've hit your session limit · resets 7:10am (UTC)`
- `d7f5b1d40e05` {"email_input":{"author":"Community Pool <info@cityrecreation.org>","email_thread":"Dear Lance,\n\nSummer swimming registration is now open! Based on your daug…
  - `criteria` 2/3 → 0/3, `tool_calls` 3/3 → 0/3, `triage` 3/3 → 0/3
  - new error: `SubscriptionError: headless call failed 3 times: You've hit your session limit · resets 7:10am (UTC)`
- `e9092291cb7c` {"email_input":{"author":"Team Lead <teamlead@company.com>","email_thread":"Hi Lance,\n\nIt's time for our quarterly planning session. I'd like to schedule a 9…
  - `criteria` 1/3 → 0/3, `tool_calls` 1/3 → 0/3, `triage` 3/3 → 0/3
  - new error: `SubscriptionError: headless call failed 3 times: You've hit your session limit · resets 7:10am (UTC)`
- `f390e1681d84` {"email_input":{"author":"Sarah Johnson <sarah.j@partner.com>","email_thread":"Lance,\n\nI've attached the final version of our proposal for the Henderson proj…
  - `criteria` 3/3 → 0/3, `tool_calls` 3/3 → 0/3, `triage` 3/3 → 0/3
  - new error: `SubscriptionError: headless call failed 3 times: You've hit your session limit · resets 7:10am (UTC)`

<details><summary>Wobbling: changed by less than the threshold (reported, not blocking) (2)</summary>

- `cfcf4580193e` {"email_input":{"author":"HR Department <hr@company.com>","email_thread":"Hello Lance,\n\nThis is a friendly reminder that all expense reports for the previous…
  - `triage` 3/3 → 2/3
  - new error: `SubscriptionError: headless call failed 3 times: You've hit your session limit · resets 7:10am (UTC)`
- `d936c521e222` {"email_input":{"author":"GitHub <notifications@github.com>","email_thread":"Hey there!\n\nalex-dev commented on your pull request #42 in langchain-ai/project:…
  - `triage` 1/3 → 0/3
  - new error: `SubscriptionError: headless call failed 3 times: You've hit your session limit · resets 7:10am (UTC)`

</details>

### Totals

| Metric | Before | After |
|---|---|---|
| `criteria` | 14/54 | 3/54 |
| `tool_calls` | 17/54 | 3/54 |
| `triage` | 49/60 | 11/60 |

Sign test over broken and fixed cases: p = 0.000488 (the chance of a split at least this uneven if the change did nothing).

<details><summary>Provenance</summary>

- Before: `main-a` at `d83036f`, local backend, dataset `7514c07d09a6`, 3 repetition(s)
- After: `main-b` at `d83036f`, local backend, dataset `7514c07d09a6`, 3 repetition(s)

</details>
