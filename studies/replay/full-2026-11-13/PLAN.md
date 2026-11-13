# Replay study, 13 November 2026: what is scored, fixed before any held-out run

- Cases: 55 real past changes from nine repositories, each fair (its tests fail before the real
  change and pass after, twice each, and not for a missing name) and kept by a blind review that
  never saw an agent's result. `cases-tune.json` (35) steers; `cases-heldout.json` (20, the last 20
  by SHA-256 of the case id) is scored once, after the tuning runs, and never used to change
  anything.
- Arms, all with the user's own settings left out (`--clean-settings`), 3 repeats per case:
  haiku, sonnet, opus, and sonnet with the finish-check hook (`flywheel finish-check`).
- Pass: the change's own tests pass in the agent's copy. Runs that touched the source repository
  or history are flagged and left out; runs whose agent crashed (usage limit, sign-in) are
  re-run and never counted.
- Reported per arm: pass rate with a 95% Wilson interval, mean tokens, mean seconds, and the
  share of runs that edited code and finished with it checked.
