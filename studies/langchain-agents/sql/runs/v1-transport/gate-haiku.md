<!-- flywheel-report -->
## ❌ Flywheel: this change is blocked

Flywheel ran the agent on 24 test cases, 3 times each, before and after this change, and compared the results case by case. Result: 1 case that passed before now fails; 9 moved by less than the noise threshold. Blocked because 1 case broke (at most 0 allowed).

### Broken: passed before, fail now

- `967bae3075b7` {"question":"Which artist has the most albums in the store, and how many albums do they have?"}
  - `correct` 3/3 → 1/3

<details><summary>Wobbling: changed by less than the threshold (reported, not blocking) (9)</summary>

- `109826cfaa8d` {"question":"Which media type has sold the most units (invoice line quantities), and how many units?"}
  - `correct` 2/3 → 3/3
- `3e9c36acf413` {"question":"How many tracks are longer than 10 minutes?"}
  - `correct` 2/3 → 3/3, `read_only` 2/3 → 3/3
- `42c328847fd6` {"question":"How many employees report directly to the General Manager?"}
  - `read_only` 2/3 → 3/3
- `54b8bbc25c54` {"question":"Which playlist contains the most tracks from the 'Rock' genre, and how many Rock tracks does it contain? Count each track once."}
  - `correct` 3/3 → 2/3
- `7ab000f5a063` {"question":"Which country's customers spent the most in total, and what was that total, rounded to two decimals?"}
  - `correct` 2/3 → 3/3
- `81b8e52098ed` {"question":"Which genre has the most tracks, and how many tracks is that?"}
  - `correct` 2/3 → 3/3
- `8c2b9661e7c5` {"question":"What is the total of all invoices issued in 2011, rounded to two decimals?"}
  - `read_only` 2/3 → 3/3
- `bf6e91ff48f6` {"question":"How many artists have no albums in the store?"}
  - `correct` 2/3 → 1/3
- `d013ff596964` {"question":"In which month of 2012 was revenue highest? Give the month as YYYY-MM and the revenue rounded to two decimals."}
  - `correct` 3/3 → 2/3

</details>

### Totals

| Metric | Before | After |
|---|---|---|
| `correct` | 62/72 | 61/72 |
| `read_only` | 69/72 | 72/72 |

Sign test over broken and fixed cases: p = 1 (the chance of a split at least this uneven if the change did nothing).

<details><summary>Provenance</summary>

- Before: `base-sonnet45` at `161b913`, local backend, dataset `6eb3cb89ce5a`, 3 repetition(s)
- After: `head-haiku` at `161b913`, local backend, dataset `6eb3cb89ce5a`, 3 repetition(s)

</details>
