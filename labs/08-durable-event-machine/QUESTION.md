# Lab 08 — Durable state/event machine

## Question

When do mutable checkpoints stop being sufficient and justify explicit transition identity plus deterministic event replay?

## Failure boundary

The same logical transition events are delivered in different orders after restart/replay:

```text
ordered:   start -> complete  => completed
reordered: complete -> start  => running   (wrong)
```

A last-arrival-wins snapshot has no stable answer for duplicate or stale transition delivery.

## Baseline

Apply incoming transition notifications directly to a mutable snapshot with no event identity, sequence, deduplication, or reducer semantics.

## Treatment

Add the smallest mechanism required by the failure:

- append-only process-persistent transition log
- event identity
- transition sequence
- duplicate detection
- deterministic reducer over canonical sequence
- reuse Lab 07 `operation_id`

## Non-goals

No message broker, queue, Temporal-style runtime, HITL, DAG scheduler, leases, or multi-agent orchestration is introduced here.
