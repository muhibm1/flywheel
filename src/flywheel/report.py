"""The gate's result as Markdown: a pull-request comment a reviewer can act on in a minute.

It opens with one plain sentence (what ran, what changed, whether it blocks), then the cases
that need attention with links to their traces, then the totals and provenance for anyone who
wants to check the numbers.
"""

from flywheel.experiment import Experiment
from flywheel.gate import CaseResult, CostSide, GateResult
from flywheel.grading import KIND_TITLES

MARKER = "<!-- flywheel-report -->"
VERDICT_TITLES = {
    "broken": "Broken: passed before, fail now",
    "fixed": "Fixed: failed before, pass now",
    "wobble": "Wobbling: changed by less than the threshold (reported, not blocking)",
    "new": "New cases",
    "removed": "Removed cases",
}


def fraction(rate: float | None, runs: int) -> str:
    """A pass rate as `passed/runs`, or a dash when the side did not run the case."""
    if rate is None:
        return "–"
    return f"{round(rate * runs)}/{runs}"


def headline(result: GateResult) -> str:
    """The title line."""
    broken = result.count("broken")
    if result.passed:
        if broken:
            return f"## ✅ Flywheel: passed, with {broken} broken case(s) within the allowance"
        return "## ✅ Flywheel: no regressions"
    return "## ❌ Flywheel: this change is blocked"


def plain_summary(result: GateResult) -> str:
    """One paragraph a non-engineer can repeat: what was run and what changed."""
    head = result.head
    shared = sum(1 for case in result.cases if case.verdict not in ("new", "removed"))
    counts = [len(head.runs_of(case.example_id)) for case in result.cases]
    least, most = min(counts, default=head.repetitions), max(counts, default=head.repetitions)
    reps = "once each" if least == 1 else f"{least} times each"
    if most > least:
        extra = sum(1 for count in counts if count > least)
        reps += (
            f", and {most} times for the {extra} close call{'s' if extra != 1 else ''} "
            "where more runs could change the answer"
        )
    parts = [
        f"Flywheel ran the agent on {shared} test case{'s' if shared != 1 else ''}, {reps}, "
        "before and after this change, and compared the results case by case."
    ]
    broken, fixed, wobble = result.count("broken"), result.count("fixed"), result.count("wobble")
    changes = []
    if broken:
        changes.append(
            f"{broken} case{'s' if broken != 1 else ''} that passed before now "
            f"fail{'' if broken != 1 else 's'}"
        )
    if fixed:
        changes.append(
            f"{fixed} case{'s' if fixed != 1 else ''} that failed before now "
            f"pass{'' if fixed != 1 else 'es'}"
        )
    if wobble:
        changes.append(f"{wobble} moved by less than the noise threshold")
    parts.append(("Result: " + "; ".join(changes) + ".") if changes else "Nothing changed.")
    if result.reasons:
        parts.append("Blocked because " + "; and ".join(result.reasons) + ".")
    return " ".join(parts)


def case_lines(case: CaseResult, base: Experiment, head: Experiment) -> list[str]:
    """One bullet for a case, with the metrics that moved and its trace links."""
    moved = [m for m in case.metrics if m.verdict not in ("steady_pass", "steady_fail")]
    shown = moved or case.metrics
    base_runs = len(base.runs_of(case.example_id)) or base.repetitions
    head_runs = len(head.runs_of(case.example_id)) or head.repetitions
    metrics = ", ".join(
        f"`{m.metric}` {fraction(m.base_rate, base_runs)} → {fraction(m.head_rate, head_runs)}"
        + (f" (p = {m.p_value:.2g})" if m.p_value is not None else "")
        for m in shown
    )
    line = f"- `{case.example_id}` {case.summary}"
    lines = [line, f"  - {metrics}"]
    if case.new_error:
        lines.append(f"  - new error: `{case.new_error}`")
    if case.head_urls:
        links = " · ".join(f"[run {i}]({url})" for i, url in enumerate(case.head_urls, start=1))
        lines.append(f"  - traces: {links}")
    return lines


def comparison_url(base: Experiment, head: Experiment) -> str | None:
    """LangSmith's side-by-side view of both experiments, when both ran on one dataset there."""
    if not (base.url and head.url) or "selectedSessions=" not in base.url:
        return None
    base_page, _, base_session = base.url.partition("selectedSessions=")
    head_page, _, head_session = head.url.partition("selectedSessions=")
    if base_page != head_page:
        return None
    return f"{base_page}selectedSessions={base_session},{head_session}"


def cost_lines(result: GateResult) -> list[str]:
    """The cost table: what an average run used on each side; nothing when neither counted."""
    base, head = result.base_cost, result.head_cost
    if base is None and head is None:
        return []

    def cell(side: CostSide | None, value) -> str:
        return "–" if side is None else value(side)

    def share(side: CostSide) -> str:
        return "–" if side.cache_share is None else f"{side.cache_share:.0%}"

    def dollars(side: CostSide) -> str:
        return "–" if side.usd is None else f"${side.usd:.4f}"

    rows = [
        ("Model calls", lambda side: f"{side.calls:.1f}"),
        ("Tokens, prompt and output", lambda side: f"{side.tokens:,.0f}"),
        ("Share of the prompt read from the cache", share),
    ]
    if any(side is not None and side.usd is not None for side in (base, head)):
        rows.append(("Dollars at list price", dollars))
    lines = ["### Cost of a run", "", "| Per run | Before | After |", "|---|---|---|"]
    lines += [f"| {name} | {cell(base, value)} | {cell(head, value)} |" for name, value in rows]
    lines.append("")
    sides = [side for side in (base, head) if side is not None]
    spent = sum(side.billed for side in sides)
    replayed = sum(side.replayed for side in sides)
    note = f"API credit these runs spent: ${spent:.2f}."
    if replayed:
        note += f" {replayed} call{'s' if replayed != 1 else ''} came from recordings at no cost."
    for side, name in ((base, "base branch's"), (head, "pull request's")):
        if side is None:
            note += f" The {name} runs counted no model calls, so the sides cannot be compared."
    lines += [note, ""]
    return lines


def render(result: GateResult) -> str:
    """The whole comment."""
    base, head = result.base, result.head
    lines = [MARKER, headline(result), "", plain_summary(result), ""]
    if result.grading_changes:
        status = (
            "A person approved these edits."
            if result.grading_approved
            else "A person must approve these before the gate can pass: add the "
            "`flywheel-grading-approved` label, or pass `--approve-grading`."
        )
        lines += [
            "### This pull request changes how it is graded",
            "",
            "Edits like these can turn a failure into a pass without changing the agent. " + status,
            "",
        ]
        for change in result.grading_changes:
            detail = f": {change.detail}" if change.detail else ""
            lines.append(f"- {KIND_TITLES[change.kind]}: `{change.subject}`{detail}")
        lines.append("")
    for verdict in ("broken", "fixed", "wobble", "new", "removed"):
        cases = [case for case in result.cases if case.verdict == verdict]
        if not cases:
            continue
        body = [line for case in cases for line in case_lines(case, base, head)]
        if verdict in ("broken", "fixed"):
            lines += [f"### {VERDICT_TITLES[verdict]}", "", *body, ""]
        else:
            title = f"{VERDICT_TITLES[verdict]} ({len(cases)})"
            lines += [f"<details><summary>{title}</summary>", "", *body, "", "</details>", ""]

    lines += ["### Totals", "", "| Metric | Before | After |", "|---|---|---|"]
    for total in result.totals:
        lines.append(
            f"| `{total.metric}` | {total.base_passed}/{total.base_runs} | "
            f"{total.head_passed}/{total.head_runs} |"
        )
    lines.append("")
    if result.sign_test_p is not None:
        lines.append(
            f"Sign test over broken and fixed cases: p = {result.sign_test_p:.3g} (the chance of a "
            "split at least this uneven if the change did nothing)."
        )
        lines.append("")
    lines += cost_lines(result)
    lines += ["<details><summary>Provenance</summary>", ""]
    for side, experiment in (("Before", base), ("After", head)):
        name = (
            f"[{experiment.name or experiment.label}]({experiment.url})"
            if experiment.url
            else (f"`{experiment.label}`")
        )
        sha = f" at `{experiment.git_sha[:7]}`" if experiment.git_sha else ""
        lines.append(
            f"- {side}: {name}{sha}, {experiment.backend} backend, dataset "
            f"`{experiment.dataset_version}`, {len(experiment.runs)} run(s)"
        )
    both = comparison_url(base, head)
    if both:
        lines.append(f"- [Compare both experiments side by side in LangSmith]({both})")
    if base.dataset_version != head.dataset_version:
        lines.append("- The dataset changed in this pull request; cases are matched by id.")
    lines += ["", "</details>", ""]
    return "\n".join(lines)
