# Lab 10 — Concurrent DAG execution

## Question

When does independent work justify bounded dependency-aware concurrency instead of deterministic sequential execution?

## Workload

```text
A (120ms) ─┐
           ├─> C (20ms)
B (120ms) ─┘
```

A and B are independent. C may start only after both complete.

## Baseline

Run A, then B, then C sequentially.

## Treatment

Run ready independent tasks with at most two workers. A dependent task becomes runnable only after all dependencies complete successfully.

## Failure controls

- a planted scheduler launches A/B/C at once and must be rejected for a dependency violation
- a real failure in A must block C while preserving independent B completion

## Non-goals

No distributed workers, leases, queues, retries, speculative execution, or multi-agent scheduling is introduced.
