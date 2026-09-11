# Lab 07 result contract

The architecture is justified only if the same crash gap produces both of these outcomes:

## Baseline — checkpoint-only replay

```text
first worker:  exit 99 after external commit
second worker: exit 0 after replay
physical effects: 2
duplicate effects: 1
```

A locally pending checkpoint cannot distinguish "never executed" from "executed externally but died before recording completion".

## Treatment — operation identity + reconciliation

```text
first worker:  exit 99 after one keyed external commit
second worker: exit 0 after reconciling the same operation identity
physical effects: 1
duplicate effects: 0
final local state: completed
```

This proves that checkpoint/resume alone is insufficient across an ambiguous commit gap. It does **not** prove that a general durable event machine is required; that question belongs to Lab 08.
