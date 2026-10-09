"""Agent adapters.

An adapter plugs your agent into the benchmark. It is a module exposing:

    NAME: str
        A short identifier for the scorecard, e.g. ``"mock"``.

    def run(task: Task) -> RunResult:
        Execute one task and report usage. Fill RunResult.usage (one
        ModelUsage per model call), tool_calls and steps. Do NOT set
        latency_s — the runner times the call. On failure, either raise
        (the runner records it) or return a RunResult with ``error`` set.

Keep any one-time setup (client construction, loading config) at module import
so it is not repeated per task. To measure a real agent, write a sibling module
that drives it and maps its native usage onto ModelUsage.
"""
from __future__ import annotations

import importlib


def load(name: str):
    """Import an adapter module by its short name."""
    return importlib.import_module(f"{__name__}.{name}")
