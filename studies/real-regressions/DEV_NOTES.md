
## Dev round 2 notes (2026-11-23)
- Endpoint v2.1 (00:4x UTC): proxy re-asks up to 2 times when a tool turn returns no calls and text says a tool is unavailable (agno, crewai writers saw ~1 in 6). Sealed copy /root/sealed/proxy-v2.1.py.
- miniswe-g1 (regression) PASS again in r2: the regression only shows on a malformed tool call, which the writer could not provoke from the live model. Candidate method change: allow writers fault injection (scripted / deterministic model replies) for cases about handling bad model output. Decide with a Fable review after all dev gates.
- autogen-g1 (regression) BLOCKED in r2.
- autogen-g2 (control, SocietyOfMindAgent #6142) BLOCKED in r2: 3 explored cases (caps, NAME: format, sign-off) 3/3 -> 0/3. Cause found in the diff: head builds the final answer from inner_messages, which skip the task messages, so the response model never sees the user's format instruction. Real behaviour change; autogen later reworked task-message skipping (f650d35f, #6678, closes #6150). So "control" means "no revert", not "harmless". Need a pre-registered adjudication rule for blocked controls before held-out scoring (Fable review).
- crewai-g1 (regression) BLOCKED in r2. miniswe-g2 (control) PASS.
- Veto kept 100% in autogen, miniswe, crewai, agno, smolagents; dropped 1 of 9 in gptr. Likely too lenient; consider in review.

## Budget turn (2026-11-23 02:35Z): Opus weekly limit hit; must finish this week
Direction review (Fable) adopted, to be written into PLAN.md as Amendment 3 before any held-out gate:
- Tier 1 (24 gates, 12 regressions + 12 first controls): agno, browseruse g1-6, deepagents g1-6, gptr, odr, pydanticai g1-4, strands (list in /root/sealed/tiers.txt). Tier 2 adk (12 gates) only if budget remains by a cut-off set at freeze, whole project or nothing. Dropped: openhands, all second controls, held-out noise gates. Reported as dropped for budget, decided before any held-out gate ran; plus a line on the original 24-regression denominator with dropped counted as misses.
- Headline false-block rate = all blocked controls / controls run. Adjudicated rate beside it (reproduces on fresh 3v3 and base-vs-base passes; Sonnet adjudicator finds the check documented at base and not an intended change; upstream later fix/issue found by a fixed search). Same adjudicator on blocked regressions: "caught for the stated reason".
- Arm 5 fault injection: proxy v2.2 /fault/<name>/v1 (6 faults), at most 2 per gate, all Tier 1 gates, base 2/2, separate arm. FAULT_NOTE.md.
- Timeouts: max 3 gates in parallel; every TimeoutError run is rerun once; a second timeout stands (run_gate.timeout_pass). autogen-g2 noise rerun under this rule.
- Reps 3, min_new_error_runs 2, close calls on. Wilson intervals; under 12+12 call it a pilot; 93% cannot be established on this sample, say so.
- Writers now Sonnet (gptr, odr, agno were Opus); split results by writer model. Veto unchanged; probe it with 5 planted non-required checks; <4 rejected -> label arm 4 unvetoed.
- Primary arm for the headline: arm 3 (standing + change-aware), arm 4 beside it with seen-on-head counts.
- Endpoint v2.3 (03:1xZ): the headless calls inherited host-session context (project memory index, user email) from the environment. Now stripped (CONTEXT_VARIABLES, CLAUDE_CODE_DISABLE_AUTO_MEMORY=1); a probe asking the model to quote such context returns NONE. All dev runs before this had the leak on both sides. Held-out runs use v2.3 only.
- Veto probe (03:3xZ): 8 planted cases in an autogen copy; dropped 5/5 non-required, kept 3/3 required. Arm 4 counts as vetoed.
- Endpoint 2.3 bug 03:13-03:47Z: an empty system prompt became a whitespace block the API rejects, so system-less requests 500ed. Fixed (neutral one-line system prompt when none is given); proxy_check.py (10 checks) now runs before any held-out gate and passed at 03:5xZ. Dev smolagents g3/g4 overlapped this window.
- gptr fault cases are inert: gpt-researcher's default flow never offers tools, so the tool-turn faults never fire. Kept as written; arm 5 adds nothing for gptr and the write-up says so.
- smolagents dev noise gates skipped for budget (03:59Z); dev noise covers autogen, miniswe, crewai.
- 07:4xZ the container restarted (uptime reset) and killed the runners and the endpoint mid-way through deepagents g1-g3. Endpoint restarted, proxy_check 10/10, runners resumed; finished side files were kept and missing ones rerun.
- 09:01Z the container had been reclaimed again ~07:48Z (it is reclaimed when the session idles; untracked background jobs die with it). Runner and endpoint now run as tracked background tasks.
- 11:02Z tracked background tasks stop at 2 hours; the endpoint and runner were restarted, finished side files kept (browseruse g1 base/head kept, g3 and g4 restarted from scratch).

## 2026-11-23 13:10Z: step (a) rerun for odr-g1 was invalid

`adjudicate_rerun.py` copies the gate's adapter shim into `<gate>/adjud/`, but the odr shim imports
`../suite/adapter.py`, which does not exist one level deeper. Every odr-g1 rerun crashed on import,
so its `reproduces: true, base_vs_base_passes: false` was produced by missing files, not by runs.
`confirm.py` links `<gate>/suite` to the project suite before rerunning; its result replaces the
odr-g1 step (a) result. deepagents-g1 and the other projects copy the adapter whole and were not
affected (checked: their rerun files exist and hold runs). The proxy restarted at 13:01Z on its
2-hour task limit; the Tier 1 confirm reruns show no connection or timeout errors.
confirm.py was changed after the adk-method freeze (29b1fd4a...) only to add the suite link above (absolute target); no rule changed. The ADK batch freeze hashes the fixed file.
2026-11-23: ADK writer (Sonnet) finished standing, change and sweep cases for adk-g1..g12 without running head; freeze-adk-pre-explore.json hashes them before any explored writer runs head. The writer listed `uv pip list` package names for six unused adk envs (the set-aside g13 to g18 bases); package lists only, no cases or diffs.

## 2026-11-23 15:10Z: reproduction rule made per case (before any ADK gate ran)

The first `confirm.py` cleared a block whenever base against base failed on the arm's broken cases
as a whole. On odr-g2 (every head run crashes with the datetime AttributeError, 48 of 48) that
cleared a plain regression because a few of its 16 broken cases were flaky on base. That reads
Amendment 4 more strictly than written and against its intent ("a case counts only if it passes
base against base"). `confirm.py` now drops, per arm, the broken cases that also break base-b
against base-a, and the block stands if Flywheel still blocks head-a against base-a on the rest.
`--reuse` re-decides from the existing reruns. Tier 1, post hoc: arm 3 confirmed 6 of 12 and 1 of
12 controls (odr-g1 reproduces cleanly); arm 4 confirmed 8 of 12 and 1 of 12 (deepagents-g1 does
not reproduce). Fixed before any ADK gate ran; the ADK freeze hashes this version.
2026-11-23 15:02Z: the endpoint task hit its 2-hour limit about ten minutes into the first ADK run (g1 to g3 had started). That partial run was moved whole to /root/rr-trash/adk-aborted-1502, unscored and unread, and ADK g1 to g6 restarted from scratch. The endpoint now runs detached under keep_proxy.sh, a watchdog that restarts it within about 15 s if it stops answering.
Known quirk in confirm.py, found after scoring and left as frozen: it takes broken ids from every bullet between "### Broken" and the next "###" heading, so wobbling cases listed in the <details> block under it are rerun too. Each arm is then decided by Flywheel's own gate on the rerun files, so a wobbling case could in principle carry a confirmed block if it broke on the rerun. Checked for ADK: the only confirmed block (adk-g8) is carried by the broken explored case; the wobbling sweep case did not block on its own (arm 6 not confirmed). Round 1 confirmed results are post hoc and labelled so.
