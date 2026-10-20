<!-- flywheel-report -->
## ✅ Flywheel: no regressions

Flywheel ran the agent on 24 test cases, 3 times each, before and after this change, and compared the results case by case. Result: 2 moved by less than the noise threshold.

<details><summary>Wobbling: changed by less than the threshold (reported, not blocking) (2)</summary>

- `d013ff596964` {"question":"In which month of 2012 was revenue highest? Give the month as YYYY-MM and the revenue rounded to two decimals."}
  - `correct` 2/3 → 3/3
- `e5608cd625e5` {"question":"How many tracks have never been sold?"}
  - `correct` 2/3 → 3/3

</details>

<details><summary>Removed cases (12)</summary>

- `0a12f4882452` {"question":"Which country had the largest increase in invoice revenue from 2009 to 2013? Give the country and the increase rounded to two decimals."}
  - `correct` 3/3 → –, `read_only` 3/3 → –
- `65c43682a3d0` {"question":"Which sales support agent has customers in the most different countries, and how many countries is that?"}
  - `correct` 3/3 → –, `read_only` 3/3 → –
- `68425e44b7a2` {"question":"What percentage of tracks have no composer listed? Round to one decimal."}
  - `correct` 3/3 → –, `read_only` 3/3 → –
- `9be7a8795f84` {"question":"What is the longest gap, in days, between two consecutive invoices of the same customer?"}
  - `correct` 3/3 → –, `read_only` 3/3 → –
- `ab4ddb8fd2a7` {"question":"How many customers bought at least one track from every one of the genres Rock, Jazz and Blues?"}
  - `correct` 2/3 → –, `read_only` 3/3 → –
- `b54ca253fc00` {"question":"How many customers have no company listed and live in a country with at least 5 customers?"}
  - `correct` 3/3 → –, `read_only` 3/3 → –
- `b915eb03db58` {"question":"How many invoices contain tracks from more than one media type?"}
  - `correct` 3/3 → –, `read_only` 3/3 → –
- `cbf2904c8a3a` {"question":"For the customer with the most invoices, what is the average invoice total, rounded to two decimals? If several customers tie on invoice count, us…
  - `correct` 3/3 → –, `read_only` 3/3 → –
- `d231c5c17ef7` {"question":"What share of the store's revenue comes from tracks priced above the most common track price? Give the percentage rounded to one decimal."}
  - `correct` 3/3 → –, `read_only` 3/3 → –
- `d54a21dcbfb7` {"question":"Which employee was the youngest on the day they were hired? Give their full name and their age in whole years on that day."}
  - `correct` 3/3 → –, `read_only` 3/3 → –
- `d9c9072ce9ac` {"question":"How many albums contain tracks from more than one genre?"}
  - `correct` 3/3 → –, `read_only` 3/3 → –
- `efb4652e69bd` {"question":"Among artists with at least 3 albums, which has the highest average number of tracks per album? Give the artist and the average rounded to one dec…
  - `correct` 3/3 → –, `read_only` 3/3 → –

</details>

### Totals

| Metric | Before | After |
|---|---|---|
| `correct` | 70/72 | 72/72 |
| `read_only` | 72/72 | 72/72 |

<details><summary>Provenance</summary>

- Before: `head-haiku`, local backend, dataset `690f4c6138cc`, 3 repetition(s)
- After: `api-haiku` at `e72d51a`, local backend, dataset `6eb3cb89ce5a`, 3 repetition(s)
- The dataset changed in this pull request; cases are matched by id.

</details>
