# AgentFirewall Benchmark

A scanner-agnostic benchmark for **AI-agent supply-chain security scanners** —
tools that decide whether a skill, agent, MCP server or plugin is safe to
install. The goal is a *neutral* benchmark: AgentFirewall is only the first
scanner measured, and any other tool can be scored on the same corpus by adding
an adapter.

It answers one question per scanner: **how well does it separate malicious
artifacts from benign ones, and which threat classes does it catch?**

## Run it

No third-party dependencies. From the repo root:

```bash
python benchmark/bench.py run                 # score AgentFirewall (default)
python benchmark/bench.py run --per-class      # + per-threat-class recall
python benchmark/bench.py run --format json    # machine-readable scorecard
python benchmark/bench.py run --flag-on block  # count only BLOCK as "flagged"
python benchmark/bench.py list                 # list the corpus
```

`run` exits non-zero if the scanner mislabels any case, so it doubles as a CI
regression gate.

## How scoring works

Each case is labelled `malicious` or `benign` (ground truth). The scanner is
run through an **adapter** that normalises its decision to `allow` / `warn` /
`block`. A case counts as *flagged* when the verdict meets the `--flag-on`
threshold (`warn` by default). From that:

| | predicted malicious | predicted benign |
|---|---|---|
| **actually malicious** | TP | FN |
| **actually benign** | FP | TN |

Reported: precision, recall, F1, accuracy, false-positive rate, and
per-threat-class recall (did the scanner's findings name the threat classes the
case is tagged with). The `provenance` trust-tier signal is excluded from
threat-class scoring — it is attached to nearly every artifact and is not a
detection.

## Corpus layout

```
cases/<case-id>/label.json      # ground truth + pointer to the artifact
```

`label.json` schema:

| field | required | meaning |
|---|---|---|
| `id` | no | case identifier (defaults to the directory name) |
| `title` | no | one-line human description |
| `artifact` | **yes** | path to the artifact, relative to the case directory |
| `label` | **yes** | `malicious` or `benign` |
| `threat_classes` | no | threat classes a correct scanner should flag (`[]` for benign) |
| `source` | no | provenance of the case (where it came from) |
| `references` | no | framework IDs (OWASP-LLM, MITRE-ATLAS, MCP, …) |

A case may be **self-contained** (artifact files live inside the case
directory) or **reference** an artifact elsewhere via a relative `artifact`
path. Self-contained is preferred for portability; the seed cases reference the
repo's `examples/` to avoid duplicating content.

## Adding a scanner

Drop a module in `adapters/` exposing `NAME` and
`scan(artifact_path) -> {"verdict", "categories", "raw"}` (see
`adapters/__init__.py` for the contract), then:

```bash
python benchmark/bench.py run --adapter <your_module>
```

Non-Python scanners fit too — the adapter just shells out and maps the tool's
output onto the three-way verdict.

## Honesty about the seed corpus ⚠️

The nine seed cases are **first-party**: they are AgentFirewall's own
`examples/`, authored by the same people who wrote its detection rules. That
makes them useful as a **regression gate** but weak as evidence of neutral
effectiveness — a scanner grading its own homework will score well. A perfect
score here means "no regressions," not "best in class."

The path to a credible neutral benchmark (and why this is phased):

- **Phase 1 (this directory):** working harness + adapter contract + seed
  corpus. Catches regressions today.
- **Phase 2:** independent cases from published incidents (EchoLeak, the MCP-CVE
  class, Bolt.new, …) and third-party red-team samples, plus a documented
  contribution format. Published scorecard.
- **Phase 3:** community submissions (moderated) and scoring of other scanners.

**Corpus safety rule:** cases are **synthetic or defanged** — this directory is
not a live-malware repository. Contributions that would execute real payloads,
carry real secrets, or include PII are out of scope.
