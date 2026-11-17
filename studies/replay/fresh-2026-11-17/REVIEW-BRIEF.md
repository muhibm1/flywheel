# Blind task review: the brief every reviewer got

You are judging whether each case is a fair task for a coding agent. You never see an agent's result.

An agent will get ONLY the task text (the real commit message) and a copy of the repository as it was
before the commit. Afterwards the hidden test diff is applied and run; the agent passes if those tests pass.

KEEP a case when a capable engineer, reading only the task text and the existing code, could write a
change that passes the hidden tests: every behaviour, name, message, label or value the tests assert is
stated in the task, already exists in the code, or follows directly from an existing pattern.

DROP a case when:
- the tests check exact wording, labels, messages, new function, field, flag or file names, or specific
  values that the task never gives and the existing code does not imply; or
- it is not a code change a person would ask for (copy or documentation edits, version bumps, test-only
  refactors, reformatting); or
- the task text is too thin to say what to build (for example a subject line only, for a change with
  several specific behaviours).

Judge each case on its own. Do not drop a case for being hard or large: difficulty is fine, missing
information is not.

Output: a JSON list, one object per case, `{"id": ..., "verdict": "KEEP"|"DROP", "reason": "<one sentence>"}`.
