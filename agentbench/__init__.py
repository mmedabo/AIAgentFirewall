"""agentbench — an operational benchmark for AI agents (latency, cost, tokens)."""
from __future__ import annotations

import json
import os

from .models import Task

__version__ = "0.1.0"


def load_tasks(tasks_dir: str) -> list[Task]:
    """Load tasks from a directory of ``*.json`` files.

    Each file is either one task object or a list of task objects, each with
    ``id`` and ``prompt`` (and optional ``metadata``).
    """
    tasks: list[Task] = []
    for name in sorted(os.listdir(tasks_dir)):
        if not name.endswith(".json"):
            continue
        with open(os.path.join(tasks_dir, name), encoding="utf-8") as fh:
            data = json.load(fh)
        for obj in (data if isinstance(data, list) else [data]):
            tasks.append(Task(id=obj["id"], prompt=obj["prompt"],
                              metadata=obj.get("metadata", {})))
    return tasks
