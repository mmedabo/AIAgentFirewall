"""Scanner adapters for the benchmark harness.

An adapter is a module that knows how to drive one scanner and normalise its
output into the small vocabulary the harness scores against. Keeping this
boundary explicit is what makes the benchmark *neutral*: AgentFirewall is just
the first adapter, and any other scanner (even a non-Python one driven over a
subprocess) can be measured on the same corpus by adding a sibling module.

An adapter module MUST expose:

    NAME: str
        A short identifier, e.g. ``"agentfirewall"``.

    def scan(artifact_path: str) -> dict:
        Run the scanner over the artifact at ``artifact_path`` (a file,
        directory or archive) and return a dict with:

            verdict:    "block" | "warn" | "allow"   (required)
            categories: list[str]                    (threat classes flagged)
            raw:        dict                          (scanner-native output)

The harness turns ``verdict`` into a binary flagged/not-flagged decision using
a configurable threshold, so adapters only need to report the scanner's own
three-way decision, not guess the benchmark's policy.
"""
from __future__ import annotations

import importlib

VERDICTS = ("allow", "warn", "block")


def load(name: str):
    """Import an adapter module by its short name."""
    return importlib.import_module(f"{__name__}.{name}")
