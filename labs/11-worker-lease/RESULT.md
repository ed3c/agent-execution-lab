# Lab 11 result contract

Worker ownership earns its place only if the same runnable-step workload separates shared-state execution from leased/fenced execution.

## Baseline

Two spawned processes both observe the step as runnable and both commit:

```text
workers: 2
physical effects: 2
```

## Lease treatment

Both workers race for the same lease. Exactly one receives a fencing token and exactly one authoritative effect is committed:

```text
lease owners: 1
physical effects: 1
operation identity: run-1:step-1
```

## Takeover + fencing

```text
worker A token: 1
lease expires
worker B token: 2
stale A late commit: rejected
B commit: accepted
physical effects: 1
```

## Negative control — expiry without fencing

The same token1/token2 takeover is sent to a sink that does not validate the authoritative fencing token. Both old and new owners commit, yielding two effects.

This proves why lease expiry and fencing solve different parts of the failure. It does not prove a particular production coordination backend or consensus algorithm is required.
