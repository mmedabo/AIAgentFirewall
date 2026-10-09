"""Run an agent over a task suite and aggregate operational metrics.

The runner owns timing (true wall-clock per run) and turns the raw per-run
results into a scorecard: latency distribution, token totals, cost, and
reliability (did the run complete without error).
"""
from __future__ import annotations

import math
import statistics
import time
from typing import Callable

from . import pricing as _pricing
from .models import RunResult, Task

#: An agent adapter is anything callable that maps a Task to a RunResult.
Agent = Callable[[Task], RunResult]


def _percentile(values: list[float], pct: float) -> float:
    """Nearest-rank percentile; ``pct`` in [0, 100]. Empty -> 0.0."""
    if not values:
        return 0.0
    ordered = sorted(values)
    rank = max(1, math.ceil(pct / 100 * len(ordered)))
    return ordered[rank - 1]


def _time_run(agent: Agent, task: Task) -> RunResult:
    start = time.perf_counter()
    try:
        result = agent(task)
    except Exception as exc:  # an agent crash is a failed run, not a crashed suite
        result = RunResult(error=f"{type(exc).__name__}: {exc}")
    result.latency_s = time.perf_counter() - start
    return result


def run_suite(agent: Agent, tasks: list[Task], repeat: int = 1,
              pricing: dict | None = None) -> dict:
    """Run every task ``repeat`` times and return a scorecard dict."""
    rates = pricing if pricing is not None else _pricing.PRICING
    per_task = []
    all_latencies: list[float] = []
    all_unpriced: set = set()
    total_tokens = total_prompt = total_completion = 0
    total_cost = 0.0
    total_runs = ok_runs = 0

    for task in tasks:
        runs = [_time_run(agent, task) for _ in range(repeat)]
        latencies = [r.latency_s for r in runs]
        oks = [r for r in runs if r.ok]
        task_tokens = sum(r.total_tokens for r in runs)
        task_cost = sum(_pricing.total_cost(r.usage, rates) for r in runs)
        for r in runs:
            all_unpriced |= _pricing.unpriced(r.usage, rates)

        all_latencies.extend(latencies)
        total_tokens += task_tokens
        total_prompt += sum(r.prompt_tokens for r in runs)
        total_completion += sum(r.completion_tokens for r in runs)
        total_cost += task_cost
        total_runs += len(runs)
        ok_runs += len(oks)

        per_task.append({
            "id": task.id,
            "runs": len(runs),
            "success_rate": round(len(oks) / len(runs), 4),
            "latency_s": {
                "mean": round(statistics.mean(latencies), 4),
                "median": round(statistics.median(latencies), 4),
                "p95": round(_percentile(latencies, 95), 4),
                "min": round(min(latencies), 4),
                "max": round(max(latencies), 4),
            },
            "avg_tokens": round(task_tokens / len(runs), 1),
            "avg_tool_calls": round(sum(r.tool_calls for r in runs) / len(runs), 2),
            "avg_steps": round(sum(r.steps for r in runs) / len(runs), 2),
            "avg_cost_usd": round(task_cost / len(runs), 6),
            "errors": [r.error for r in runs if not r.ok],
        })

    return {
        "agent": getattr(agent, "NAME", getattr(agent, "__name__", "agent")),
        "repeat": repeat,
        "tasks": len(tasks),
        "total_runs": total_runs,
        "overall": {
            "success_rate": round(ok_runs / total_runs, 4) if total_runs else 0.0,
            "latency_s": {
                "mean": round(statistics.mean(all_latencies), 4) if all_latencies else 0.0,
                "median": round(statistics.median(all_latencies), 4) if all_latencies else 0.0,
                "p95": round(_percentile(all_latencies, 95), 4),
            },
            "tokens": {
                "total": total_tokens,
                "prompt": total_prompt,
                "completion": total_completion,
                "per_run": round(total_tokens / total_runs, 1) if total_runs else 0.0,
            },
            "cost_usd": {
                "total": round(total_cost, 6),
                "per_run": round(total_cost / total_runs, 6) if total_runs else 0.0,
            },
        },
        "unpriced_models": sorted(all_unpriced),
        "per_task": per_task,
    }
