"""A deterministic offline agent, so the benchmark runs with no API keys.

It simulates a small multi-step agent: a couple of tool calls and two model
calls whose token usage scales with the prompt length. A tiny sleep per step
makes end-to-end latency measurable without being slow. Deterministic given the
task id, so repeated runs and tests are stable.
"""
from __future__ import annotations

import random
import time

from ..models import ModelUsage, RunResult, Task

NAME = "mock"

_STEP_DELAY_S = 0.005  # keep the suite fast; latency is still non-zero


def run(task: Task) -> RunResult:
    rng = random.Random(task.id)
    steps = rng.randint(2, 4)
    tool_calls = rng.randint(1, steps)

    prompt_len = len(task.prompt.split())
    for _ in range(steps):
        time.sleep(_STEP_DELAY_S)

    # Two model calls: a cheap planner and a larger worker.
    usage = [
        ModelUsage("mock-small",
                   prompt_tokens=prompt_len + rng.randint(20, 60),
                   completion_tokens=rng.randint(20, 80)),
        ModelUsage("mock-large",
                   prompt_tokens=prompt_len * steps + rng.randint(100, 300),
                   completion_tokens=rng.randint(80, 240)),
    ]
    return RunResult(
        output=f"[mock answer to {task.id}]",
        usage=usage,
        tool_calls=tool_calls,
        steps=steps,
    )
