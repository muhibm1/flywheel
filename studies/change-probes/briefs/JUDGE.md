# Judge brief

A code change was probed, and some probes proved that something which worked on the old code
(base) no longer works the same way on the new code (head). Each of those findings has already
been reproduced and checked. Your job is narrower: for each finding, establish from evidence in
the gate folder (a) whether this outcome is what the change set out to do, and (b) whether real
users are in the situation the probe sets up. You do not decide block or pass, and you do not know
whether this change is fine or broken. Most changes are fine; some findings are real damage.

Read `briefs/SHELL_RULES.md` (next to this file) first. Work only in the gate folder. No network,
no git history, no real model. You do not need to run anything; you may rerun a probe through the
runner if you must see its output.

## What you have

`CHANGE.md` (the author's own title and description), `change.diff` (including any tests and docs
the change itself adds, edits or deletes), `base/` and `head/` source trees, `probes/`,
`findings_final.json`, `verdicts.json` and `verdict.json`. Judge every finding listed under
`blocking` in `verdict.json`.

## Question 1: purpose

Compare what head does in the probe's exact situation with what the author says the change is for.

- `stated`: the author says head should behave this way in this situation. You must quote the
  words: from CHANGE.md, from a doc, comment or changelog line the diff adds, or from a test the
  diff adds or edits that asserts head's behaviour for this situation (a deleted test for the old
  behaviour also counts). A general title ("refactor X", "fix Y", "clean up") is not a statement
  about this situation. The quote must cover the situation, not just the feature.
- `implied`: the author does not say it, but the stated aim cannot be had without it. Write the
  one-sentence argument. Test: if no small fix could keep the stated improvement and also keep
  this situation working as at base, it is implied.
- `collateral`: the stated aim could be met in full with this situation still working as at base.
  The loss is a side effect: an unhandled case, a consumer the author did not update, a counter
  with the wrong lifetime, a default that trips the new rule, a guarantee lost on a new path.
- `contradicts`: head does the opposite of what the author says the change does.

Be strict in both directions. Do not excuse a loss as intended because it lies in the same feature
the change touches. Do not call a loss collateral when the author plainly names it.

## Question 2: exposure

Is anyone actually in this situation? Look for evidence at base, outside the probe itself.

- `shown`: you can point to it. Give `path:line` for one of: the project's own non-test code
  reaching the changed code in this situation; docs, README or examples telling users to do this;
  a base test that exercises it; a default value or default configuration that produces it; what
  an installed client library or SDK sends by default; existing users' stored data or config from
  earlier versions that the base code explicitly handles (an upgrade path).
- `plausible`: valid use, nothing in the tree shows it happening.
- `unlikely`: needs an unusual combination, a name clash, a subclass override of an internal
  method, or a failure of something else first, and nothing in the tree shows it.

## Question 3: what the user experiences at head

- `harm`: `breaks` (the operation fails, is refused, silently does not happen, data or settings
  are lost or stranded, or a safety limit stops working), `degrades` (the operation completes with
  a worse or stale result), or `cosmetic`.
- `told`: `clear_error` if head stops with a message that names the cause and what to do instead;
  `error` if it fails with a message that does not; `silent` if nothing tells the user.
- `frequency`: `every_time` if every user in this situation hits it on ordinary use,
  `sometimes` if it needs particular timing, ordering or a prior failure.

## What to write

Write `judge.json`: a list with one entry per blocking finding.

```json
{"probe": "p_07_x.py",
 "purpose": "stated | implied | collateral | contradicts",
 "purpose_evidence": "the quote with its file, or the one-sentence argument",
 "exposure": "shown | plausible | unlikely",
 "exposure_evidence": "path:line and what it shows, or null",
 "harm": "breaks | degrades | cosmetic",
 "told": "clear_error | error | silent",
 "frequency": "every_time | sometimes",
 "reason": "two sentences at most"}
```

Final message: one line: the number of findings judged. Nothing else.
