# Lab 01 Result

Status: verified locally with deterministic tests before remote publication.

## Supported boundary

The bounded single-process loop is sufficient when all of these are true:

- task state may be lost and restarted;
- tools are read-only or the environment is disposable;
- a failed tool call may terminate the run;
- no external side effect requires exactly-once semantics;
- total step count is small and explicitly bounded.

## Physically reproduced failures

- deterministic tool exception terminates the run after one call; there is no hidden retry;
- deterministic step-budget exhaustion hard-stops before an unreachable final answer;
- deterministic tool timeout terminates the run after one call.

## Evidence

Local verification before publication: 4/4 Lab 01 tests passed.

The experiment runner writes the full event trace and per-run metrics to `evidence/experiments/lab01.json`.

## Not supported

This baseline is intentionally unsafe/incomplete for:

- mutable external side effects;
- ambiguous write outcomes;
- retry/idempotency requirements;
- process crash recovery;
- long-running durable workflows;
- cross-run environment isolation;
- architecture comparisons across many workloads.

Those boundaries motivate Labs 02–06 rather than being hidden inside Lab 01.
