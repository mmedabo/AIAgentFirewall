"""Command-line interface.

    agentbench run                      # run the mock agent over tasks/
    agentbench run --adapter mymod      # run your own adapter
    agentbench run --repeat 5           # repeat each task for stable latency
    agentbench run --pricing rates.json # supply your own token prices
    agentbench run --format json        # machine-readable scorecard
    agentbench list                     # list the task suite
"""
from __future__ import annotations

import argparse
import json
import os
import sys

from . import __version__, load_tasks
from . import adapters as _adapters
from .runner import run_suite

_DEFAULT_TASKS = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "tasks")


def _load_pricing(path: str | None):
    if not path:
        return None
    with open(path, encoding="utf-8") as fh:
        raw = json.load(fh)
    return {model: tuple(rate) for model, rate in raw.items()}


def _print_text(score: dict) -> None:
    o = score["overall"]
    print(f"agent={score['agent']}  tasks={score['tasks']}  "
          f"repeat={score['repeat']}  runs={score['total_runs']}")
    print("-" * 68)
    print(f"{'task':24} {'ok':>5} {'lat.mean':>9} {'lat.p95':>8} "
          f"{'tokens':>8} {'cost$':>9}")
    for t in score["per_task"]:
        lat = t["latency_s"]
        print(f"{t['id']:24} {t['success_rate']:>5.0%} {lat['mean']:>9.3f} "
              f"{lat['p95']:>8.3f} {t['avg_tokens']:>8.0f} {t['avg_cost_usd']:>9.5f}")
    print("-" * 68)
    print(f"  success rate : {o['success_rate']:.0%}")
    print(f"  latency (s)  : mean={o['latency_s']['mean']:.3f}  "
          f"median={o['latency_s']['median']:.3f}  p95={o['latency_s']['p95']:.3f}")
    print(f"  tokens       : total={o['tokens']['total']}  "
          f"per_run={o['tokens']['per_run']}")
    print(f"  cost (USD)   : total={o['cost_usd']['total']:.5f}  "
          f"per_run={o['cost_usd']['per_run']:.5f}")
    if score["unpriced_models"]:
        print(f"  ⚠ unpriced models (counted as $0): "
              f"{', '.join(score['unpriced_models'])}")


def cmd_run(args) -> int:
    tasks = load_tasks(args.tasks)
    if not tasks:
        print(f"no tasks found in {args.tasks}", file=sys.stderr)
        return 1
    mod = _adapters.load(args.adapter)
    agent = mod.run
    agent.NAME = getattr(mod, "NAME", args.adapter)
    score = run_suite(agent, tasks, repeat=args.repeat, pricing=_load_pricing(args.pricing))
    if args.format == "json":
        print(json.dumps(score, indent=2))
    else:
        _print_text(score)
    return 0


def cmd_list(args) -> int:
    for t in load_tasks(args.tasks):
        print(f"{t.id:24} {t.prompt[:60]}")
    return 0


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(prog="agentbench", description=__doc__.splitlines()[0])
    parser.add_argument("--version", action="version", version=f"agentbench {__version__}")
    sub = parser.add_subparsers(dest="cmd", required=True)

    for name, func, helptext in (("run", cmd_run, "run the benchmark"),
                                 ("list", cmd_list, "list the task suite")):
        p = sub.add_parser(name, help=helptext)
        p.add_argument("--tasks", default=_DEFAULT_TASKS, help="task directory")
        p.set_defaults(func=func)
        if name == "run":
            p.add_argument("--adapter", default="mock", help="adapter module name")
            p.add_argument("--repeat", type=int, default=1, help="runs per task")
            p.add_argument("--pricing", help="JSON file of model -> [in,out] per 1M tokens")
            p.add_argument("--format", choices=["text", "json"], default="text")

    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
