# Lab 09 result contract

The architecture is justified only if process death separates the baseline from durable pause/resume.

## Baseline failure

```text
first worker: exit 99 after creating approval-1
human decision: approval-1 = approved
second worker: creates approval-2
privileged effects: 0
```

The decision exists, but its identity was not durably bound to the waiting operation.

## Treatment

```text
approval id: approval:run-1:privileged-step
first worker: exit 99 after durable pause + external request
human decision delivered twice: one durable decision
second worker: reuses same approval id
approved effects: 1
rejected effects: 0
```

The decision record is bound to the same Lab 07 operation identity, so approval does not create a competing side-effect identity.

This proves durable HITL pause/resume for this failure. It does not prove DAG scheduling or distributed worker ownership is needed.
