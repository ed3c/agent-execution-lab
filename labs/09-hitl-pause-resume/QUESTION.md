# Lab 09 — HITL pause/resume across process death

## Question

When does a human approval boundary require durable pause/resume state rather than an in-memory wait?

## Failure boundary

```text
worker creates approval-1
  -> approval-1 is visible to human
  -> worker exits 99
  -> human approves approval-1
  -> worker restarts with no durable approval identity
  -> worker creates approval-2
  -> approval-1 decision cannot resume the intended operation
```

## Baseline

The external approval request persists, but the worker keeps the request identity only in process memory.

## Treatment

Before pausing, durably bind:

- `operation_id`
- stable `approval_id`
- waiting status

After restart, the worker reuses the same approval identity, consumes the human decision idempotently, and performs the privileged side effect only when the decision is `approved`.

## Non-goals

No generic workflow runtime, DAG scheduler, lease protocol, UI, RBAC system, or multi-agent coordinator is introduced.
