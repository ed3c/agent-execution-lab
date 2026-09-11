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

The first dependency line is intentional:

```text
#1 agent-loop
  -> #2 tool-gateway
  -> #3 retry/idempotency
  -> #4 checkpoint/resume
  -> #5 sandbox/workspace isolation
  -> #6 eval harness integrates #1-#5
```

## Durable execution ladder

GitHub issue numbers continue after the earlier PR numbers, so the logical Lab number and GitHub issue number differ from Lab 07 onward.

| Lab | GitHub issue | Failure / bottleneck to prove | Mechanism that may earn its place |
| --- | --- | --- | --- |
| 07 | [#13](https://github.com/ed3c/agent-execution-lab/issues/13) | side effect committed, worker dies before checkpoint | stable operation identity + idempotent execution + reconciliation + durable transition |
| 08 | [#14](https://github.com/ed3c/agent-execution-lab/issues/14) | checkpoint snapshots cannot deterministically explain replay/order | durable state/event machine |
| 09 | [#15](https://github.com/ed3c/agent-execution-lab/issues/15) | approval wait is lost across process death | durable HITL pause/resume |
| 10 | [#16](https://github.com/ed3c/agent-execution-lab/issues/16) | sequential execution wastes independent critical-path time | bounded dependency-aware DAG concurrency |
| 11 | [#17](https://github.com/ed3c/agent-execution-lab/issues/17) | two workers execute one runnable step | lease/ownership + fencing |
| 12 | [#18](https://github.com/ed3c/agent-execution-lab/issues/18) | short tests hide composed long-horizon failures | seeded long-horizon eval + negative controls |

```text
Lab 07 commit/checkpoint gap
  -> Lab 08 durable state/event machine
  -> Lab 09 HITL pause/resume
  -> Lab 10 concurrent DAG
  -> Lab 11 worker lease / duplicate execution
  -> Lab 12 long-horizon eval
```

Only the next unproven failure is implemented. Later issues remain hypotheses until the preceding lab produces remote physical evidence.

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

Individual experiments write machine-readable evidence beneath `evidence/experiments/`. The integrated eval also writes a human-readable summary and preserves the prior Lab 01–06 semantic fingerprint while extending the suite with later verified labs.

## What the repository does not prove

These labs do not establish that one execution architecture is universally best. They establish narrower decision boundaries under controlled failures. Lab 05 proves workspace isolation, not hostile-code containment. Lab 04 proves checkpoint/resume only when the side effect and checkpoint are both durable before the crash. Lab 07 specifically attacks the missing window between those two commits.
