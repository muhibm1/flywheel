# Gap pass brief

A first reviewer (the hunter) has already studied one code change: listed how the new code (head)
differs from the old (base), written probes and run them on both. You are the second pass. Your
job is to find what the first pass did not try. You do not know whether this change is fine or
broken. Most changes are fine.

Read `briefs/SHELL_RULES.md` and `briefs/HUNTER.md` (next to this file) first. Everything in
HUNTER.md about limits, probes, the runner and how to classify applies to you.

## What you have

The same gate folder, now also containing the first pass's `ledger.json`, `probes/`,
`results.json`, `coverage.json`, `findings.json` and `HUNT_NOTES.md`.

## What to do

1. Read the diff and CHANGE.md yourself before reading the first pass's notes, and write down in
   `gap_ledger.json` your own list of the situations you would test. Then read the first pass's
   ledger and probes and strike what is already covered by a probe that really exercises it (open
   the probe; do not trust its name).
2. Work through these, adding to `gap_ledger.json` what is still untested:
   - **Combinations.** For each confirmed difference and each new rule the change adds, cross it
     with every special moment of the surrounding loop or lifecycle: first step, last allowed
     step, a turn after which no further request can follow, limits or budgets already reached,
     retries already used, a resumed run, a second run on the same object, a hand-off and return,
     streaming, async. Cross it with each neighbouring feature that touches the same code.
   - **Named cases.** Every case CHANGE.md or a changed docstring names must have its own probe.
   - **Who relied on the old behaviour.** For each difference the first pass called a repair or a
     reshape, name a user who depended on the old behaviour through the public interface. If one
     exists, probe their workflow end to end.
   - **Not probed.** Everything `HUNT_NOTES.md` lists as not reached or not tried. Try it.
   - **Callers.** Search head for every caller of each changed function. Any caller with no probe
     through it gets one.
3. Write the new probes as `probes/g_<nn>_<short_name>.py` (same rules as hunter probes) and run
   them with the runner using `--only` for each new file, so earlier results are kept.
4. Re-read every entry of the first pass's `findings.json` against the classification rules in
   HUNTER.md. Write `findings_final.json`: all confirmed differences from both passes (first-pass
   entries corrected where the rules say so, yours added), in the HUNTER.md findings format.

Final message: the number of new probes, new confirmed differences, and for each entry of
`findings_final.json` with `effect: loss` one line: probe, reach, what a user sees.
