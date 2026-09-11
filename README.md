# Agent Execution Lab

A failure-driven laboratory for proving Agent execution architecture decisions with controlled experiments.

## Core rule

```text
Claim -> Failure Injection -> Baseline -> Treatment -> Same Workload -> Deterministic Evidence
```

No architecture is promoted because it sounds correct. A mechanism earns its place only after a concrete failure is reproduced, the simpler baseline is measured, the proposed mechanism is added, and the same workload shows a meaningful improvement.

## Learning / implementation order

1. [#1 bounded agent loop](https://github.com/ed3c/agent-execution-lab/issues/1)
2. [#2 tool gateway](https://github.com/ed3c/agent-execution-lab/issues/2)
3. [#3 retry / idempotency](https://github.com/ed3c/agent-execution-lab/issues/3)
4. [#4 checkpoint / resume](https://github.com/ed3c/agent-execution-lab/issues/4)
5. [#5 sandbox isolation](https://github.com/ed3c/agent-execution-lab/issues/5)
6. [#6 controlled eval harness](https://github.com/ed3c/agent-execution-lab/issues/6)

Each lab adds one execution mechanism only after the previous layer's failure boundary is visible.

## Lab 01

Lab 01 implements the smallest bounded, ephemeral agent loop with explicit run/step records, a step budget, tool timeout, deterministic failure injection, and an append-only event trace.

Run:

```bash
python -m pip install -e '.[dev]'
pytest
python labs/01-agent-loop/experiment.py
```

The experiment writes machine-readable evidence to `evidence/experiments/lab01.json`.
