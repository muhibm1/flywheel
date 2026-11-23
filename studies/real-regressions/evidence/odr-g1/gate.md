<!-- flywheel-report -->
## ❌ Flywheel: this change is blocked

Flywheel ran the agent on 16 test cases, 3 times each, and 6 times for the 8 close calls where more runs could change the answer, before and after this change, and compared the results case by case. Result: 5 cases that passed before now fail; 3 moved by less than the noise threshold. Blocked because 5 cases broke (at most 0 allowed).

### Broken: passed before, fail now

- `g1-chg-three-way-timeline` {"question":"Put these three events in chronological order and give the year of each: the first opening of the Linmere Tramway, the opening of the Harrowgate O…
  - `check_facts` 3/6 → 0/6, `check_tools` 4/6 → 3/6
- `std-compare-phones` {"question":"Compare the battery capacity and weight of the Quillon Q7 and Quillon Q9 phones, using the official specifications. Which one has the larger batte…
  - `check_facts` 6/6 → 3/6, `check_tools` 6/6 → 3/6
- `std-mcp-prompt` {"mcp_prompt":"Before any search, always call list_documents first to see the whole catalogue, then read the relevant document with read_document. Cite each do…
  - `check_facts` 5/6 → 3/6, `check_tools` 5/6 → 0/6
- `std-no-clarify-when-off` {"allow_clarification":false,"question":"Give me an overview of the history of the Linmere Tramway."}
  - `check_facts` 3/3 → 0/3, `check_tools` 3/3 → 0/3
- `std-sum-offices` {"question":"How many staff does Brannock Logistics employ in total across all of its offices? List each office's headcount and give the total."}
  - `check_facts` 5/6 → 2/6, `check_tools` 5/6 → 2/6

<details><summary>Wobbling: changed by less than the threshold (reported, not blocking) (3)</summary>

- `g1-chg-one-unit-two-topics` {"max_concurrent_research_units":1,"question":"Answer two things: how long is the Kestrel River, and what default port does Aurel Protocol v3 use?"}
  - `check_tools` 3/6 → 5/6
- `std-fact-bridge` {"question":"Who designed the Varnholt Bridge and in what year was it completed?"}
  - `check_cites` 4/6 → 2/6, `check_facts` 4/6 → 2/6, `check_tools` 4/6 → 2/6
- `std-two-topic-report` {"question":"Write a short structured report with one section on the Harrowgate Observatory (who founded it, when it opened, its main telescope) and one sectio…
  - `check_facts` 2/6 → 0/6, `check_tools` 6/6 → 4/6

</details>

### Totals

| Metric | Before | After |
|---|---|---|
| `check_cites` | 68/72 | 66/72 |
| `check_clarification` | 72/72 | 72/72 |
| `check_facts` | 46/72 | 28/72 |
| `check_headings` | 72/72 | 72/72 |
| `check_no_forbidden` | 72/72 | 72/72 |
| `check_report_produced` | 72/72 | 72/72 |
| `check_tools` | 54/72 | 37/72 |

Sign test over broken and fixed cases: p = 0.0625 (the chance of a split at least this uneven if the change did nothing).

<details><summary>Provenance</summary>

- Before: `base` at `539fec6`, local backend, dataset `d1f0552b032e`, 72 run(s)
- After: `head` at `539fec6`, local backend, dataset `d1f0552b032e`, 72 run(s)

</details>
