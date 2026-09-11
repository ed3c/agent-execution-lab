# Lab 08 result contract

The architecture earns its place only if two claims are physically visible.

## Baseline failure

The same unique logical events produce different terminal snapshots solely because arrival order differs:

```text
[start, complete] -> completed
[complete, start] -> running
```

This is a replay ambiguity, not an LLM reasoning failure.

## Treatment

A process-persistent append-only transition log is reopened and replayed. Duplicate events are collapsed by identity, events are ordered by sequence, and a deterministic reducer derives the terminal state.

Expected evidence:

```text
arrival:   complete, start, start
canonical: start, complete
duplicates ignored: 1
final state: completed
operation identity: run-1:step-1
```

This proves explicit durable transition history is useful for this replay failure. It does not prove a general workflow engine, HITL runtime, or DAG scheduler is necessary.
