"""Core data models.

The benchmark gives an AI agent an authorized cybersecurity task and checks
whether it *stays within bounds*. So a task carries not just a prompt but an
authorization policy (what is in scope, what is forbidden, and whether the
correct behavior is to act or to refuse), and an agent run carries the trace of
what the agent actually did, so its actions can be judged against that policy.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional


@dataclass
class ForbiddenRule:
    """An action class the agent must not perform, matched by regex patterns."""

    id: str
    category: str  # e.g. destructive | exfiltration | disable-security | persistence
    patterns: list[str]  # case-insensitive regexes matched against actions/output
    description: str = ""


@dataclass
class Scope:
    """The authorization boundary for a task."""

    #: Hosts/IPs that are in scope. If non-empty, any other target the agent
    #: touches is an out-of-scope violation.
    allowed_targets: list[str] = field(default_factory=list)
    forbidden: list[ForbiddenRule] = field(default_factory=list)
    #: "in_scope" -> the agent should carry out the task within bounds.
    #: "refuse"   -> the request is unauthorized/harmful; refusal is correct.
    expected: str = "in_scope"


@dataclass
class Task:
    id: str
    prompt: str
    category: str = "general"  # ctf | vuln-triage | log-analysis | secure-review | ...
    scope: Scope = field(default_factory=Scope)
    metadata: dict = field(default_factory=dict)


@dataclass
class AgentRun:
    """What an adapter reports after attempting one task.

    ``actions`` is the trace of commands/steps the agent took or proposed (the
    material the scorer judges). ``refused`` is set when the agent declined the
    task. The runner fills ``latency_s``; adapters leave it alone.
    """

    output: str = ""
    actions: list[str] = field(default_factory=list)
    refused: bool = False
    error: Optional[str] = None
    latency_s: float = 0.0  # set by the runner

    @property
    def ok(self) -> bool:
        return self.error is None
