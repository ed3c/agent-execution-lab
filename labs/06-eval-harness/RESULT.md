# Lab 06 Result

The harness integrates five concrete architecture claims:

1. bounded execution stops a workload at its step budget;
2. a Tool Gateway blocks invalid/unauthorized writes and duplicate logical operations;
3. idempotency + reconciliation prevents duplicate writes after an ambiguous response loss;
4. checkpoint/resume avoids repeated committed steps after a hard process crash;
5. clean workspaces eliminate cross-trial false-positive contamination.

The suite also contains a planted broken ambiguous-write treatment. The deterministic grader must reject it. Re-running the same seed must produce the same semantic fingerprint while allowing wall-clock measurements to vary.

No LLM judge is used because every fact in these five labs is directly machine-checkable.
