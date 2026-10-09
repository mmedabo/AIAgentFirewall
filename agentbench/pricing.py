"""Token -> cost conversion.

Prices are USD per 1,000,000 tokens as ``(input, output)``. The table below is
a small set of PLACEHOLDERS so the demo produces numbers — they are NOT
guaranteed current. Maintain your own rates: edit this dict, or pass a pricing
JSON to the CLI (``--pricing rates.json``) shaped as
``{"model-id": [input_per_mtok, output_per_mtok]}``.

A model with no entry costs 0 and is reported under ``unpriced_models`` in the
scorecard, so missing rates are visible rather than silently wrong.
"""
from __future__ import annotations

from typing import Iterable

from .models import ModelUsage

# USD per 1M tokens: (input, output). Placeholders — verify and update.
PRICING: dict[str, tuple[float, float]] = {
    "mock-small": (0.25, 1.25),
    "mock-large": (3.00, 15.00),
}


def model_cost(usage: ModelUsage, pricing: dict[str, tuple[float, float]]) -> float:
    rate = pricing.get(usage.model)
    if rate is None:
        return 0.0
    in_rate, out_rate = rate
    return (usage.prompt_tokens * in_rate + usage.completion_tokens * out_rate) / 1_000_000


def total_cost(usages: Iterable[ModelUsage], pricing: dict[str, tuple[float, float]]) -> float:
    return sum(model_cost(u, pricing) for u in usages)


def unpriced(usages: Iterable[ModelUsage], pricing: dict[str, tuple[float, float]]) -> set:
    return {u.model for u in usages if u.model not in pricing}
