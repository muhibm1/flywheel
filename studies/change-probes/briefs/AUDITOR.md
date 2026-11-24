# Witness auditor brief

You check the answer key of a code-review study. A labeller has claimed that some changes are
regressions and saved a witness test for each. You decide, independently, whether each claim is
sound. Everything you read and write is an answer key: write only into the sealed folder named in
your task, and report only counts. Read `briefs/SHELL_RULES.md` (next to this file) first.

## Input

`labelled/<project>.json` in the sealed folder. Audit only rows with `"kept": true`. The witness
file for a row is under `witnesses/<project>/<intro_sha[:10]>/`. The clone is at the path named in
your task. You do not build an environment or run tests; you read.

## For each kept row, answer four questions

1. **Does the witness run the project's code and check what it does?** It must call project code
   and assert on a returned value, a raised exception or an action taken. Reject a witness that
   reads source text or a requirements file, checks only that something can be imported or that a
   name or signature exists, or mocks so much that the changed code never runs.
2. **Does the head failure describe behaviour?** `head_failure` must be an assertion or an error
   raised by the behaviour under test. Reject ImportError, ModuleNotFoundError, a missing fixture,
   a collection error, or an AttributeError/TypeError for a name or argument that only exists
   after the fix (check with `git -C <clone> show <intro_sha>:<path>`).
3. **Does the introducing change cause it?** Read `git -C <clone> show --stat <intro_sha>` and the
   relevant part of the diff against `base_sha`. The code the witness exercises must be code this
   change touched or directly affected, and the described breakage must follow from the diff.
   Reject when the link is not visible.
4. **Is it a real loss for a user of the project?** The witness must check something a caller of
   the project could rely on at base. Reject a witness that pins an internal detail no caller
   would notice (a private helper's exact output, log wording, ordering nobody documents).
   Also check `base_sha` is the first parent of `intro_sha` (`git rev-parse <intro_sha>^1`), the
   fix is a different change from the introducing one and comes later, and `intro_date` is on or
   after 2026-07-01.

Be strict: when unsure, reject. A wrongly kept row damages the study more than a lost row.

## Output

Write `audited/<project>.json` in the sealed folder (create the folder with `mkdir -p`): the same
list as the labelled file, every row unchanged except that each row that was kept gains

```json
"audit": {"behavioural": true, "failure_is_behaviour": true, "caused_by_intro": true,
          "user_visible": true, "history_ok": true, "note": "one sentence"}
```

and `"kept"` becomes false, with `"dropped": "audit: <reason>"`, when any answer is false.
Final message: per project, rows audited, kept, rejected by question number. Nothing else.
