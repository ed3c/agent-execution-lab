# Lab 02 — Tool Gateway

## Architecture question

When does direct tool invocation become unsafe enough to justify a gateway?

## Failure injection

Use the same fake mutable service to demonstrate that direct calls can commit malformed payloads, commit unauthorized actions, and duplicate a logical operation.

## Treatment

Add only a gateway boundary with argument validation, permission checking, timeout, idempotency-key propagation, and structured allow/deny audit events.

## Decision boundary

The gateway is justified when a tool can mutate external state or when the caller is not trusted to enforce the tool contract itself. It is unnecessary overhead for pure/read-only calls whose invalid inputs cannot create side effects.
