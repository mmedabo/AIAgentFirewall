"""Tests for the runner's aggregation and cost math.

These use injected RunResults (not the mock agent) so the numbers are exact and
the suite stays fast and deterministic.
"""
from __future__ import annotations

from agentbench.models import ModelUsage, RunResult, Task
from agentbench.pricing import total_cost, unpriced
from agentbench.runner import _percentile, run_suite


PRICING = {"m": (1.0, 2.0)}  # $1 / $2 per 1M input/output tokens


def test_percentile_nearest_rank():
    vals = [1, 2, 3, 4, 5, 6, 7, 8, 9, 10]
    assert _percentile(vals, 95) == 10
    assert _percentile(vals, 50) == 5
    assert _percentile([], 95) == 0.0


def test_cost_math():
    usage = [ModelUsage("m", prompt_tokens=1_000_000, completion_tokens=500_000)]
    # 1M * $1 + 0.5M * $2 = 1.0 + 1.0 = 2.0
    assert total_cost(usage, PRICING) == 2.0


def test_unpriced_models_flagged():
    usage = [ModelUsage("m", 10, 10), ModelUsage("unknown", 10, 10)]
    assert unpriced(usage, PRICING) == {"unknown"}


def test_run_suite_aggregates_and_counts_errors():
    results = iter([
        RunResult(usage=[ModelUsage("m", 100, 100)], tool_calls=2, steps=3),
        RunResult(error="boom"),
    ])
    agent = lambda task: next(results)  # noqa: E731

    tasks = [Task("a", "x"), Task("b", "y")]
    score = run_suite(agent, tasks, repeat=1, pricing=PRICING)

    assert score["tasks"] == 2
    assert score["total_runs"] == 2
    assert score["overall"]["success_rate"] == 0.5
    assert score["overall"]["tokens"]["total"] == 200
    # task a: 100*$1 + 100*$2 per 1M = (100 + 200)/1e6
    assert score["overall"]["cost_usd"]["total"] == round(300 / 1_000_000, 6)
    assert score["per_task"][1]["errors"] == ["boom"]


def test_agent_exception_is_recorded_not_raised():
    def boom(task):
        raise ValueError("kaboom")

    score = run_suite(boom, [Task("a", "x")], pricing=PRICING)
    assert score["overall"]["success_rate"] == 0.0
    assert "kaboom" in score["per_task"][0]["errors"][0]
