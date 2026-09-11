# Agent Execution Lab Rules

## Primary invariant

Do not add an execution abstraction until a simpler architecture has physically reproduced the failure that motivates it.

## Required experiment shape

Every architecture change must preserve this order:

1. State the claim.
2. Reproduce a concrete failure deterministically.
3. Measure the simpler baseline.
4. Add exactly one mechanism when possible.
5. Re-run the same workload and failure schedule.
6. Verify with deterministic evidence where deterministic verification is possible.
7. Record what the evidence does **not** prove.

## Scope discipline

- Prefer one-process, in-memory implementations until evidence requires durability or distribution.
- Do not introduce LangGraph, Temporal, a multi-agent planner, a memory service, or a generic benchmark platform as a shortcut around a missing experiment.
- Side effects must become observable before they become abstract.
- Negative controls are mandatory once a grader/eval layer exists.
- Tests are evidence for observable behavior, not proof that an architecture is universally superior.

## Lab dependency line

```text
#1 agent-loop
  -> #2 tool-gateway
  -> #3 retry/idempotency
  -> #4 checkpoint/resume
  -> #5 sandbox
  -> #6 eval-harness integrates #1-#5
```

A later lab may reuse verified primitives from an earlier lab, but must not silently backport its abstraction into earlier baselines.
