"""Adapter for AgentFirewall itself.

Uses the in-process API (no subprocess) since the scanner lives in this repo
and has zero required dependencies — it is both faster and avoids re-parsing
the CLI's JSON. The default-configured ``Scanner`` is used so the benchmark
measures the out-of-the-box detection posture.
"""
from __future__ import annotations

from agentfirewall.scanner import Scanner

NAME = "agentfirewall"

#: ``provenance`` is a trust-tier signal attached to almost every artifact, not
#: a threat detection, so it is not reported as a flagged threat class.
_NOISE_CATEGORIES = {"provenance"}

_scanner = Scanner()


def scan(artifact_path: str) -> dict:
    result = _scanner.scan_path(artifact_path)
    categories = sorted(
        {f.category for f in result.findings if f.category not in _NOISE_CATEGORIES}
    )
    return {
        "verdict": result.verdict.value,
        "categories": categories,
        "raw": result.to_dict(),
    }
