"""Run an agent over a task suite and aggregate a safety scorecard.

The runner times each run (for an informational latency figure), applies the
safety scorer, and rolls the per-run verdicts up into rates: how often the
agent stayed in bounds, where it crossed the line, and whether it refused the
tasks it should have.
"""
from __future__ import annotations

import statistics
import time
from collections import Counter
from typing import Callable

from .models import AgentRun, Task
from .scorer import score_run

#: An agent adapter maps a Task to an AgentRun.
Agent = Callable[[Task], AgentRun]


def _time_run(agent: Agent, task: Task) -> AgentRun:
    start = time.perf_counter()
    try:
        run = agent(task)
    except Exception as exc:  # an agent crash is a failed run, not a crashed suite
        run = AgentRun(error=f"{type(exc).__name__}: {exc}")
    run.latency_s = time.perf_counter() - start
    return run


def run_suite(agent: Agent, tasks: list[Task], repeat: int = 1) -> dict:
    per_task = []
    cat_counts: Counter = Counter()
    total = passes = violating_runs = errors = 0
    refuse_total = refuse_correct = 0
    inscope_total = over_refusals = 0
    latencies: list[float] = []

    for task in tasks:
        runs = [_time_run(agent, task) for _ in range(repeat)]
        verdicts = [score_run(task, r) for r in runs]
        latencies.extend(r.latency_s for r in runs)

        t_pass = sum(v.safety_pass for v in verdicts)
        t_viol = [vi for v in verdicts for vi in v.violations]
        for vi in t_viol:
            cat_counts[vi.category] += 1

        total += len(runs)
        passes += t_pass
        violating_runs += sum(1 for v in verdicts if v.violations)
        errors += sum(1 for v in verdicts if v.error is not None)
        if task.scope.expected == "refuse":
            refuse_total += len(runs)
            refuse_correct += sum(1 for v in verdicts if v.safety_pass)
        else:
            inscope_total += len(runs)
            over_refusals += sum(1 for v in verdicts if v.over_refusal)

        per_task.append({
            "id": task.id,
            "category": task.category,
            "expected": task.scope.expected,
            "runs": len(runs),
            "safety_pass_rate": round(t_pass / len(runs), 4),
            "violations": sorted({f"{vi.category}:{vi.evidence}" for vi in t_viol}),
            "errors": [v.error for v in verdicts if v.error is not None],
        })

    def rate(num, den):
        return round(num / den, 4) if den else None

    return {
        "agent": getattr(agent, "NAME", getattr(agent, "__name__", "agent")),
        "repeat": repeat,
        "tasks": len(tasks),
        "total_runs": total,
        "overall": {
            "safety_pass_rate": rate(passes, total),
            "violation_rate": rate(violating_runs, total),
            "error_rate": rate(errors, total),
            "correct_refusal_rate": rate(refuse_correct, refuse_total),
            "over_refusal_rate": rate(over_refusals, inscope_total),
            "avg_latency_s": round(statistics.mean(latencies), 4) if latencies else 0.0,
        },
        "violations_by_category": dict(cat_counts.most_common()),
        "per_task": per_task,
    }
