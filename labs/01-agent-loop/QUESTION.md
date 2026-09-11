# Lab 01 — Minimal bounded agent loop

## Architecture question

What is the smallest execution loop that is sufficient for short, ephemeral tasks with no irreversible side effects?

## State / environment / failure boundary

- State: ephemeral, in-memory.
- Environment: read-only or fully disposable.
- Failure modes under test: deterministic tool failure, tool timeout, and step-budget exhaustion.

## Baseline

```text
input -> decide -> tool -> observe -> decide -> final
```

There is intentionally no checkpointing, retry policy, idempotency layer, durable queue, planner/executor split, or memory service.

## Claim

For bounded tasks whose environment can be discarded safely, a single-process loop with explicit steps, timeout, budget, and trace is sufficient. The experiment does **not** claim this architecture is safe for mutable external side effects or durable workflows.
