# agentbench

An **operational benchmark for AI agents**. It runs an agent over a suite of
tasks and reports how it performs on the metrics that drive production cost and
UX: **latency, token usage, and dollar cost** — plus reliability (did the run
finish without error).

It deliberately does *not* score answer quality. It measures how *expensively*
and how *fast* an agent does its work, and is agnostic to which framework the
agent is built on.

> Zero third-party dependencies. Ships with a mock agent so it runs with no API
> keys; plug in your real agent via a small adapter.

## Quick start

```bash
python -m agentbench run                 # mock agent over tasks/
python -m agentbench run --repeat 5      # repeat each task for stable latency
python -m agentbench run --format json   # machine-readable scorecard
python -m agentbench list                # show the task suite
```

Example output:

```
agent=mock  tasks=5  repeat=1  runs=5
--------------------------------------------------------------------
task                        ok  lat.mean  lat.p95   tokens     cost$
summarize-doc             100%     0.015    0.015      611   0.00412
...
--------------------------------------------------------------------
  success rate : 100%
  latency (s)  : mean=0.016  median=0.016  p95=0.020
  tokens       : total=3194  per_run=638.8
  cost (USD)   : total=0.02158  per_run=0.00432
```

## Concepts

- **Task** — a prompt handed to the agent (`tasks/*.json`, each with `id` and
  `prompt`).
- **Adapter** — a module that runs one task with your agent and reports usage.
  The runner times the call itself, so latency is true end-to-end wall-clock.
- **Scorecard** — per-task and overall latency distribution (mean/median/p95),
  token totals, cost, success rate, and any unpriced models.

## Measure your own agent

Write `agentbench/adapters/myagent.py`:

```python
from agentbench.models import ModelUsage, RunResult, Task

NAME = "myagent"

def run(task: Task) -> RunResult:
    # ... invoke your agent on task.prompt ...
    return RunResult(
        output=answer,
        usage=[ModelUsage("claude-...", prompt_tokens=..., completion_tokens=...)],
        tool_calls=...,
        steps=...,
    )
```

Then: `python -m agentbench run --adapter myagent`. Don't set `latency_s` — the
runner measures it. Raise or set `RunResult.error` on failure; the suite records
it rather than crashing.

## Pricing

Token prices live in `agentbench/pricing.py` as USD per 1M `(input, output)`
tokens. The bundled rates are **placeholders** for the mock models — maintain
your own by editing that file or passing `--pricing rates.json`:

```json
{ "claude-opus-4": [15.0, 75.0], "claude-haiku-4": [0.80, 4.0] }
```

Any model with no price is counted as $0 and listed under `unpriced_models` in
the scorecard, so a missing rate is visible, never silent.

## Tests

```bash
pip install -e ".[dev]"
pytest
```

## Status

Early scaffold (v0.1). Metrics only, offline mock agent. Natural next steps: a
real model/agent adapter, concurrency for throughput benchmarking, and
persisting scorecards for run-over-run comparison.
