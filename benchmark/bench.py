#!/usr/bin/env python3
"""The benchmark harness.

Runs a scanner (via an adapter) over a labelled corpus and scores how well it
separates malicious artifacts from benign ones. Zero third-party dependencies:
labels are JSON, and the default adapter calls AgentFirewall in-process.

    python benchmark/bench.py run                 # score the default adapter
    python benchmark/bench.py run --format json   # machine-readable scorecard
    python benchmark/bench.py run --per-class      # add per-threat-class recall
    python benchmark/bench.py list                 # list the corpus
"""
from __future__ import annotations

import argparse
import dataclasses
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
REPO_ROOT = os.path.dirname(HERE)
CASES_DIR = os.path.join(HERE, "cases")

# Make both the repo (for `agentfirewall`) and this dir (for `adapters`)
# importable regardless of the current working directory.
for _p in (REPO_ROOT, HERE):
    if _p not in sys.path:
        sys.path.insert(0, _p)

import adapters  # noqa: E402  (after sys.path setup)

VERDICT_RANK = {"allow": 0, "warn": 1, "block": 2}


@dataclasses.dataclass
class Case:
    id: str
    label: str  # "malicious" | "benign"
    artifact_path: str
    threat_classes: list
    title: str = ""
    source: str = ""

    @property
    def is_malicious(self) -> bool:
        return self.label == "malicious"


def load_cases(cases_dir: str = CASES_DIR) -> list:
    cases = []
    for entry in sorted(os.listdir(cases_dir)):
        case_dir = os.path.join(cases_dir, entry)
        label_file = os.path.join(case_dir, "label.json")
        if not os.path.isfile(label_file):
            continue
        with open(label_file, encoding="utf-8") as fh:
            meta = json.load(fh)
        if meta.get("label") not in ("malicious", "benign"):
            raise ValueError(f"{label_file}: 'label' must be 'malicious' or 'benign'")
        artifact_path = os.path.normpath(os.path.join(case_dir, meta["artifact"]))
        if not os.path.exists(artifact_path):
            raise FileNotFoundError(f"{label_file}: artifact not found at {artifact_path}")
        cases.append(Case(
            id=meta.get("id", entry),
            label=meta["label"],
            artifact_path=artifact_path,
            threat_classes=meta.get("threat_classes", []),
            title=meta.get("title", ""),
            source=meta.get("source", ""),
        ))
    return cases


def evaluate(cases: list, adapter, flag_on: str) -> dict:
    """Run the adapter over every case and compute scores.

    A case is 'flagged' when the scanner's verdict is at least as severe as
    ``flag_on`` ('warn' or 'block').
    """
    threshold = VERDICT_RANK[flag_on]
    tp = fp = tn = fn = 0
    rows = []
    # per-threat-class: expected vs. detected across malicious cases
    class_expected: dict = {}
    class_detected: dict = {}

    for case in cases:
        out = adapter.scan(case.artifact_path)
        flagged = VERDICT_RANK.get(out["verdict"], 0) >= threshold
        detected_classes = set(out.get("categories", []))

        if case.is_malicious:
            correct = flagged
            if flagged:
                tp += 1
            else:
                fn += 1
            for cls in case.threat_classes:
                class_expected[cls] = class_expected.get(cls, 0) + 1
                if cls in detected_classes:
                    class_detected[cls] = class_detected.get(cls, 0) + 1
        else:
            correct = not flagged
            if flagged:
                fp += 1
            else:
                tn += 1

        rows.append({
            "id": case.id,
            "label": case.label,
            "verdict": out["verdict"],
            "flagged": flagged,
            "correct": correct,
            "categories": sorted(detected_classes),
        })

    total = tp + fp + tn + fn
    precision = tp / (tp + fp) if (tp + fp) else 0.0
    recall = tp / (tp + fn) if (tp + fn) else 0.0
    f1 = (2 * precision * recall / (precision + recall)) if (precision + recall) else 0.0
    per_class = {
        cls: {
            "expected": class_expected[cls],
            "detected": class_detected.get(cls, 0),
            "recall": class_detected.get(cls, 0) / class_expected[cls],
        }
        for cls in sorted(class_expected)
    }

    return {
        "adapter": adapter.NAME,
        "flag_on": flag_on,
        "cases": total,
        "confusion": {"tp": tp, "fp": fp, "tn": tn, "fn": fn},
        "metrics": {
            "precision": round(precision, 4),
            "recall": round(recall, 4),
            "f1": round(f1, 4),
            "accuracy": round((tp + tn) / total, 4) if total else 0.0,
            "false_positive_rate": round(fp / (fp + tn), 4) if (fp + tn) else 0.0,
        },
        "per_class": per_class,
        "rows": rows,
    }


def _print_text(score: dict, per_class: bool) -> None:
    c, m = score["confusion"], score["metrics"]
    print(f"Benchmark: {score['adapter']}  (flag-on={score['flag_on']}, {score['cases']} cases)")
    print("-" * 60)
    for r in score["rows"]:
        mark = "ok " if r["correct"] else "MISS"
        print(f"  [{mark}] {r['id']:26} {r['label']:9} -> {r['verdict']}")
    print("-" * 60)
    print(f"  TP={c['tp']}  FP={c['fp']}  TN={c['tn']}  FN={c['fn']}")
    print(f"  precision={m['precision']}  recall={m['recall']}  f1={m['f1']}")
    print(f"  accuracy={m['accuracy']}  false_positive_rate={m['false_positive_rate']}")
    if per_class and score["per_class"]:
        print("-" * 60)
        print("  per-threat-class recall:")
        for cls, s in score["per_class"].items():
            print(f"    {cls:22} {s['detected']}/{s['expected']}  ({s['recall']:.2f})")


def cmd_run(args) -> int:
    cases = load_cases()
    if not cases:
        print("no cases found under benchmark/cases/", file=sys.stderr)
        return 1
    adapter = adapters.load(args.adapter)
    score = evaluate(cases, adapter, args.flag_on)
    if args.format == "json":
        print(json.dumps(score, indent=2))
    else:
        _print_text(score, args.per_class)
    # Non-zero exit if the scanner got anything wrong, so CI can gate on it.
    return 0 if score["confusion"]["fp"] == 0 and score["confusion"]["fn"] == 0 else 1


def cmd_list(args) -> int:
    for case in load_cases():
        classes = ",".join(case.threat_classes) or "-"
        print(f"{case.id:26} {case.label:9} {classes}")
    return 0


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(prog="bench", description=__doc__.splitlines()[0])
    sub = parser.add_subparsers(dest="cmd", required=True)

    p_run = sub.add_parser("run", help="score a scanner against the corpus")
    p_run.add_argument("--adapter", default="agentfirewall", help="adapter module name")
    p_run.add_argument("--flag-on", choices=["warn", "block"], default="warn",
                       help="verdict severity that counts as 'flagged as malicious'")
    p_run.add_argument("--format", choices=["text", "json"], default="text")
    p_run.add_argument("--per-class", action="store_true",
                       help="also print per-threat-class recall")
    p_run.set_defaults(func=cmd_run)

    p_list = sub.add_parser("list", help="list the corpus")
    p_list.set_defaults(func=cmd_list)

    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
