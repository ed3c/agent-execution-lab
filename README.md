# Agent Execution Lab

A failure-driven laboratory for proving Agent execution architecture decisions with controlled experiments.

## Core rule

```text
Claim -> Failure Injection -> Baseline -> Treatment -> Same Workload -> Deterministic Evidence
```

No architecture is promoted because it sounds correct. A mechanism earns its place only after a concrete failure is reproduced, the simpler baseline is measured, the proposed mechanism is added, and the same workload shows a meaningful improvement.

## First architecture ladder

| Lab | Failure boundary | Mechanism under test | Deterministic evidence |
| --- | --- | --- | --- |
| [#1](https://github.com/ed3c/agent-execution-lab/issues/1) | runaway / failed tool step | bounded agent loop | step count, status, trace |
| [#2](https://github.com/ed3c/agent-execution-lab/issues/2) | invalid / unauthorized / duplicate mutable call | Tool Gateway | physical writes, rejected calls |
| [#3](https://github.com/ed3c/agent-execution-lab/issues/3) | response lost after commit | idempotency + reconciliation | physical writes, retries, reconciliations |
| [#4](https://github.com/ed3c/agent-execution-lab/issues/4) | hard process crash | checkpoint + resume | process exit code, repeated committed steps |
| [#5](https://github.com/ed3c/agent-execution-lab/issues/5) | cross-trial state leakage | fresh workspace isolation | false-positive verifier result |
| [#6](https://github.com/ed3c/agent-execution-lab/issues/6) | untrusted architecture claim / weak grader | controlled eval harness | claim gates + planted negative control + fingerprint |

The dependency line is intentional:

```text
#1 agent-loop
  -> #2 tool-gateway
  -> #3 retry/idempotency
  -> #4 checkpoint/resume
  -> #5 sandbox/workspace isolation
  -> #6 eval harness integrates #1-#5
```

Each lab adds one mechanism only after the previous failure boundary is visible. The repository intentionally does not start with LangGraph, Temporal, a multi-agent planner, a memory service, or a generic benchmark platform.

## Run the evidence

```bash
python -m pip install -e '.[dev]'
pytest -q

for experiment in labs/*/experiment.py; do
  python "$experiment"
done

python labs/06-eval-harness/run.py --seed 17
```

Individual experiments write machine-readable evidence beneath `evidence/experiments/`. The integrated eval also writes a human-readable summary.

## What the first ladder does not prove

These labs do not establish that one execution architecture is universally best. They establish narrower decision boundaries under controlled failures. In particular, Lab 05 proves workspace isolation, not hostile-code containment, and Lab 04 deliberately excludes the crash window between an external side effect and checkpoint persistence.

That excluded window is the natural next failure to reproduce before introducing a durable workflow runtime.
