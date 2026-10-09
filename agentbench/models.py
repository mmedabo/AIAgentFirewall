"""Core data models for the agent benchmark.

The vocabulary is small on purpose: a *task* goes in, an agent runs it, and a
*run result* carries back how much it cost to do so (tokens, tool calls) plus
whatever the agent produced. Latency is measured by the runner, not reported by
the agent, so it reflects true end-to-end wall-clock time.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Optional


@dataclass
class Task:
    """A unit of work handed to the agent."""

    id: str
    prompt: str
    metadata: dict = field(default_factory=dict)


@dataclass
class ModelUsage:
    """Token usage for a single model call (an agent may use several)."""

    model: str
    prompt_tokens: int = 0
    completion_tokens: int = 0

    @property
    def total_tokens(self) -> int:
        return self.prompt_tokens + self.completion_tokens


@dataclass
class RunResult:
    """What an agent reports after processing one task.

    Adapters fill everything except ``latency_s``, which the runner sets by
    timing the call. On failure, set ``error`` to a short string.
    """

    output: Any = None
    usage: list[ModelUsage] = field(default_factory=list)
    tool_calls: int = 0
    steps: int = 0
    error: Optional[str] = None
    latency_s: float = 0.0  # set by the runner

    @property
    def ok(self) -> bool:
        return self.error is None

    @property
    def prompt_tokens(self) -> int:
        return sum(u.prompt_tokens for u in self.usage)

    @property
    def completion_tokens(self) -> int:
        return sum(u.completion_tokens for u in self.usage)

    @property
    def total_tokens(self) -> int:
        return self.prompt_tokens + self.completion_tokens
