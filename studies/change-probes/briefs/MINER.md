# Miner brief

You find real regressions in open-source projects: a change that a team merged and later had to
fix or revert because something that used to work stopped working. Other agents will later be
tested on whether they can spot these changes without knowing the outcome, so what you write is
an answer key. Keep it out of every folder except the sealed one named in your task, and report
only counts in your final message. Read `briefs/SHELL_RULES.md` (next to this file) first.

## For each project you are given

1. Clone it once: `git clone --filter=blob:none <url> <root>/clones/<name>`.
2. Find fix or revert commits on the default branch dated on or after 2026-07-01 whose own text
   names an earlier change as the cause. Search commit messages (`git -C <clone> log
   --since=2026-07-01 -i -E --grep=<pattern> --format=...`) for patterns such as: `regression`,
   `revert`, `introduced (in|by)`, `broke`, `broken (by|since|in)`, `caused by`, `since #`,
   `after #`, `fix.*#[0-9]+`, `follow-?up`, `restore`, `no longer`, `stopped working`. Also search
   merged pull requests and closed issues with `gh api -X GET search/issues -f q="repo:<owner>/<repo>
   regression merged:>2026-07-01"` and similar queries. Read each hit; most are not what we need.
3. For each hit, identify the **introducing change** (a commit on the default branch). Keep the
   pair only if all hold:
   - The team's own words (fix message, pull request text, linked issue by a maintainer) name the
     introducing change, by pull request number, commit or an unambiguous description, **and** say
     what got worse. A bare "Revert X" with no reason is out.
   - The introducing commit is dated on or after 2026-07-01 and is on the default branch.
   - Something that worked before the introducing change stopped working after it. A bug inside a
     brand-new feature that never worked is out.
   - The introducing change touches source code (not only docs, CI, or dependency pins) and is at
     most 2,000 changed source lines.
   - The breakage can plausibly be shown by a repeatable test without a live language model and
     without a paid service. If it exists only as a live model responding worse to reworded prompt
     text, record it with `"needs_live_model": true` (it is counted, not used).
4. Write one JSON file per project to the sealed folder, a list of rows:

```json
{"repo": "owner/name", "intro_sha": "...", "intro_pr": 123, "intro_date": "2026-08-14",
 "intro_title": "...", "base_sha": "<first parent of intro_sha>",
 "fix_sha": "...", "fix_pr": 456, "fix_date": "...",
 "team_quote": "the team's words naming the cause and the harm", "quote_source": "fix commit message | PR #456 body | issue #400",
 "what_broke": "one plain sentence",
 "fix_adds_test": true, "fix_test_paths": ["tests/..."],
 "changed_source_lines": 180, "needs_live_model": false,
 "confidence": "high | medium", "notes": ""}
```

`confidence` is `high` only when the team names the introducing change explicitly. Use `medium`
when you had to pin it with `git log -S`, blame or bisect-by-reading and the evidence is strong.
Drop anything weaker.

Be thorough: read the whole window, not the first page of results. Be strict: a wrong row poisons
the key. Final message: per project, the number of hits read, rows kept at high and at medium
confidence, and rows marked `needs_live_model`. Nothing else about the rows.
