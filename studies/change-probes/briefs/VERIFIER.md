# Verifier brief

Two reviewers studied a code change and claim that some things which worked on the old code
(base) no longer work on the new code (head). You are the independent check, and your default is
doubt: a wrongly blocked change costs a team real time. Throw out every claim that does not hold
up. Keep every claim that does. You do not know whether this change is fine or broken.

Read `briefs/SHELL_RULES.md` (next to this file) first. The same limits apply: work only in the
gate folder, no network look-ups about the project, no real model.

## What you have

The gate folder: `CHANGE.md`, `change.diff`, `base/`, `head/`, both venvs, `probes/`,
`results.json`, and `findings_final.json` (or `findings.json` if there was no second pass). Do
not read `ledger.json`, `gap_ledger.json` or `HUNT_NOTES.md`: judge the evidence, not the
reviewers' reasoning.

## For every finding whose `effect` is `loss`

1. **Rerun it.** `<gate>/venv-head/bin/python /home/user/flywheel/studies/change-probes/run_probes.py <gate> --only <probe>`.
   It must again pass every run on base and fail every run on head.
2. **Read the probe line by line.** Does it fail on head for the reason the finding says? A probe
   that fails for a different reason (an import, a helper, a timing check, a pinned message
   string) proves nothing. Does its base expectation describe real base behaviour, or something
   the probe's own scaffolding produced?
3. **Entry point.** Does it go through an interface the project documents or exports for users?
   A probe that reaches into underscore-prefixed helpers, or builds internal objects by hand in a
   way no user would, is `contrived` unless the public route demonstrably reaches the same code
   with the same input.
4. **Effect.** Is the user worse off? `loss` means an outcome that base delivered is not delivered
   at head: a result became an exception, an action no longer happens, a run ends early or empty,
   valid input is now rejected, a user's setup is discarded. If base crashed or gave a wrong
   answer and head does better, it is `gain_or_repair`. If the outcome is the same in another
   form (wording, order, extra fields, logs, an extra internal step that still ends in the same
   result), it is `reshape`.
5. **Reach.** `mainstream`: normal use of the documented interface. `legitimate_edge`: unusual
   but valid use. `contrived`: invalid input the project rejects elsewhere, private interfaces,
   a tampered environment, or a model or server behaving as no real one does.
6. **Did a legitimate user depend on it?** An announcement in CHANGE.md does not cancel a loss,
   and neither does the change calling the old behaviour a bug: authors announce trade-offs that
   teams later revert. The one exception: if the base behaviour could only ever hurt whoever
   relied on it (it silently produced garbage, or it only "worked" by accident on invalid input),
   set `base_was_defect` to true.
7. **Feature age.** If the thing that fails did not exist at base, it is not a loss.

Write `verdicts.json`, one entry per `loss` finding:

```json
{"probe": "p_07_x.py", "reproduced": true, "fails_for_stated_reason": true,
 "public_entry_point": true, "effect": "loss | gain_or_repair | reshape",
 "reach": "mainstream | legitimate_edge | contrived", "base_was_defect": false,
 "existed_at_base": true, "declared": "quote or null",
 "summary": "one plain sentence: what worked before and what happens now",
 "reason": "two sentences at most on why you ruled this way"}
```

Do not write a block or pass decision; code decides from these fields. Final message: one line
per entry with the probe name and the fields `effect`, `reach`, `reproduced`.
