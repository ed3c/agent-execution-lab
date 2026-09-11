# Lab 11 — Worker lease and fencing

## Question

When does concurrent durable execution require explicit worker ownership rather than a shared runnable step, and why is lease expiry alone insufficient?

## Failure boundary

Two separate worker processes observe the same runnable step and both execute it.

```text
ready step
  -> worker A observes ready
  -> worker B observes ready
  -> A commits
  -> B commits
  => duplicate physical effects
```

A lease can choose one current owner. But after the lease expires and a new worker takes over, the old worker may still be alive and may arrive late at the side-effect sink. TTL permits takeover; a fencing token is what lets the sink reject that stale owner.

## Treatment

- exclusive step lease
- monotonically increasing fencing token
- expiry permits takeover
- side-effect sink validates current owner + current fencing token
- reuse Lab 07 stable operation identity

## Lab boundary

This lab uses POSIX file locks only as a deterministic local coordination fixture on the Ubuntu CI runner. It does **not** claim file locks are a production distributed lock, consensus protocol, or cross-host lease implementation.

## Non-goals

No Raft/Paxos, Redis/etcd, queue, autoscaling worker pool, multi-region coordination, or multi-agent orchestration is introduced.
