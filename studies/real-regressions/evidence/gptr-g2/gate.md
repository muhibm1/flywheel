<!-- flywheel-report -->
## ❌ Flywheel: this change is blocked

Flywheel ran the agent on 15 test cases, 3 times each, and 6 times for the 1 close call where more runs could change the answer, before and after this change, and compared the results case by case. Result: 15 cases that passed before now fail. Blocked because 15 cases broke (at most 0 allowed); and 15 cases raise an error it did not raise before.

### Broken: passed before, fail now

- `custom-report-json` {"docs":{"brannoch.txt":"The Brannoch Observatory\n\nThe Brannoch Observatory sits on Carn Liath in the Scottish Highlands. It was founded by the amateur astro…
  - `check_completed` 3/3 → 0/3, `check_facts` 3/3 → 0/3, `check_format` 3/3 → 0/3, `check_no_forbidden` 3/3 → 0/3, `check_search_results` 3/3 → 0/3, `check_sources` 3/3 → 0/3
  - new error: `RuntimeError: research run failed (exit 1):
Traceback (most recent call last):
  File "/tmp/rr/blind/gptr/suite/runner.py", line 389, in <module>
    main()
  File "/tmp/rr/blind/gptr/suite/runner.py", line 378, in main
    out = asyncio.run(run(inputs, workdir, site))
          ^^^^^^^^^^^^^^^^^^^^`
- `g2-diff-custom-report-web` {"pages":{"brask-railway":{"text":"The Brask Valley railway opened in 1884 and linked the river town of Holm Ferry to the coal port of Ostrand. It was built by…
  - `check_completed` 3/3 → 0/3, `check_facts` 3/3 → 0/3, `check_format` 3/3 → 0/3, `check_no_forbidden` 3/3 → 0/3, `check_search_results` 3/3 → 0/3, `check_sources` 3/3 → 0/3
  - new error: `RuntimeError: research run failed (exit 1):
Traceback (most recent call last):
  File "/tmp/rr/blind/gptr/suite/runner.py", line 389, in <module>
    main()
  File "/tmp/rr/blind/gptr/suite/runner.py", line 378, in main
    out = asyncio.run(run(inputs, workdir, site))
          ^^^^^^^^^^^^^^^^^^^^`
- `g2-diff-outline-local-docs` {"docs":{"quillfeather.txt":"Quillfeather Bakery is a worker cooperative in Ghent, Belgium, founded in 2014. Each of its 31 worker-members holds one vote.\n\nQ…
  - `check_completed` 3/3 → 0/3, `check_facts` 3/3 → 0/3, `check_format` 3/3 → 0/3, `check_no_forbidden` 3/3 → 0/3, `check_search_results` 3/3 → 0/3, `check_sources` 3/3 → 0/3
  - new error: `RuntimeError: research run failed (exit 1):
Traceback (most recent call last):
  File "/tmp/rr/blind/gptr/suite/runner.py", line 389, in <module>
    main()
  File "/tmp/rr/blind/gptr/suite/runner.py", line 378, in main
    out = asyncio.run(run(inputs, workdir, site))
          ^^^^^^^^^^^^^^^^^^^^`
- `g2-fault-call-as-text` {"fault":"call_as_text","max_iterations":1,"pages":{"brask-railway":{"text":"The Brask Valley railway opened in 1884 and linked the river town of Holm Ferry to…
  - `check_completed` 3/3 → 0/3, `check_facts` 3/3 → 0/3, `check_format` 3/3 → 0/3, `check_no_forbidden` 3/3 → 0/3, `check_search_results` 3/3 → 0/3, `check_sources` 3/3 → 0/3
  - new error: `RuntimeError: research run failed (exit 1):
Traceback (most recent call last):
  File "/tmp/rr/blind/gptr/suite/runner.py", line 389, in <module>
    main()
  File "/tmp/rr/blind/gptr/suite/runner.py", line 378, in main
    out = asyncio.run(run(inputs, workdir, site))
          ^^^^^^^^^^^^^^^^^^^^`
- `g2-fault-empty` {"fault":"empty","max_iterations":1,"pages":{"vorna-char-decline":{"text":"Surveys of the silver char in Lake Vorna found the spawning population fell by about…
  - `check_completed` 3/3 → 0/3, `check_facts` 3/3 → 0/3, `check_format` 3/3 → 0/3, `check_no_forbidden` 3/3 → 0/3, `check_search_results` 3/3 → 0/3, `check_sources` 3/3 → 0/3
  - new error: `RuntimeError: research run failed (exit 1):
Traceback (most recent call last):
  File "/tmp/rr/blind/gptr/suite/runner.py", line 389, in <module>
    main()
  File "/tmp/rr/blind/gptr/suite/runner.py", line 378, in main
    out = asyncio.run(run(inputs, workdir, site))
          ^^^^^^^^^^^^^^^^^^^^`
- `g2-local-docs-planning` {"docs":{"zephyr_company.txt":"Zephyr Mosaics company profile\n\nZephyr Mosaics is a small glass-tile manufacturer. It was founded in 2009 in Tallinn, Estonia,…
  - `check_completed` 3/3 → 0/3, `check_facts` 3/3 → 0/3, `check_format` 3/3 → 0/3, `check_no_forbidden` 3/3 → 0/3, `check_search_results` 3/3 → 0/3, `check_sources` 3/3 → 0/3
  - new error: `RuntimeError: research run failed (exit 1):
Traceback (most recent call last):
  File "/tmp/rr/blind/gptr/suite/runner.py", line 389, in <module>
    main()
  File "/tmp/rr/blind/gptr/suite/runner.py", line 378, in main
    out = asyncio.run(run(inputs, workdir, site))
          ^^^^^^^^^^^^^^^^^^^^`
- `g2-query-with-json-characters` {"pages":{"kestrel-intro":{"text":"Kestrel-9 is a statically typed programming language first released in 2021 by the Halvard Compiler Group. Programs are orga…
  - `check_completed` 3/3 → 0/3, `check_facts` 3/3 → 0/3, `check_format` 3/3 → 0/3, `check_no_forbidden` 3/3 → 0/3, `check_search_results` 3/3 → 0/3, `check_sources` 3/3 → 0/3
  - new error: `RuntimeError: research run failed (exit 1):
Traceback (most recent call last):
  File "/tmp/rr/blind/gptr/suite/runner.py", line 389, in <module>
    main()
  File "/tmp/rr/blind/gptr/suite/runner.py", line 378, in main
    out = asyncio.run(run(inputs, workdir, site))
          ^^^^^^^^^^^^^^^^^^^^`
- `g2-single-iteration` {"max_iterations":1,"pages":{"vorna-char-decline":{"text":"Surveys of the silver char in Lake Vorna found the spawning population fell by about 70 percent betw…
  - `check_completed` 3/3 → 0/3, `check_facts` 3/3 → 0/3, `check_format` 3/3 → 0/3, `check_no_forbidden` 3/3 → 0/3, `check_search_results` 3/3 → 0/3, `check_sources` 3/3 → 0/3
  - new error: `RuntimeError: research run failed (exit 1):
Traceback (most recent call last):
  File "/tmp/rr/blind/gptr/suite/runner.py", line 389, in <module>
    main()
  File "/tmp/rr/blind/gptr/suite/runner.py", line 378, in main
    out = asyncio.run(run(inputs, workdir, site))
          ^^^^^^^^^^^^^^^^^^^^`
- `g2-subqueries-web-research` {"pages":{"brask-railway":{"text":"The Brask Valley railway opened in 1884 and linked the river town of Holm Ferry to the coal port of Ostrand. It was built by…
  - `check_completed` 3/3 → 0/3, `check_facts` 3/3 → 0/3, `check_format` 3/3 → 0/3, `check_no_forbidden` 3/3 → 0/3, `check_search_results` 3/3 → 0/3, `check_sources` 3/3 → 0/3
  - new error: `RuntimeError: research run failed (exit 1):
Traceback (most recent call last):
  File "/tmp/rr/blind/gptr/suite/runner.py", line 389, in <module>
    main()
  File "/tmp/rr/blind/gptr/suite/runner.py", line 378, in main
    out = asyncio.run(run(inputs, workdir, site))
          ^^^^^^^^^^^^^^^^^^^^`
- `langchain-documents` {"langchain_documents":[{"source":"quillfeather-charter","text":"Quillfeather Bakery is a worker cooperative in Ghent, Belgium, founded in 2014. Each of its 31…
  - `check_completed` 6/6 → 0/6, `check_facts` 5/6 → 0/6, `check_format` 6/6 → 0/6, `check_no_forbidden` 6/6 → 0/6, `check_search_results` 6/6 → 0/6, `check_sources` 6/6 → 0/6
  - new error: `RuntimeError: research run failed (exit 1):
Traceback (most recent call last):
  File "/tmp/rr/blind/gptr/suite/runner.py", line 389, in <module>
    main()
  File "/tmp/rr/blind/gptr/suite/runner.py", line 378, in main
    out = asyncio.run(run(inputs, workdir, site))
          ^^^^^^^^^^^^^^^^^^^^`
- `local-docs-company-history` {"docs":{"zephyr_company.txt":"Zephyr Mosaics company profile\n\nZephyr Mosaics is a small glass-tile manufacturer. It was founded in 2009 in Tallinn, Estonia,…
  - `check_completed` 3/3 → 0/3, `check_facts` 3/3 → 0/3, `check_format` 3/3 → 0/3, `check_no_forbidden` 3/3 → 0/3, `check_search_results` 3/3 → 0/3, `check_sources` 3/3 → 0/3
  - new error: `RuntimeError: research run failed (exit 1):
Traceback (most recent call last):
  File "/tmp/rr/blind/gptr/suite/runner.py", line 389, in <module>
    main()
  File "/tmp/rr/blind/gptr/suite/runner.py", line 378, in main
    out = asyncio.run(run(inputs, workdir, site))
          ^^^^^^^^^^^^^^^^^^^^`
- `outline-report-vorna` {"pages":{"vorna-char-decline":{"text":"Surveys of the silver char in Lake Vorna found the spawning population fell by about 70 percent between 1998 and 2015. …
  - `check_completed` 3/3 → 0/3, `check_facts` 3/3 → 0/3, `check_format` 3/3 → 0/3, `check_no_forbidden` 3/3 → 0/3, `check_search_results` 3/3 → 0/3, `check_sources` 3/3 → 0/3
  - new error: `RuntimeError: research run failed (exit 1):
Traceback (most recent call last):
  File "/tmp/rr/blind/gptr/suite/runner.py", line 389, in <module>
    main()
  File "/tmp/rr/blind/gptr/suite/runner.py", line 378, in main
    out = asyncio.run(run(inputs, workdir, site))
          ^^^^^^^^^^^^^^^^^^^^`
- `resource-report-kestrel` {"pages":{"kestrel-intro":{"text":"Kestrel-9 is a statically typed programming language first released in 2021 by the Halvard Compiler Group. Programs are orga…
  - `check_completed` 3/3 → 0/3, `check_facts` 3/3 → 0/3, `check_format` 3/3 → 0/3, `check_no_forbidden` 3/3 → 0/3, `check_search_results` 3/3 → 0/3, `check_sources` 3/3 → 0/3
  - new error: `RuntimeError: research run failed (exit 1):
Traceback (most recent call last):
  File "/tmp/rr/blind/gptr/suite/runner.py", line 389, in <module>
    main()
  File "/tmp/rr/blind/gptr/suite/runner.py", line 378, in main
    out = asyncio.run(run(inputs, workdir, site))
          ^^^^^^^^^^^^^^^^^^^^`
- `source-urls-only` {"complement_source_urls":false,"pages":{"kestrel-intro":{"text":"Kestrel-9 is a statically typed programming language first released in 2021 by the Halvard Co…
  - `check_completed` 3/3 → 0/3, `check_facts` 3/3 → 0/3, `check_format` 3/3 → 0/3, `check_no_forbidden` 3/3 → 0/3, `check_search_results` 3/3 → 0/3, `check_sources` 3/3 → 0/3
  - new error: `RuntimeError: research run failed (exit 1):
Traceback (most recent call last):
  File "/tmp/rr/blind/gptr/suite/runner.py", line 389, in <module>
    main()
  File "/tmp/rr/blind/gptr/suite/runner.py", line 378, in main
    out = asyncio.run(run(inputs, workdir, site))
          ^^^^^^^^^^^^^^^^^^^^`
- `web-research-lake-vorna` {"pages":{"vorna-char-decline":{"text":"Surveys of the silver char in Lake Vorna found the spawning population fell by about 70 percent between 1998 and 2015. …
  - `check_completed` 3/3 → 0/3, `check_facts` 3/3 → 0/3, `check_format` 3/3 → 0/3, `check_no_forbidden` 3/3 → 0/3, `check_search_results` 3/3 → 0/3, `check_sources` 3/3 → 0/3
  - new error: `RuntimeError: research run failed (exit 1):
Traceback (most recent call last):
  File "/tmp/rr/blind/gptr/suite/runner.py", line 389, in <module>
    main()
  File "/tmp/rr/blind/gptr/suite/runner.py", line 378, in main
    out = asyncio.run(run(inputs, workdir, site))
          ^^^^^^^^^^^^^^^^^^^^`

### Totals

| Metric | Before | After |
|---|---|---|
| `check_completed` | 48/48 | 0/48 |
| `check_facts` | 47/48 | 0/48 |
| `check_format` | 48/48 | 0/48 |
| `check_no_forbidden` | 48/48 | 0/48 |
| `check_search_results` | 48/48 | 0/48 |
| `check_sources` | 48/48 | 0/48 |

Sign test over broken and fixed cases: p = 6.1e-05 (the chance of a split at least this uneven if the change did nothing).

<details><summary>Provenance</summary>

- Before: `base` at `539fec6`, local backend, dataset `b77103de0e04`, 48 run(s)
- After: `head` at `539fec6`, local backend, dataset `b77103de0e04`, 48 run(s)

</details>
