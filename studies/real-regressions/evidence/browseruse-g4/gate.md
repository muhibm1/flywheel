<!-- flywheel-report -->
## ❌ Flywheel: this change is blocked

Flywheel ran the agent on 16 test cases, 3 times each, and 6 times for the 1 close call where more runs could change the answer, before and after this change, and compared the results case by case. Result: 14 cases that passed before now fail. Blocked because 14 cases broke (at most 0 allowed).

### Broken: passed before, fail now

- `c4-default-openai-agent` {"max_steps":8,"pages":{"/weather.html":"<html><body><h1>Weather in Graz</h1><table border='1'><tr><th>Day</th><th>High</th><th>Low</th></tr><tr><td>Today</td>…
  - `check_answer` 3/3 → 0/3, `check_completed` 3/3 → 0/3
- `c4-output-schema-default` {"max_steps":8,"pages":{"/order.html":"<html><body><h1>Order ORD-55120</h1><ul><li>Notebook x2 - $7.00</li><li>Pen set x1 - $12.50</li><li>Stapler x1 - $9.25</…
  - `check_completed` 3/3 → 0/3, `check_structured` 3/3 → 0/3
- `d4-plain-lookup` {"max_steps":8,"pages":{"/hours.html":"<html><body><h1>Library hours</h1><ul><li>Mon-Fri: 08:00 - 20:00</li><li>Saturday: 10:00 - 16:00</li><li>Sunday: closed<…
  - `check_answer` 3/3 → 0/3, `check_completed` 3/3 → 0/3
- `d4-structured-product-list` {"max_steps":8,"pages":{"/catalog.html":"<html><body><h1>Catalog</h1><div><b>Oak Shelf</b> - $89.00 - In stock</div><div><b>Pine Stool</b> - $45.00 - Sold out<…
  - `check_completed` 3/3 → 0/3, `check_structured` 3/3 → 0/3
- `f4-empty-reply` {"fault":"empty","max_steps":10,"pages":{"/price.html":"<html><body><h1>Granite Mortar</h1><p>Price: $31.40</p></body></html>"},"task":"Open {base}/price.html …
  - `check_answer` 3/3 → 0/3, `check_completed` 3/3 → 0/3
- `f4-truncated-reply` {"fault":"truncated","max_steps":10,"pages":{"/city.html":"<html><body><h1>Brookvale</h1><p>Population: 48,210</p></body></html>"},"task":"Open {base}/city.htm…
  - `check_answer` 3/3 → 0/3, `check_completed` 3/3 → 0/3
- `s-custom-tool` {"max_steps":10,"pages":{"/cart.html":"<html><head><title>Cart</title></head><body><h1>Your cart</h1><ul><li>Desk lamp - SKU A-100 - qty 1</li><li>Office chair…
  - `check_answer` 6/6 → 0/6, `check_completed` 6/6 → 0/6, `check_tools` 3/6 → 0/6
- `s-extract-price` {"max_steps":8,"pages":{"/product.html":"<html><head><title>Trailblazer 2 Tent</title></head><body><h1>Trailblazer 2 Tent</h1><p>A two-person backpacking tent.…
  - `check_answer` 3/3 → 0/3, `check_completed` 3/3 → 0/3
- `s-follow-up` {"follow_up":"Now open the details page of that most recent order and tell me the tracking code.","max_steps":10,"pages":{"/orders.html":"<html><head><title>Or…
  - `check_answer` 3/3 → 0/3, `check_completed` 3/3 → 0/3
- `s-form-submit` {"max_steps":12,"pages":{"/contact.html":"<html><head><title>Contact us</title></head><body><h1>Contact us</h1><form method='post' action='/contact'><label>Nam…
  - `check_answer` 3/3 → 0/3, `check_completed` 3/3 → 0/3, `check_requests` 3/3 → 0/3
- `s-multi-page-nav` {"max_steps":12,"pages":{"/about.html":"<html><body><h1>About us</h1><p>Acme has 40 staff.</p><p>See the <a href='/people/directory.html'>staff directory</a>.<…
  - `check_answer` 3/3 → 0/3, `check_completed` 3/3 → 0/3, `check_requests` 3/3 → 0/3
- `s-search-filter` {"max_steps":10,"pages":{"/books.html":"<html><head><title>Library</title></head><body><h1>Library catalogue</h1><form method='get' action='/search.html'><inpu…
  - `check_answer` 3/3 → 0/3, `check_completed` 3/3 → 0/3, `check_requests` 3/3 → 0/3
- `s-sensitive-login` {"max_steps":10,"pages":{"/login.html":"<html><head><title>Bank login</title></head><body><h1>Sign in</h1><form method='post' action='/session'><label>Username…
  - `check_answer` 3/3 → 0/3, `check_completed` 3/3 → 0/3, `check_requests` 3/3 → 0/3
- `s-structured-product` {"max_steps":8,"pages":{"/item.html":"<html><head><title>Shop</title></head><body><h1>Copper Kettle 1.5L</h1><div class='price'>Price: $42.90</div><div class='…
  - `check_completed` 3/3 → 0/3, `check_structured` 3/3 → 0/3

### Totals

| Metric | Before | After |
|---|---|---|
| `check_answer` | 39/39 | 3/39 |
| `check_completed` | 51/51 | 6/51 |
| `check_requests` | 15/15 | 3/15 |
| `check_structured` | 12/12 | 3/12 |
| `check_tools` | 3/6 | 0/6 |

Sign test over broken and fixed cases: p = 0.000122 (the chance of a split at least this uneven if the change did nothing).

<details><summary>Provenance</summary>

- Before: `base` at `539fec6`, local backend, dataset `937bdcb27ad7`, 51 run(s)
- After: `head` at `539fec6`, local backend, dataset `937bdcb27ad7`, 51 run(s)

</details>
