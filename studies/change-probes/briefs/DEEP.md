# Deep pass brief

Two reviewers have already studied this change and written probes. Reviewers at that stage miss
the same kinds of difference again and again, because they test what they imagine the change does.
Your job is to find what they did not imagine: observe the old code (base) and the new code (head)
doing the same ordinary things, compare everything observable, and prove each difference with a
probe. You do not know whether this change is fine or broken. Most changes are fine.

Read `briefs/SHELL_RULES.md` and `briefs/HUNTER.md` (next to this file) first. The hunter brief's
limits, probe rules and runner apply to you unchanged. You may read everything in the gate folder,
including `ledger.json`, `gap_ledger.json`, `findings_final.json`, `results.json` and the probes.
Name your probes `probes/x_<nn>_<short_name>.py` and your scenarios `probes/s_<nn>_<short_name>.py`.

## Step 1. Snapshot scenarios (mandatory, do this before reading the earlier findings closely)

A scenario does not assert anything. It drives one ordinary use and records all that could be
observed, as one JSON object written to the path in the environment variable `SNAP_OUT`:

- the return value and any exception (type and message);
- stored state afterwards: conversation history row by row with roles, saved files and their
  contents, config written back to disk, counters, registries;
- every request the project sent outwards: the full payload to the model stand-in, to tools, to
  fake servers, to subprocesses (argv), in order;
- telemetry: spans (name, parent, attributes), metrics, log records at warning level or above.
  If the project has tracing or metrics hooks, install an in-memory exporter or handler and record
  what arrives. Record which calls produced one span and which none;
- exported or rendered forms: `to_dict`, `to_json`, history strings, exports, printed output,
  and their sizes (length, line count).

Run them with `python3 /home/user/flywheel/studies/change-probes/snap_diff.py <gate>`
(`--only s_03_name.py` for one). It runs each scenario twice per side, drops values that vary
within a side, and prints every path whose value differs between base and head.

Write scenarios for, at least:

1. The default object. Build each changed class or call each changed function the way the
   project's own README, docs, examples and tests at base do, with defaults, and run one ordinary
   operation. One scenario per public entry point whose code path includes a changed line.
2. Each caller. For every changed function, find its call sites in the project (search the tree)
   and write a scenario through each distinct caller: other classes, workflows, servers, command
   line entry points, wrappers and decorators around it. A difference often shows only in a caller
   that matches on a message string, a return shape, an attribute, or relies on a decorator or
   context manager still wrapping the same function.
3. Each kind of thing that flows through the changed code. List the kinds from the code, not from
   imagination: every subclass, every content shape (plain string, list of blocks, structured
   object, very large value stored elsewhere and replaced by a preview), every tool kind (sync,
   async, long-running, one that waits on another task or on the user), every provider or
   integration the docs describe. One scenario per kind.
4. Each documented recipe. For every doc page, example or docstring in the tree that mentions a
   changed module, function or setting, write the scenario it describes.
5. A second round. Run the same operation several times in one process and across a save and
   resume, and record the state after each round.

Every differing path is a lead. For each one, decide what it means for someone relying on base and
write a probe that asserts base's value (probes are as in the hunter brief). Do not discard a lead
because the outcome "still works": a lost bound (a cap, a truncation, a limit, a redaction, a
timeout), an extra or missing row, a missing span or attribute, a dropped argument, an extra
argument sent to someone else's server, and a value that no longer follows what the user set are
all probes to write.

## Step 2. Lenses the first reviewers tend to skip

Walk each of these over the diff. For each, write probes or one line in `deep_ledger.json` saying
why it cannot apply.

- **Re-routing.** When the change sends a case to a different handler, backend or code path than
  before, list every guarantee the old path gave for that case (bounded output, formatting,
  retries, auth, error translation, caching) and probe each on the new path.
- **Error flow.** For every changed `try`, `except`, `finally`, `await`, `gather`, `shield`,
  task cancel or timeout: which exceptions passed through before and are swallowed, converted or
  delayed now, and the other way round? Include cancellation (`asyncio.CancelledError`),
  `KeyboardInterrupt` and timeouts. Probe through the nearest function that the project's own code
  calls; an internal component counts when the project's own callers rely on that behaviour.
- **Guards removed or loosened.** For every check, validation, cap or refusal the change removes
  or relaxes: what did it protect, and where does the previously refused input go now? Follow it
  to the next boundary (a server, a file, a model request). Write a probe that asserts base's
  refusal and classify it `guard_removed` (see below). Look in the tree (docs, comments, error
  tables, vendored API notes) for the reason the guard existed and quote it.
- **Counters and state lifetime.** For every new or moved counter, cache, flag or buffer: over
  what span does it live (one call, one round, one run, the process, forever on disk)? Probe a
  normal sequence that crosses that span: several rounds, several runs, a retry after a failure,
  a late registration.
- **Matching on text.** When a message, name, key, parameter name or schema field is reworded or
  renamed, search the tree for every place that compares against the old text and probe it.
- **Defaults.** When a default value changes or a parameter is removed, snapshot what an object
  built with defaults contains and emits, and look for leftovers of the old or new default (an
  empty entry, a `None` rendered as text, a stale field).
- **Outside contracts.** When the change alters what is sent to or accepted from software the
  project does not control (an SDK, a protocol client, a hosted API), capture what the real
  client library installed in the environment sends by default and replay it; check parameter
  names and extra fields against the protocol's rules as written in the tree or the installed
  package.
- **Variants of every confirmed difference.** For each difference already confirmed (yours or the
  earlier ones), list the dimension the changed code branches on and probe the neighbouring
  values of that dimension. A team's eventual bug report is usually one specific variant.

## Step 3. Coverage and findings

Run the runner over your probes (one at a time with `--only` if the gate is heavy). Close the
coverage loop as in the hunter brief for any changed line still uncovered.

Append your confirmed differences to a copy of `findings_final.json` and write the whole list back
as `findings_final.json`. Use the hunter brief's fields, with these changes:

- `effect` may also be `guard_removed`: base deliberately refused this input and head lets it
  through to something downstream. Add `"guard_reason"`: the quote that says why the guard existed,
  or null.
- Classify as `loss`, not `reshape`, when a guarantee is gone even though a result still comes
  back: output no longer bounded, a record no longer written, a span or attribute no longer
  emitted, an extra artefact (row, field, argument) now present where consumers do not expect it,
  a signal (cancellation, error, state change) no longer delivered.
- Add `"exposure"`: where in the tree (path and line at base: the project's own non-test code,
  docs, examples, tests, defaults, or the installed client library) this exact situation is
  shown to occur, or null.

Write `DEEP_NOTES.md`, ten lines at most. Final message: one line with the number of scenarios,
probes, and new confirmed differences per `effect`. Nothing else.
