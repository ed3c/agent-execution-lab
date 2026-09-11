# Lab 06 — Controlled eval harness

## Architecture question

How do we prove an Agent execution architecture is better rather than merely more complex?

## Concrete contract

The harness integrates only Labs 01–05. It does not create a generic benchmark platform.

Each comparison binds:

- a fixed workload;
- a deterministic failure condition;
- the simpler baseline;
- the treatment architecture;
- deterministic machine-verifiable claim logic;
- semantic metrics plus optional wall-clock measurements.

## Reproducibility

A seed chooses deterministic failure parameters (for example Lab 04 crash step). Re-running the same seed must produce the same semantic evidence fingerprint. Wall time is measured but excluded from the fingerprint because scheduler noise is not semantic architecture evidence.

## Negative control

A planted broken Lab 03 treatment uses blind retry for an ambiguous post-commit timeout. The grader must reject it because it produces a duplicate physical write. If the negative control passes, the eval suite is untrusted.
