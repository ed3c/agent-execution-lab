# Lab 10 result contract

Bounded DAG concurrency earns its place only if it improves the same workload without weakening dependency semantics.

Expected evidence:

```text
sequential max concurrency: 1
bounded DAG max concurrency: 2
both complete: A, B, C
bounded DAG wall time: < 80% of sequential wall time
dependency violations: 0
```

The planted all-at-once scheduler must be rejected because C starts before A/B have completed, even if its wall time is lower.

When A fails, B may still complete because it is independent, but C must never start.

This lab proves one-process bounded concurrency for independent DAG branches. It does not prove distributed workers or lease/fencing semantics are needed.
