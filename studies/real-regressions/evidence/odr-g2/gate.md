<!-- flywheel-report -->
## ❌ Flywheel: this change is blocked

Flywheel ran the agent on 16 test cases, 3 times each, and 6 times for the 9 close calls where more runs could change the answer, before and after this change, and compared the results case by case. Result: 16 cases that passed before now fail. Blocked because 16 cases broke (at most 0 allowed); and 16 cases raise an error it did not raise before.

### Broken: passed before, fail now

- `fault-bad-json-args` {"fault":"bad_json_args","question":"Who designed the Varnholt Bridge and in what year was it completed?"}
  - `check_cites` 3/3 → 0/3, `check_clarification` 3/3 → 0/3, `check_facts` 3/3 → 0/3, `check_headings` 3/3 → 0/3, `check_no_forbidden` 3/3 → 0/3, `check_report_produced` 3/3 → 0/3, `check_tools` 3/3 → 0/3
  - new error: `RuntimeError: agent run failed under fault: Traceback (most recent call last):
  File "/home/user/flywheel/studies/real-regressions/runs-heldout/odr/suite/adapter.py", line 392, in <module>
    print(json.dumps(_run(json.loads(sys.stdin.read()))))
                     ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^`
- `fault-unknown-tool` {"fault":"unknown_tool","question":"How many staff does Brannock Logistics employ in total across all of its offices? List each office's headcount and give the…
  - `check_cites` 3/3 → 0/3, `check_clarification` 3/3 → 0/3, `check_facts` 3/3 → 0/3, `check_headings` 3/3 → 0/3, `check_no_forbidden` 3/3 → 0/3, `check_report_produced` 3/3 → 0/3, `check_tools` 3/3 → 0/3
  - new error: `RuntimeError: agent run failed under fault: Traceback (most recent call last):
  File "/home/user/flywheel/studies/real-regressions/runs-heldout/odr/suite/adapter.py", line 392, in <module>
    print(json.dumps(_run(json.loads(sys.stdin.read()))))
                     ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^`
- `g2-chg-clarify-node` {"allow_clarification":true,"question":"Look into this for me please."}
  - `check_cites` 3/3 → 0/3, `check_clarification` 3/3 → 0/3, `check_facts` 3/3 → 0/3, `check_headings` 3/3 → 0/3, `check_no_forbidden` 3/3 → 0/3, `check_report_produced` 3/3 → 0/3, `check_tools` 3/3 → 0/3
  - new error: `AttributeError: type object 'datetime.datetime' has no attribute 'datetime'`
- `g2-chg-clear-with-clarify-on` {"allow_clarification":true,"question":"What default port does Aurel Protocol v3 use, how often must clients send a heartbeat, and in what year was the protoco…
  - `check_cites` 6/6 → 0/6, `check_clarification` 5/6 → 0/6, `check_facts` 4/6 → 0/6, `check_headings` 6/6 → 0/6, `check_no_forbidden` 6/6 → 0/6, `check_report_produced` 6/6 → 0/6, `check_tools` 4/6 → 0/6
  - new error: `AttributeError: type object 'datetime.datetime' has no attribute 'datetime'`
- `g2-chg-launch-age` {"question":"When was the Quillon Q9 launched, and roughly how long before today's date was that?"}
  - `check_cites` 6/6 → 0/6, `check_clarification` 6/6 → 0/6, `check_facts` 2/6 → 0/6, `check_headings` 6/6 → 0/6, `check_no_forbidden` 6/6 → 0/6, `check_report_produced` 6/6 → 0/6, `check_tools` 2/6 → 0/6
  - new error: `AttributeError: type object 'datetime.datetime' has no attribute 'datetime'`
- `g2-chg-years-since` {"question":"As of today's date, how many years ago was the Varnholt Bridge completed? Give the completion year and the number of years."}
  - `check_cites` 3/3 → 0/3, `check_clarification` 3/3 → 0/3, `check_facts` 3/3 → 0/3, `check_headings` 3/3 → 0/3, `check_no_forbidden` 3/3 → 0/3, `check_report_produced` 3/3 → 0/3, `check_tools` 3/3 → 0/3
  - new error: `AttributeError: type object 'datetime.datetime' has no attribute 'datetime'`
- `g2-diff-clarify-need-report` {"allow_clarification":true,"question":"I need a report."}
  - `check_cites` 3/3 → 0/3, `check_clarification` 3/3 → 0/3, `check_facts` 3/3 → 0/3, `check_headings` 3/3 → 0/3, `check_no_forbidden` 3/3 → 0/3, `check_report_produced` 3/3 → 0/3, `check_tools` 3/3 → 0/3
  - new error: `AttributeError: type object 'datetime.datetime' has no attribute 'datetime'`
- `g2-diff-clarify-topicless` {"allow_clarification":true,"question":"Can you dig into that topic for me?"}
  - `check_cites` 3/3 → 0/3, `check_clarification` 3/3 → 0/3, `check_facts` 3/3 → 0/3, `check_headings` 3/3 → 0/3, `check_no_forbidden` 3/3 → 0/3, `check_report_produced` 3/3 → 0/3, `check_tools` 3/3 → 0/3
  - new error: `AttributeError: type object 'datetime.datetime' has no attribute 'datetime'`
- `std-clarify-vague` {"allow_clarification":true,"question":"Write me a report about it."}
  - `check_cites` 3/3 → 0/3, `check_clarification` 3/3 → 0/3, `check_facts` 3/3 → 0/3, `check_headings` 3/3 → 0/3, `check_no_forbidden` 3/3 → 0/3, `check_report_produced` 3/3 → 0/3, `check_tools` 3/3 → 0/3
  - new error: `AttributeError: type object 'datetime.datetime' has no attribute 'datetime'`
- `std-compare-phones` {"question":"Compare the battery capacity and weight of the Quillon Q7 and Quillon Q9 phones, using the official specifications. Which one has the larger batte…
  - `check_cites` 6/6 → 0/6, `check_clarification` 6/6 → 0/6, `check_facts` 3/6 → 0/6, `check_headings` 6/6 → 0/6, `check_no_forbidden` 6/6 → 0/6, `check_report_produced` 6/6 → 0/6, `check_tools` 3/6 → 0/6
  - new error: `AttributeError: type object 'datetime.datetime' has no attribute 'datetime'`
- `std-fact-bridge` {"question":"Who designed the Varnholt Bridge and in what year was it completed?"}
  - `check_cites` 3/6 → 0/6, `check_clarification` 6/6 → 0/6, `check_facts` 3/6 → 0/6, `check_headings` 6/6 → 0/6, `check_no_forbidden` 6/6 → 0/6, `check_report_produced` 6/6 → 0/6, `check_tools` 3/6 → 0/6
  - new error: `AttributeError: type object 'datetime.datetime' has no attribute 'datetime'`
- `std-followup-turn` {"allow_clarification":true,"messages":[{"content":"I need some research on a cheese.","role":"user"},{"content":"Happy to help. Which cheese would you like me…
  - `check_cites` 6/6 → 0/6, `check_clarification` 6/6 → 0/6, `check_facts` 3/6 → 0/6, `check_headings` 6/6 → 0/6, `check_no_forbidden` 6/6 → 0/6, `check_report_produced` 6/6 → 0/6, `check_tools` 3/6 → 0/6
  - new error: `AttributeError: type object 'datetime.datetime' has no attribute 'datetime'`
- `std-mcp-prompt` {"mcp_prompt":"Before any search, always call list_documents first to see the whole catalogue, then read the relevant document with read_document. Cite each do…
  - `check_cites` 6/6 → 0/6, `check_clarification` 6/6 → 0/6, `check_facts` 4/6 → 0/6, `check_headings` 6/6 → 0/6, `check_no_forbidden` 6/6 → 0/6, `check_report_produced` 6/6 → 0/6, `check_tools` 1/6 → 0/6
  - new error: `AttributeError: type object 'datetime.datetime' has no attribute 'datetime'`
- `std-no-clarify-when-off` {"allow_clarification":false,"question":"Give me an overview of the history of the Linmere Tramway."}
  - `check_cites` 6/6 → 0/6, `check_clarification` 6/6 → 0/6, `check_facts` 2/6 → 0/6, `check_headings` 6/6 → 0/6, `check_no_forbidden` 6/6 → 0/6, `check_report_produced` 6/6 → 0/6, `check_tools` 2/6 → 0/6
  - new error: `AttributeError: type object 'datetime.datetime' has no attribute 'datetime'`
- `std-sum-offices` {"question":"How many staff does Brannock Logistics employ in total across all of its offices? List each office's headcount and give the total."}
  - `check_cites` 6/6 → 0/6, `check_clarification` 6/6 → 0/6, `check_facts` 3/6 → 0/6, `check_headings` 6/6 → 0/6, `check_no_forbidden` 6/6 → 0/6, `check_report_produced` 6/6 → 0/6, `check_tools` 3/6 → 0/6
  - new error: `AttributeError: type object 'datetime.datetime' has no attribute 'datetime'`
- `std-two-topic-report` {"question":"Write a short structured report with one section on the Harrowgate Observatory (who founded it, when it opened, its main telescope) and one sectio…
  - `check_cites` 6/6 → 0/6, `check_clarification` 6/6 → 0/6, `check_facts` 1/6 → 0/6, `check_headings` 6/6 → 0/6, `check_no_forbidden` 6/6 → 0/6, `check_report_produced` 6/6 → 0/6, `check_tools` 5/6 → 0/6
  - new error: `AttributeError: type object 'datetime.datetime' has no attribute 'datetime'`

### Totals

| Metric | Before | After |
|---|---|---|
| `check_cites` | 72/75 | 0/75 |
| `check_clarification` | 74/75 | 0/75 |
| `check_facts` | 46/75 | 0/75 |
| `check_headings` | 75/75 | 0/75 |
| `check_no_forbidden` | 75/75 | 0/75 |
| `check_report_produced` | 75/75 | 0/75 |
| `check_tools` | 47/75 | 0/75 |

Sign test over broken and fixed cases: p = 3.05e-05 (the chance of a split at least this uneven if the change did nothing).

<details><summary>Provenance</summary>

- Before: `base` at `539fec6`, local backend, dataset `2e274412eeb0`, 75 run(s)
- After: `head` at `539fec6`, local backend, dataset `2e274412eeb0`, 75 run(s)

</details>
