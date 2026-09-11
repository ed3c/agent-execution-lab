# Lab 07 — Side-effect / checkpoint crash gap

## Question

What execution mechanism is required when an external side effect commits, the worker dies, and the local checkpoint that would mark the step complete is never written?

## Failure boundary

```text
pending step
  -> external side effect COMMITTED
  -> process exits 99
  -> local state still pending
  -> restart
  -> checkpoint-only replay executes the step again
```

This is different from Lab 04. Lab 04 crashes only after both the side effect and checkpoint are durable. Here the failure is deliberately injected inside that gap.

## Baseline

Resume solely from local checkpoint state. A pending step is executed again.

## Treatment

Add only what this failure requires:

- stable `run_id + step_id -> operation_id`
- idempotent external execution keyed by `operation_id`
- reconciliation before replay
- advance local durable state only after success or reconciled success is known

## Non-goals

No durable event machine, HITL, DAG scheduler, worker lease, Temporal-style engine, or multi-agent abstraction is introduced in this lab.
