"""agentbench — benchmark AI agents on cybersecurity tasks for staying in bounds."""
from __future__ import annotations

import json
import os

from .models import ForbiddenRule, Scope, Task

__version__ = "0.2.0"


def _parse_scope(obj: dict) -> Scope:
    return Scope(
        allowed_targets=obj.get("allowed_targets", []),
        forbidden=[ForbiddenRule(**r) for r in obj.get("forbidden", [])],
        expected=obj.get("expected", "in_scope"),
    )


def load_tasks(tasks_dir: str) -> list[Task]:
    """Load tasks from a directory of ``*.json`` files.

    Each file is one task object or a list of them, each with ``id`` and
    ``prompt`` and an optional ``scope`` (``allowed_targets``, ``forbidden``,
    ``expected``).
    """
    tasks: list[Task] = []
    for name in sorted(os.listdir(tasks_dir)):
        if not name.endswith(".json"):
            continue
        with open(os.path.join(tasks_dir, name), encoding="utf-8") as fh:
            data = json.load(fh)
        for obj in (data if isinstance(data, list) else [data]):
            tasks.append(Task(
                id=obj["id"],
                prompt=obj["prompt"],
                category=obj.get("category", "general"),
                scope=_parse_scope(obj.get("scope", {})),
                metadata=obj.get("metadata", {}),
            ))
    return tasks
