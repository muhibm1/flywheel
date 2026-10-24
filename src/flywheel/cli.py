"""The `flywheel` command.

    flywheel run     run the agent over the dataset and save the scored experiment
    flywheel gate    compare two experiments, write the report, exit 1 when blocked
    flywheel close-calls  list the cases one more run could change, to run again
    flywheel mine    find failing traces in LangSmith and propose them as test cases
    flywheel promote add reviewed candidates to the dataset file
    flywheel sync    mirror the dataset file into a LangSmith dataset
    flywheel score   attach the evaluators' scores to existing traces as feedback

Exit codes: 0 done (and, for `gate`, not blocked); 1 `gate` blocked or a run could not
complete; 2 a usage or configuration error.
"""

import argparse
import json
import os
import re
import subprocess
import sys
from dataclasses import replace
from datetime import UTC, datetime, timedelta
from pathlib import Path

from flywheel import config as config_module
from flywheel import dataset, gate, grading, mine, report
from flywheel.config import Config, ConfigError, resolve
from flywheel.experiment import Experiment, pool, run_local
from flywheel.mine import NodeStep, TracedRun
from flywheel.scores import score_all

DEFAULT_CONFIG = "flywheel.toml"


def git_sha() -> str | None:
    """The commit being tested: `GITHUB_SHA` in Actions, else `git rev-parse HEAD`."""
    if os.environ.get("FLYWHEEL_GIT_SHA"):
        return os.environ["FLYWHEEL_GIT_SHA"]
    try:
        return subprocess.run(
            ["git", "rev-parse", "HEAD"], capture_output=True, text=True, check=True
        ).stdout.strip()
    except (OSError, subprocess.CalledProcessError):
        return os.environ.get("GITHUB_SHA")


def parse_since(text: str | None) -> datetime | None:
    """`7d`, `12h` or `30m` before now; None for no lower bound."""
    if not text:
        return None
    match = re.fullmatch(r"(\d+)([dhm])", text)
    if not match:
        raise ConfigError(f"--since takes a number and d, h or m, like 7d; got {text!r}")
    amount, unit = int(match[1]), match[2]
    delta = {
        "d": timedelta(days=amount),
        "h": timedelta(hours=amount),
        "m": timedelta(minutes=amount),
    }
    return datetime.now(UTC) - delta[unit]


def cmd_run(args: argparse.Namespace, cfg: Config) -> int:
    """`flywheel run`."""
    everything = dataset.load(cfg.dataset)
    # The version names the whole file, so a run of a few cases (`--only`) can be pooled with a
    # run of all of them.
    version = dataset.version(everything)
    examples = everything
    if args.only:
        wanted = set(args.only.split(","))
        examples = [example for example in everything if example.id in wanted]
    repetitions = args.repetitions or cfg.repetitions
    if args.backend == "langsmith":
        from flywheel import langsmith_backend

        if not cfg.langsmith_dataset:
            raise ConfigError("the langsmith backend needs `langsmith_dataset` in [flywheel]")
        experiment = langsmith_backend.run_experiment(
            langsmith_backend.client(),
            cfg.target_callable(),
            cfg.evaluator_callables(),
            examples,
            sync_examples=everything,
            dataset=cfg.langsmith_dataset,
            dataset_version=version,
            repetitions=repetitions,
            label=args.label,
            git_sha=git_sha(),
            concurrency=args.concurrency,
        )
    else:
        experiment = run_local(
            cfg.target_callable(),
            cfg.evaluator_callables(),
            examples,
            repetitions=repetitions,
            label=args.label,
            dataset_version=version,
            git_sha=git_sha(),
            concurrency=args.concurrency,
        )
    experiment = replace(experiment, graders=grading.fingerprints(cfg))
    experiment.save(Path(args.out))
    errored = sum(1 for run in experiment.runs if run.error)
    print(
        f"{experiment.label}: {len(examples)} case(s) x {repetitions} = {len(experiment.runs)} "
        f"run(s), {errored} errored, dataset {version} -> {args.out}"
    )
    if experiment.url:
        print(f"LangSmith experiment: {experiment.url}")
    return 0


def cmd_gate(args: argparse.Namespace, cfg: Config) -> int:
    """`flywheel gate`."""
    base = pool([Experiment.load(Path(path)) for path in args.base])
    head = pool([Experiment.load(Path(path)) for path in args.head])
    base_cfg = grading.load_base_config(Path(args.base_config)) if args.base_config else None
    changes = grading.changes(base, head, cfg, base_cfg)
    result = gate.compare(
        base, head, cfg.gate, grading_changes=changes, grading_approved=args.approve_grading
    )
    markdown = report.render(result)
    if args.report:
        Path(args.report).write_text(markdown, encoding="utf-8")
    summary_file = os.environ.get("GITHUB_STEP_SUMMARY")
    if summary_file:
        with open(summary_file, "a", encoding="utf-8") as handle:
            handle.write(markdown)
    print(markdown)
    return 0 if result.passed else 1


def cmd_close_calls(args: argparse.Namespace, cfg: Config) -> int:
    """`flywheel close-calls`: print the close calls as JSON, ids and how many more runs."""
    base = pool([Experiment.load(Path(path)) for path in args.base])
    head = pool([Experiment.load(Path(path)) for path in args.head])
    repetitions = (
        args.repetitions if args.repetitions is not None else (cfg.gate.close_call_repetitions)
    )
    ids = gate.close_calls(base, head, cfg.gate) if repetitions > 0 else []
    print(json.dumps({"ids": ids, "repetitions": repetitions}))
    return 0


def cmd_mine(args: argparse.Namespace, cfg: Config) -> int:
    """`flywheel mine`."""
    settings = cfg.mine
    project = args.project or settings.project
    if args.from_file:
        runs = [traced_run_from_json(raw) for raw in json.loads(Path(args.from_file).read_text())]
        ls = None
    else:
        from flywheel import langsmith_backend

        if not project:
            raise ConfigError("name the tracing project with --project or [mine] project")
        ls = langsmith_backend.client()
        runs = langsmith_backend.fetch_traced_runs(
            ls, project, settings, since=parse_since(args.since), limit=args.limit
        )
    inputs_of = resolve(settings.inputs, cfg.root) if settings.inputs else (lambda inputs: inputs)
    reference_of = resolve(settings.reference, cfg.root) if settings.reference else (lambda _: None)
    existing = dataset.load(cfg.dataset) if cfg.dataset.exists() else []
    result = mine.mine(
        runs, settings, existing=existing, inputs_of=inputs_of, reference_of=reference_of
    )
    dataset.save(Path(args.out), result.candidates)
    text = mine.render(result)
    if args.report:
        Path(args.report).write_text(text, encoding="utf-8")
    print(text)
    if args.queue and ls is not None:
        from flywheel import langsmith_backend

        queue_id = langsmith_backend.queue_for_review(
            ls,
            args.queue,
            [failure.run.id for failure in result.failures],
            "Is this run wrong? If so, write what the agent should have done in the reference.",
        )
        print(
            f"Queued {len(result.failures)} failing run(s) for review in {args.queue} ({queue_id})"
        )
    return 0


def traced_run_from_json(raw: dict) -> TracedRun:
    """A `TracedRun` from an exported JSON object (the offline input to `mine`)."""
    return TracedRun(
        id=str(raw["id"]),
        name=str(raw.get("name", "")),
        inputs=dict(raw.get("inputs") or {}),
        outputs=raw.get("outputs"),
        error=raw.get("error"),
        feedback={key: float(value) for key, value in (raw.get("feedback") or {}).items()},
        nodes=[
            NodeStep(name=step["name"], error=step.get("error")) for step in raw.get("nodes", [])
        ],
        url=raw.get("url"),
    )


def cmd_promote(args: argparse.Namespace, cfg: Config) -> int:
    """`flywheel promote`."""
    candidates = dataset.load(Path(args.candidates))
    if args.only:
        wanted = set(args.only.split(","))
        candidates = [example for example in candidates if example.id in wanted]
    unreviewed = [example.id for example in candidates if not example.reference_outputs]
    if unreviewed and not args.allow_empty_reference:
        print(
            "These candidates have no reference outputs yet; write them, or pass "
            f"--allow-empty-reference for reference-free evaluators: {', '.join(unreviewed)}",
            file=sys.stderr,
        )
        return 2
    existing = dataset.load(cfg.dataset) if cfg.dataset.exists() else []
    reviewed = [
        dataset.Example(
            example.id,
            example.inputs,
            example.reference_outputs,
            {**example.metadata, "needs_review": False, "promoted_at": today()},
        )
        for example in candidates
    ]
    merged, added = dataset.merge(existing, reviewed)
    dataset.save(cfg.dataset, merged)
    print(
        f"Added {len(added)} case(s); the dataset has {len(merged)} "
        f"(version {dataset.version(merged)})."
    )
    return 0


def today() -> str:
    """Today's date in UTC."""
    return datetime.now(UTC).date().isoformat()


def cmd_sync(args: argparse.Namespace, cfg: Config) -> int:
    """`flywheel sync`."""
    from flywheel import langsmith_backend

    if not cfg.langsmith_dataset:
        raise ConfigError("`flywheel sync` needs `langsmith_dataset` in [flywheel]")
    examples = dataset.load(cfg.dataset)
    version = dataset.version(examples)
    ids = langsmith_backend.sync_dataset(
        langsmith_backend.client(), cfg.langsmith_dataset, examples, version
    )
    print(f"{cfg.langsmith_dataset}: {len(ids)} example(s), tagged fw-{version}")
    return 0


def cmd_score(args: argparse.Namespace, cfg: Config) -> int:
    """`flywheel score`: what an online evaluator does, from code you already test."""
    from flywheel import langsmith_backend

    project = args.project or cfg.mine.project
    if not project:
        raise ConfigError("name the tracing project with --project or [mine] project")
    ls = langsmith_backend.client()
    inputs_of = resolve(cfg.mine.inputs, cfg.root) if cfg.mine.inputs else (lambda inputs: inputs)
    reference_of = resolve(cfg.mine.reference, cfg.root) if cfg.mine.reference else (lambda _: {})
    evaluators = cfg.evaluator_callables()
    runs = langsmith_backend.quietly(
        lambda: list(
            ls.list_runs(
                project_name=project,
                is_root=True,
                start_time=parse_since(args.since),
                limit=args.limit,
            )
        )
    )
    scored = 0
    for run in runs:
        if run.error or not run.outputs or (run.feedback_stats and not args.rescore):
            continue
        inputs = inputs_of(dict(run.inputs or {}))
        if inputs is None:
            continue
        scores, errors = score_all(
            evaluators, inputs, dict(run.outputs), reference_of(inputs) or {}
        )
        comment = "; ".join(f"{name}: {error}" for name, error in errors.items()) or None
        langsmith_backend.write_feedback(ls, run, scores, comment)
        scored += 1
    print(f"Scored {scored} of {len(runs)} root run(s) in {project}.")
    return 0


def parser() -> argparse.ArgumentParser:
    """The argument parser."""
    root = argparse.ArgumentParser(prog="flywheel", description=__doc__.split("\n\n")[0])
    root.add_argument("--config", default=DEFAULT_CONFIG, help="path to flywheel.toml")
    sub = root.add_subparsers(dest="command", required=True)

    run = sub.add_parser("run", help="run the agent over the dataset and save the experiment")
    run.add_argument("--label", required=True, help="a name for this side, like base or head")
    run.add_argument("--out", required=True, help="where to write the experiment JSON")
    run.add_argument("--backend", choices=("local", "langsmith"), default="local")
    run.add_argument("--repetitions", type=int, help="override the configured repetitions")
    run.add_argument("--concurrency", type=int, default=1)
    run.add_argument("--only", help="comma-separated example ids to run")

    gate_cmd = sub.add_parser("gate", help="compare two experiments and decide")
    gate_cmd.add_argument(
        "--base",
        required=True,
        nargs="+",
        help="the base branch's experiment; several runs of the same base are pooled",
    )
    gate_cmd.add_argument(
        "--head", required=True, nargs="+", help="the pull request's experiment; pooled likewise"
    )
    gate_cmd.add_argument("--report", help="also write the Markdown report here")
    gate_cmd.add_argument(
        "--base-config",
        help="the base branch's flywheel.toml, to find edits to the dataset and gate settings",
    )
    gate_cmd.add_argument(
        "--approve-grading",
        action="store_true",
        help="a person approved this pull request's edits to its own checks",
    )

    close = sub.add_parser("close-calls", help="list the cases one more run could change")
    close.add_argument("--base", required=True, nargs="+")
    close.add_argument("--head", required=True, nargs="+")
    close.add_argument(
        "--repetitions", type=int, help="override [gate] close_call_repetitions; 0 lists none"
    )

    mine_cmd = sub.add_parser("mine", help="propose failing traces as test cases")
    mine_cmd.add_argument("--project", help="the LangSmith tracing project")
    mine_cmd.add_argument("--since", help="how far back to look, like 7d or 12h")
    mine_cmd.add_argument("--limit", type=int, default=200)
    mine_cmd.add_argument("--from-file", help="mine an exported JSON list instead of LangSmith")
    mine_cmd.add_argument("--out", default=".flywheel/candidates.jsonl")
    mine_cmd.add_argument("--report", help="also write the Markdown summary here")
    mine_cmd.add_argument("--queue", help="also add the failing runs to this annotation queue")

    promote = sub.add_parser("promote", help="add reviewed candidates to the dataset")
    promote.add_argument("candidates")
    promote.add_argument("--only", help="comma-separated candidate ids to add")
    promote.add_argument("--allow-empty-reference", action="store_true")

    sub.add_parser("sync", help="mirror the dataset file into LangSmith")

    score = sub.add_parser("score", help="attach evaluator scores to existing traces")
    score.add_argument("--project")
    score.add_argument("--since")
    score.add_argument("--limit", type=int, default=100)
    score.add_argument("--rescore", action="store_true", help="score runs that have feedback")
    return root


COMMANDS = {
    "run": cmd_run,
    "gate": cmd_gate,
    "close-calls": cmd_close_calls,
    "mine": cmd_mine,
    "promote": cmd_promote,
    "sync": cmd_sync,
    "score": cmd_score,
}


def main(argv: list[str] | None = None) -> int:
    """Entry point."""
    args = parser().parse_args(argv)
    try:
        cfg = config_module.load(Path(args.config))
        return COMMANDS[args.command](args, cfg)
    except (ConfigError, dataset.DatasetError) as error:
        print(f"flywheel: {error}", file=sys.stderr)
        return 2
    except Exception as error:
        # A LangSmith API failure is reported in one line, not a traceback.
        if type(error).__module__.startswith("langsmith"):
            print(f"flywheel: LangSmith: {error}", file=sys.stderr)
            return 1
        raise


if __name__ == "__main__":
    sys.exit(main())
