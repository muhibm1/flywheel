# Task: find real, team-confirmed agent regressions in a git history

You are doing a read-only survey of one or more open-source AI-agent repositories that are
already cloned (history only, blob-less, no checkout) under /tmp/oss/<dir>. Use `git -C /tmp/oss/<dir> log`,
`git show --stat`, `git show <sha> -- <path>` (blobs download lazily; that is fine). Never check out,
never modify the repo, never run project code. Do not use the network other than git's lazy fetch.

## What we are looking for
A REGRESSION PAIR = (introducing change, later fix-or-revert), where the project's own maintainers
reverted or fixed a change that had ALREADY MERGED to the main branch because it made the agent
behave worse or break at run time. The team's own revert/fix message is the evidence; do not decide
yourself that something was a regression.

Classes to keep:
- B (behavioural): the introducing change altered what the model sees or how the loop is steered:
  prompt text, tool descriptions/schemas, context/history assembly, compaction/summarisation,
  default model or sampling parameters, stop/retry/step-limit logic, output parsing leniency.
  Later reverted/fixed because agent results got worse (wrong answers, loops, refusals, worse evals).
- C (run-path code break): a bug introduced in the code an ordinary agent run executes (tool
  execution, parsing of model output, state/memory handling, streaming, subagents, middleware)
  that made normal agent runs fail or misbehave, and that the project's tests did not catch at merge.

Drop: UI/TUI/cosmetic, docs, CI/infra/release, dependency bumps, typing/lint, packaging, auth/OAuth,
telemetry, pure performance, security hardening, test-only changes, things reverted before any
release for non-behaviour reasons (e.g. "revert test comment"), and commits whose message merely says
"add regression test" with no earlier breaking change identifiable.

## How to search
For each repo: list commits whose message matches (case-insensitive) any of: ^revert, regress, broke,
broken by, worse, degrad, "introduced in", "caused by #", rollback, "roll back", hotfix. Read subject+body
(`git log --format='%H%n%ad%n%s%n%b%n----' --date=short -i -E --grep=...`). For promising ones, inspect
`git show --stat` and the diff to (1) confirm the class, (2) identify the INTRODUCING commit: the revert
target, a PR number/sha cited in the body, or via `git log -S`/`git log -L`/blame-style digging on the
changed lines. If you cannot pin the introducing commit with good confidence, still record it with
intro_confidence "low". Budget: skim everything, deep-read at most ~60 candidates per repo, prioritising
class B, then C in core agent-loop code. For very large monorepos focus on the core agent/SDK package paths.

## Output
Write one JSON object per line to the output file named in your prompt (create it; append as you go so
partial work survives). Fields:
repo, fix_sha, fix_date, fix_subject, intro_sha (or null), intro_date, intro_subject, intro_confidence
(high|medium|low), class (B|C), what_broke (one plain sentence, from the maintainers' words),
evidence_quote (short verbatim quote from the fix/revert message showing the team says it got worse/broke),
paths (main files changed by the introducing commit, max 5), fix_added_test (true|false|unknown),
released_between (true|false|unknown: did a release/version tag land between intro and fix),
days_live (integer days between intro and fix, or null),
provider_specific (null, or the provider/model it only affects, e.g. "openai", "gemini", "anthropic"),
needs_external (short list of what a run needs beyond an LLM: e.g. "browser", "docker sandbox", "web search key", "none"),
replay_notes (one sentence: how hard would it be to run the agent at intro^ and intro, and what kind of
task would exercise the broken behaviour).

Final reply to me (short): per repo, number of commits skimmed, number of class B and class C pairs written,
how many have intro_confidence high, and the 5 strongest class-B pairs in one line each. Report only what
you verified in the git data; say "unknown" rather than guess.
