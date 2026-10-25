"""Prices, the budget guard, record and replay, the meter, and the gate's cost checks."""

import contextvars
import json
import threading
import time
from concurrent.futures import ThreadPoolExecutor

import pytest

from flywheel import spend
from flywheel.cli import main
from flywheel.config import GateSettings, load
from flywheel.dataset import Example
from flywheel.experiment import Experiment, RunRecord, run_local
from flywheel.gate import compare
from flywheel.report import render

SONNET = "claude-sonnet-5-5"
HAIKU = "claude-haiku-5-5"


def request(text="hello", **extra):
    """A Messages API request body."""
    return {
        "model": HAIKU,
        "max_tokens": 100,
        "messages": [{"role": "user", "content": [{"type": "text", "text": text}]}],
        **extra,
    }


def answer(input_tokens=1000, output_tokens=200, read=0, write=0):
    """A Messages API response body with its usage."""
    return {
        "content": [{"type": "text", "text": "hi"}],
        "usage": {
            "input_tokens": input_tokens,
            "output_tokens": output_tokens,
            "cache_read_input_tokens": read,
            "cache_creation_input_tokens": write,
        },
    }


# --- prices -------------------------------------------------------------------------------------


def test_list_prices_per_kind_of_token():
    """Each kind of token is priced at its own rate."""
    assert spend.price(SONNET, spend.Usage(input=1_000_000)) == pytest.approx(2.00)
    assert spend.price(SONNET, spend.Usage(cache_read=1_000_000)) == pytest.approx(0.10)
    assert spend.price(SONNET, spend.Usage(cache_write_5m=1_000_000)) == pytest.approx(2.50)
    assert spend.price(SONNET, spend.Usage(cache_write_1h=1_000_000)) == pytest.approx(4.00)
    assert spend.price(SONNET, spend.Usage(output=1_000_000)) == pytest.approx(10.00)
    assert spend.price(SONNET, spend.Usage(web_searches=3)) == pytest.approx(0.03)


def test_haiku_5_5_pays_more_for_a_long_prompt():
    """Over 100,000 prompt tokens, cache reads included, the whole call takes the higher rates."""
    short = spend.Usage(input=50_000, cache_read=50_000, output=1_000)
    long = spend.Usage(input=50_000, cache_read=50_001, output=1_000)
    assert spend.price(HAIKU, short) == pytest.approx((50_000 * 0.10 + 50_000 * 0.01 + 500) / 1e6)
    assert spend.price(HAIKU, long) == pytest.approx(
        (50_000 * 0.50 + 50_001 * 0.05 + 1_000 * 2.50) / 1e6
    )


def test_model_ids_are_normalised():
    """A date suffix, a provider prefix and a context tag name the same price."""
    usage = spend.Usage(input=1_000_000)
    assert spend.price("claude-haiku-4-5-20251001", usage) == pytest.approx(1.00)
    assert spend.price("anthropic:claude-haiku-5-5", spend.Usage(input=100_000)) == pytest.approx(
        0.01
    )
    assert spend.price("claude-opus-5-5[1m]", usage) == pytest.approx(4.00)
    with pytest.raises(spend.UnknownModel):
        spend.price("gpt-5", usage)


def test_usage_from_the_api_and_from_langchain():
    """The API counts input without the cache; LangChain counts it with."""
    api = spend.Usage.from_api(
        {
            "input_tokens": 100,
            "cache_creation_input_tokens": 300,
            "cache_creation": {"ephemeral_5m_input_tokens": 100, "ephemeral_1h_input_tokens": 200},
            "cache_read_input_tokens": 600,
            "output_tokens": 50,
            "server_tool_use": {"web_search_requests": 2},
        }
    )
    assert api == spend.Usage(100, 100, 200, 600, 50, 2)
    assert spend.Usage.from_api({"cache_creation_input_tokens": 40}).cache_write_5m == 40
    chain = spend.Usage.from_langchain(
        {
            "input_tokens": 1000,
            "output_tokens": 50,
            "input_token_details": {"cache_read": 600, "cache_creation": 300},
        }
    )
    assert chain == spend.Usage(input=100, cache_write_5m=300, cache_read=600, output=50)
    assert spend.cache_share(chain) == pytest.approx(0.6)
    assert spend.cache_share(spend.Usage()) is None


# --- the guard ----------------------------------------------------------------------------------


def test_paid_calls_are_off_without_a_cap(tmp_path, monkeypatch):
    """No cap, no paid call; the refusal says how to allow one."""
    monkeypatch.delenv(spend.CAP_VARIABLE, raising=False)
    guard = spend.Guard.from_env(default_ledger=str(tmp_path / "ledger.jsonl"))
    with pytest.raises(spend.SpendRefused, match=spend.CAP_VARIABLE):
        guard.require()
    monkeypatch.setenv(spend.CAP_VARIABLE, "not a number")
    assert spend.Guard.from_env().cap == 0


def test_the_cap_holds_across_calls_and_processes(tmp_path, monkeypatch):
    """The total comes from the ledger file, so a second guard on it sees the first's spend."""
    ledger = tmp_path / "ledger.jsonl"
    monkeypatch.setenv(spend.CAP_VARIABLE, "0.002")
    monkeypatch.setenv(spend.LEDGER_VARIABLE, str(ledger))
    guard = spend.Guard.from_env(project="demo")
    guard.require()
    usd = guard.record(HAIKU, spend.Usage(input=10_000, output=2_000))
    assert usd == pytest.approx(0.002)
    other = spend.Guard.from_env()
    assert other.spent() == pytest.approx(0.002)
    with pytest.raises(spend.SpendRefused, match="already spent"):
        other.require()
    row = json.loads(ledger.read_text())
    assert row["project"] == "demo" and row["route"] == "api" and row["billed"] == row["usd"]


def test_a_model_without_a_price_is_refused(tmp_path):
    """The cap cannot hold a call it cannot price."""
    guard = spend.Guard(5, tmp_path / "ledger.jsonl")
    with pytest.raises(spend.SpendRefused, match="no price"):
        guard.require(model="some-new-model")


def test_parallel_records_append_whole_lines(tmp_path):
    """Threads writing at once leave one valid row per call."""
    guard = spend.Guard(5, tmp_path / "ledger.jsonl")
    with ThreadPoolExecutor(max_workers=8) as pool:
        list(pool.map(lambda _: guard.record(HAIKU, spend.Usage(input=10)), range(200)))
    assert len(spend.read_ledger([guard.ledger])) == 200


# --- record and replay --------------------------------------------------------------------------


def test_fingerprint_ignores_cache_markers_streaming_and_key_order():
    """Turning caching on keeps a recording valid; changing the prompt does not."""
    plain = request()
    marked = request()
    marked["messages"][0]["content"][0]["cache_control"] = {"type": "ephemeral"}
    reordered = dict(reversed(list(request(stream=True).items())))
    assert spend.fingerprint(plain) == spend.fingerprint(marked) == spend.fingerprint(reordered)
    assert spend.fingerprint(plain) != spend.fingerprint(request("hello!"))
    assert spend.fingerprint(plain) != spend.fingerprint(request(max_tokens=101))


def test_a_rerun_is_answered_from_the_recordings_for_free(tmp_path):
    """A later run of the same work is answered from what the first run recorded and bills
    nothing."""
    guard = spend.Guard(1, tmp_path / "ledger.jsonl")
    sent = []

    def send(body):
        sent.append(body)
        return answer()

    first = spend.call(request(), send, guard=guard, recorder=spend.Recorder(tmp_path / "r"))
    second = spend.call(request(), send, guard=guard, recorder=spend.Recorder(tmp_path / "r"))
    assert first == second and len(sent) == 1
    rows = spend.read_ledger([guard.ledger])
    assert [row["route"] for row in rows] == ["api", "replay"]
    assert rows[0]["key"] == rows[1]["key"] == spend.fingerprint(request())
    assert guard.spent() == pytest.approx(rows[0]["usd"])
    assert rows[1]["billed"] == 0 and rows[1]["usd"] == rows[0]["usd"]
    totals = spend.tally(rows)["total"]
    assert totals.replayed == 1 and totals.saved == pytest.approx(rows[0]["usd"])


def test_repeats_of_one_request_are_separate_samples(tmp_path):
    """Within a run the same request asked three times gets three answers, not one answer three
    times; a rerun replays the three in order."""
    guard = spend.Guard(1, tmp_path / "ledger.jsonl")
    sent = []

    def send(body):
        sent.append(body)
        return answer(output_tokens=len(sent))  # each live answer differs

    recorder = spend.Recorder(tmp_path / "r")
    first = [spend.call(request(), send, guard=guard, recorder=recorder) for _ in range(3)]
    assert len(sent) == 3 and len({json.dumps(a) for a in first}) == 3
    rerun = spend.Recorder(tmp_path / "r", "replay")
    assert [spend.call(request(), send, guard=guard, recorder=rerun) for _ in range(3)] == first
    assert len(sent) == 3
    with pytest.raises(spend.ReplayMiss):
        spend.call(request(), send, guard=guard, recorder=rerun)  # a fourth was never recorded


def test_each_repetition_replays_its_own_answers(tmp_path):
    """Inside meter(sample=r) the recordings are kept per repetition: a later run replays each
    repetition's own answer, and a further repetition goes live."""
    guard = spend.Guard(1, tmp_path / "ledger.jsonl")
    sent = []

    def send(body):
        sent.append(body)
        return answer(output_tokens=len(sent))

    def run(repetition, recorder):
        with spend.meter(sample=repetition):
            return spend.call(request(), send, guard=guard, recorder=recorder)

    recorder = spend.Recorder(tmp_path / "r")
    recorded = {rep: run(rep, recorder) for rep in (1, 2, 3)}
    later = spend.Recorder(tmp_path / "r")
    assert {rep: run(rep, later) for rep in (3, 1, 2)} == recorded and len(sent) == 3
    assert run(4, later) not in recorded.values() and len(sent) == 4


def test_replay_never_goes_live(tmp_path):
    """A miss in replay mode raises before anything is sent, with or without a key."""
    recorder = spend.Recorder(tmp_path / "replay", "replay")

    def send(body):
        raise AssertionError("replay must not call the model")

    with pytest.raises(spend.ReplayMiss):
        spend.call(request(), send, guard=spend.Guard(5, tmp_path / "l.jsonl"), recorder=recorder)
    spend.Recorder(tmp_path / "replay", "record").put(
        spend.fingerprint(request()), HAIKU, answer(), spend.Usage(input=1000, output=200)
    )
    rerun = spend.Recorder(tmp_path / "replay", "replay")
    assert spend.call(request(), send, guard=None, recorder=rerun) == answer()
    assert (recorder.hits, recorder.misses, rerun.hits, rerun.misses) == (0, 1, 1, 0)


def test_a_live_call_needs_a_guard_and_a_cap(tmp_path):
    """Without a guard, or with a guard that has no cap, nothing is sent."""

    def send(body):
        raise AssertionError("must not be sent")

    with pytest.raises(spend.SpendRefused):
        spend.call(request(), send, guard=None)
    with pytest.raises(spend.SpendRefused):
        spend.call(request(), send, guard=spend.Guard(0, tmp_path / "ledger.jsonl"))


def test_recorder_from_the_environment(tmp_path, monkeypatch):
    """Off unless asked for; the folder can be moved."""
    monkeypatch.delenv("FLYWHEEL_REPLAY", raising=False)
    assert spend.Recorder.from_env().mode == "off"
    monkeypatch.setenv("FLYWHEEL_REPLAY", "replay")
    monkeypatch.setenv("FLYWHEEL_REPLAY_DIR", str(tmp_path))
    recorder = spend.Recorder.from_env()
    assert recorder.mode == "replay" and recorder.root == tmp_path
    with pytest.raises(ValueError):
        spend.Recorder(tmp_path, "sometimes")


# --- the meter ----------------------------------------------------------------------------------


def test_the_meter_counts_routes_and_prices_only_paid_ones():
    """Subscription calls keep their tokens and get no price."""
    with spend.meter() as paid:
        spend.note(HAIKU, spend.Usage(input=1000, output=100))
        spend.note(HAIKU, spend.Usage(input=1000, output=100), "replay")
    summary = paid.summary()
    assert summary["calls"] == 2 and summary["replayed"] == 1
    assert summary["usd"] == pytest.approx(2 * (1000 * 0.10 + 100 * 0.50) / 1e6)
    assert summary["billed"] == pytest.approx(summary["usd"] / 2)
    with spend.meter() as free:
        spend.note(SONNET, spend.Usage(input=500, cache_read=1500, output=10), "subscription")
    summary = free.summary()
    assert "usd" not in summary and summary["cache_read"] == 1500 and summary["billed"] == 0
    with spend.meter() as idle:
        pass
    assert idle.summary() is None
    with pytest.raises(ValueError):
        spend.note(HAIKU, spend.Usage(), "free")


def test_the_meter_follows_copied_context_into_threads():
    """An agent that fans out with a copied context is still counted."""
    with spend.meter() as used:
        context = contextvars.copy_context()
        worker = threading.Thread(
            target=context.run, args=(spend.note, HAIKU, spend.Usage(input=10))
        )
        worker.start()
        worker.join()
    assert used.calls == 1


# --- the runner ---------------------------------------------------------------------------------


def test_runs_keep_their_usage_and_the_first_runs_alone():
    """Each run's calls are kept on it, and parallel runs start only after the first ends."""
    timeline = []
    lock = threading.Lock()

    def target(inputs):
        with lock:
            timeline.append(("start", inputs["n"], time.perf_counter()))
        if inputs["n"] == 0:
            time.sleep(0.05)
        spend.note(HAIKU, spend.Usage(input=100 * (inputs["n"] + 1), output=10))
        with lock:
            timeline.append(("end", inputs["n"], time.perf_counter()))
        return {"ok": True}

    examples = [Example(id=f"c{n}", inputs={"n": n}, reference_outputs={}) for n in range(5)]
    result = run_local(
        target, [], examples, repetitions=1, label="x", dataset_version="v1", concurrency=4
    )
    first_end = next(t for kind, n, t in timeline if kind == "end" and n == 0)
    others = [t for kind, n, t in timeline if kind == "start" and n != 0]
    assert all(t >= first_end for t in others)
    assert [run.usage["input"] for run in result.runs] == [100, 200, 300, 400, 500]
    assert result.runs[0].usage["usd"] > 0


def test_a_spend_stop_ends_the_run_but_an_ordinary_error_is_one_errored_run():
    """A bug in one case is that case's result; a refused call would refuse every later case."""
    started = []

    def target(inputs):
        started.append(inputs["n"])
        if inputs["n"] == 0:
            raise ValueError("a bug in the agent")
        if inputs["n"] == 1:
            raise spend.SpendRefused("a call to claude-haiku-5-5 refused: paid calls are off")
        return {"ok": True}

    examples = [Example(id=f"c{n}", inputs={"n": n}, reference_outputs={}) for n in range(4)]
    with pytest.raises(spend.SpendRefused):
        run_local(target, [], examples, repetitions=1, label="x", dataset_version="v1")
    assert started == [0, 1]


def test_a_replay_miss_in_parallel_runs_drops_the_runs_not_yet_started():
    """Runs already going finish; the rest never start."""
    started = []

    def target(inputs):
        started.append(inputs["n"])
        if inputs["n"] == 1:
            raise spend.ReplayMiss("no recording for this call")
        time.sleep(0.2)
        return {"ok": True}

    examples = [Example(id=f"c{n}", inputs={"n": n}, reference_outputs={}) for n in range(10)]
    with pytest.raises(spend.ReplayMiss):
        run_local(
            target, [], examples, repetitions=1, label="x", dataset_version="v1", concurrency=2
        )
    assert 2 <= len(started) < 10


def test_usage_survives_save_and_load(tmp_path):
    """An experiment's usage is written and read back; old files without it still load."""
    run = RunRecord("a", 1, {"ok": 1.0}, usage={"calls": 1, "input": 5})
    experiment = Experiment("x", "local", "v1", 1, [run], {"a": "case a"})
    experiment.save(tmp_path / "x.json")
    assert Experiment.load(tmp_path / "x.json").runs[0].usage == {"calls": 1, "input": 5}
    raw = json.loads((tmp_path / "x.json").read_text())
    del raw["runs"][0]["usage"]
    (tmp_path / "old.json").write_text(json.dumps(raw))
    assert Experiment.load(tmp_path / "old.json").runs[0].usage is None


# --- the gate's cost checks -----------------------------------------------------------------------


def costed(label, usage, cases=("a", "b"), runs=3):
    """An experiment whose every run passes and used `usage`."""
    records = [
        RunRecord(case, rep, {"ok": 1.0}, usage=dict(usage))
        for case in cases
        for rep in range(1, runs + 1)
    ]
    return Experiment(label, "local", "v1", runs, records, {case: f"case {case}" for case in cases})


PAID = {"calls": 2, "input": 1000, "cache_write": 0, "cache_read": 3000, "output": 200}


def test_cost_checks_are_reported_but_off_by_default():
    """A dearer run is shown, not blocked, until a limit is set."""
    base = costed("base", {**PAID, "usd": 0.001, "billed": 0.001})
    head = costed("head", {**PAID, "output": 400, "usd": 0.002, "billed": 0.002})
    result = compare(base, head, GateSettings(metrics=("ok",)))
    assert result.passed
    assert result.base_cost.usd == pytest.approx(0.001) and result.head_cost.calls == 2
    text = render(result)
    assert "### Cost of a run" in text and "Dollars at list price" in text
    assert "| Share of the prompt read from the cache | 75% | 75% |" in text


def test_a_dearer_run_blocks_when_a_limit_is_set():
    """Dollars, tokens and the cache share each have their own limit."""
    base = costed("base", {**PAID, "usd": 0.001, "billed": 0.001})
    pricier = costed("head", {**PAID, "output": 400, "usd": 0.0015, "billed": 0.0015})
    settings = GateSettings(metrics=("ok",), max_cost_increase=0.25)
    result = compare(base, pricier, settings)
    assert not result.passed
    assert "a run's cost rose 50%" in result.reasons[0]
    assert compare(base, pricier, GateSettings(metrics=("ok",), max_cost_increase=0.5)).passed

    uncached = costed("head", {**PAID, "input": 4000, "cache_read": 0, "usd": 0.002})
    result = compare(base, uncached, GateSettings(metrics=("ok",), max_cache_drop=0.2))
    assert not result.passed
    assert "fell from 75% to 0%" in result.reasons[0]

    longer = costed("head", {**PAID, "input": 3000})
    result = compare(base, longer, GateSettings(metrics=("ok",), max_token_increase=0.25))
    assert not result.passed and "tokens rose 48%" in result.reasons[0]


def test_subscription_runs_compare_tokens_not_dollars():
    """Without a price on either side, the token and cache checks still work."""
    base = costed("base", {**PAID, "subscription": 2})
    head = costed("head", {**PAID, "input": 4000, "cache_read": 0, "subscription": 2})
    settings = GateSettings(metrics=("ok",), max_cost_increase=0.1, max_cache_drop=0.2)
    result = compare(base, head, settings)
    assert result.base_cost.usd is None
    assert len(result.reasons) == 1 and "cache" in result.reasons[0]
    assert "Dollars at list price" not in render(result)


def test_no_usage_on_one_side_compares_nothing():
    """A side that counted no calls cannot be compared, and does not block."""
    base = costed("base", {**PAID, "usd": 0.001})
    head = costed("head", {})
    settings = GateSettings(metrics=("ok",), max_cost_increase=0.1)
    result = compare(base, head, settings)
    assert result.passed and result.head_cost is None
    assert "pull request's runs counted no model calls" in render(result)
    plain = compare(costed("base", {}), costed("head", {}), settings)
    assert "### Cost of a run" not in render(plain)


def test_cost_limits_load_from_the_config(tmp_path):
    """The three limits are read from `[gate]`; unset means off."""
    path = tmp_path / "flywheel.toml"
    path.write_text(
        '[flywheel]\ntarget = "m:t"\nevaluators = []\ndataset = "d.jsonl"\n'
        "[gate]\nmax_cost_increase = 0.25\nmax_cache_drop = 0.2\n"
    )
    gate = load(path).gate
    assert gate.max_cost_increase == 0.25 and gate.max_cache_drop == 0.2
    assert gate.max_token_increase is None


# --- flywheel spend -----------------------------------------------------------------------------


def test_spend_totals_a_ledger_without_a_config(tmp_path, monkeypatch, capsys):
    """`flywheel spend` needs only the ledger, and prints totals by day, model and project."""
    monkeypatch.chdir(tmp_path)
    ledger = tmp_path / "ledger.jsonl"
    guard = spend.Guard(5, ledger, project="orion")
    guard.record(HAIKU, spend.Usage(input=1000, cache_read=3000, output=200))
    guard.record(HAIKU, spend.Usage(input=1000, cache_read=3000, output=200), route="replay")
    assert main(["spend", str(ledger)]) == 0
    text = capsys.readouterr().out
    assert "total" in text and "claude-haiku-5-5" in text and "orion" in text and "75%" in text
    assert main(["spend", str(ledger), "--json"]) == 0
    data = json.loads(capsys.readouterr().out)
    assert data["total"]["calls"] == 2 and data["total"]["replayed"] == 1
    assert data["total"]["billed"] == pytest.approx(data["total"]["saved"])
    assert main(["spend", str(tmp_path / "missing.jsonl")]) == 2
