# Bug report in, proven culprit change out

A user says "this used to work and now it does not". The job is to name the one change that broke
it, and to prove it with a small program anyone can rerun. This document fixes the design and the
scoring rule before any held-out case is looked at.

## Why this job

The first job this study tried was a gate that blocks a bad change before it merges. On practice
data it caught 12 of 20 real regressions strictly and 15 of 20 with a deeper pass, and about 3 in
20 real regressions are a stated purpose that the team later reversed, which no gate can know at
merge time. That job stays in the repository as a secondary feature with its own number.

Naming the culprit after the fact does not have that ceiling. The bug is known, so the question
has one right answer, and the answer can be checked by running code.

## How it works

1. **Reproduce.** A reproducer reads the report and the broken source tree and writes `probe.py`.
   Exit 0 means the behaviour works. Exit 1 means the reported bug shows. Exit 125 means this
   version cannot be judged. The reproducer never sees the history.
2. **Check both ends.** The probe must exit 0 at the version the user says worked and 1 at the
   broken version, every time it is run. If not, the probe is rejected and rewritten.
3. **Search.** A deterministic tracer bisects the first-parent history between the two ends. No
   model takes part. The answer is the first change at which the probe fails while it passes at
   that change's parent. Versions that cannot be judged are stepped around. If they leave more
   than one candidate the status is `ambiguous`, never a guess.
4. **Report.** `found` with one commit, plus the probe and the list of versions tested. Anyone can
   rerun the probe at the culprit and at its parent.

A probe is run three times per version. Mixed exits count as "cannot judge". Variables that look
like credentials are removed from the probe's environment.

## What was learned on practice data (20 regressions, 10 projects)

| Arm | Detailed reports | Short vague reports |
|---|---|---|
| Tool: culprit correct, with proof | 20 of 20 | 20 of 20 |
| Tool: probe also passes at the team's real fix | 20 of 20 | 17 of 20 |
| Plain model naming the culprit by reading the history | 20 of 20 | 19 of 20 |
| Plain model writing a probe without running it, valid at both ends and the fix | 15 of 20 | not run |

Two things follow. First, a strong model reading a history of 50 to 560 changes names the right
change almost as often as the tool. Accuracy alone is not the difference. The difference is that
the tool's answer comes with a reproduction that was run, and the plain model's does not: it has
no way to tell its one wrong answer from its right ones. Second, when a report is vague the probe
can show a neighbouring symptom of the same change. In 3 of 20 short reports the culprit was right
but the team's fix did not make that probe pass, because the fix repaired a narrower case than the
probe set up. This is reported as a separate number and never hidden inside the headline.

## The scoring rule, fixed in advance

- **Set.** H1: 60 real regressions from 27 projects that were never used in development. The
  answers are sealed. The person running the study sees counts only until scoring.
- **Input per case.** A short vague report (no code, no identifiers, no exact error text), the
  version that worked, the broken version, and an environment with the project's dependencies.
  The window between the two versions starts 40 to 120 changes before the true culprit and ends
  just before the team's fix.
- **Headline: proven culprit rate.** A case counts only if the tool ends in `found` and the commit
  is right. Right means the true introducing commit is contained in the named change and not in
  its parent. `ambiguous`, a rejected probe, an environment that could not be built, and a case
  that could not be set up all count as misses. The denominator is always 60.
- **Target.** At least 92 percent, which is 56 of 60.
- **Also reported.** Wrong answers given as `found` (false proofs). Agreement with the team's real
  fix, over the cases where the fix version can be run in the same environment. Number of full
  searches per case.
- **Baselines, with a stronger model than the tool uses.** (a) Naming the culprit by reading the
  same window of history, one commit diff at a time, without running code. (b) Writing a probe
  from the same report without running anything, then handing it to the same tracer; it scores
  under the same headline rule.
- **Once.** The code and briefs are frozen at a commit before the tool or any baseline runs on an
  H1 case. One change was made after the first freeze, while environments were being built and
  before any H1 case was run: a case may list fallback interpreters, because one project's
  dependencies changed incompatibly inside its window. H1 is scored one time. If the target is missed, H1 becomes practice data, the design is reworked, and the
  rework is scored on H2 (43 regressions, 23 other projects).

## Disclosed limits

- The reports are written by a model, in two steps. A first writer sees the failing test that
  shows the bug and writes a careful report with the cause removed. A second writer, who sees only
  that report, rewrites it as a short note with no code or identifiers. The tool sees only the
  short note. Real users write worse and better reports than this.
- The good and bad versions are given. A real user usually knows them as two release numbers.
- The environments are built from install notes recorded when the cases were collected. The
  reproducer may add a missing package but never installs the project itself.
- Python projects that build agents on language models. Other ecosystems are untested.
- First-parent history only: a merge is blamed as one change.
