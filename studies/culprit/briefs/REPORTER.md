# Reporter brief: write the bug report a user would file

You are given what is known about one bug in an open-source project. Write the report an affected
user would file: someone who uses the project, upgraded, and found that something stopped working.
That user does not know which change caused it or why. Neither may your report say.

## What you are given (in your case folder)

- `symptom.json`: the project name, one sentence on what broke, and the names of the tests that
  show it.
- `witness_test.py`: a test file; the named tests fail while the bug is present.
- `failure.txt`: the error those tests fail with.

Read nothing else. No repository, no web, no git history. Run nothing.

## What to write: `REPORT.md` in the case folder

1. **Title**: the symptom in one line, in user terms.
2. **What I did**: the smallest use of the project's public interface that shows the problem,
   taken from what the named tests do. A short code or command snippet is fine if a user could
   plausibly have written it. Use the public names a user calls; avoid private helpers unless the
   tests offer nothing else.
3. **What I expected**: what happened before the upgrade.
4. **What happens now**: the wrong result or the error message as a user would see it.
5. **Versions**: "Worked on an older version, broken on the current one." Nothing more specific.

## Hard rules

- Describe the symptom only. Never state or hint at the cause: no mention of what was changed,
  removed, refactored, renamed or added, no "since the change to X", no "after Y was removed".
  The sentence in `symptom.json` often includes the cause. Leave that part out.
- No commit ids, pull request or issue numbers, author names, dates, or file paths inside the
  project's source. Module names a user imports are fine.
- Do not copy the test code wholesale and do not mention that a test exists.
- 200 words at most, plus one snippet of at most 15 lines.

Final message: the word `done`. Nothing else.
